[CmdletBinding()]
param(
    [string]$Source,
    [Parameter(Mandatory=$true)][string]$Out,
    [ValidateSet('eden','atmosphere')][string]$Layout = 'eden',
    [string]$UpdateNsp,
    [switch]$ControlOnly
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Get-SHA([string]$Path) {
    $stream = [IO.File]::OpenRead($Path)
    $hasher = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($hasher.ComputeHash($stream)).Replace('-', '').ToLowerInvariant() }
    finally { $stream.Dispose(); $hasher.Dispose() }
}
function Test-File([string]$Path, $Expected) {
    if (!(Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
    $item = Get-Item -LiteralPath $Path
    if ($item.Length -ne $Expected.size) { return $false }
    return (Get-SHA $Path) -eq $Expected.sha256
}
function Assert-File([string]$Path, $Expected) {
    if (!(Test-File $Path $Expected)) { throw "Wrong file size or SHA-256: $Path" }
}
function Save-JSON([string]$Path, $Value) {
    $text = $Value | ConvertTo-Json -Depth 12
    [IO.File]::WriteAllText($Path + '.tmp', $text, (New-Object Text.UTF8Encoding($false)))
    Move-Item -LiteralPath ($Path + '.tmp') -Destination $Path -Force
}
function Safe-Path([string]$Root, [string]$Relative) {
    if ([IO.Path]::IsPathRooted($Relative) -or $Relative -match '(^|[\\/])\.\.([\\/]|$)|:') { throw 'Unsafe relative path in manifest' }
    $base = [IO.Path]::GetFullPath($Root).TrimEnd('\','/')
    $full = [IO.Path]::GetFullPath((Join-Path $base $Relative))
    if (!$full.StartsWith($base + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Path escapes its root' }
    $walk = $full
    while ($walk -and $walk.Length -ge $base.Length) {
        if (Test-Path -LiteralPath $walk) {
            if (((Get-Item -LiteralPath $walk -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Link or junction unsupported: $walk" }
        }
        $walk = [IO.Path]::GetDirectoryName($walk)
    }
    return $full
}
function Find-Source($Row) {
    $rel = [string]$Row.source
    $candidates = @($rel)
    if ($rel.StartsWith('effective/')) {
        $suffix = $rel.Substring(10)
        $candidates += @(('program0/' + $suffix), $suffix)
    } elseif ($rel.StartsWith('program1/')) { $candidates += 'update/' + $rel }
    foreach ($candidate in $candidates) {
        $p = Safe-Path $sourceRoot $candidate
        if (Test-File $p $Row.input) { return $p }
    }
    throw "Original file missing or wrong version: $rel (requires Japanese Base v0 + Update 1.12.0)"
}
function Target-Path([string]$Root, [string]$Relative) {
    $split = $Relative.IndexOf('/')
    $title = $Relative.Substring(0, $split)
    $rel = $Relative.Substring($split + 1)
    if ($Layout -eq 'eden') { return Safe-Path $Root ($title + '/KoreanPatch/' + $rel) }
    return Safe-Path $Root ('atmosphere/contents/' + $title + '/' + $rel)
}

function Invoke-Control([string]$Nsp, [string]$Destination, $Manifest) {
    $original = (Resolve-Path -LiteralPath $Nsp).Path
    $dest = [IO.Path]::GetFullPath($Destination)
    Assert-File $original $Manifest.control.source
    Assert-File (Safe-Path $PSScriptRoot $Manifest.control.patch) $Manifest.control.delta
    if (Test-Path -LiteralPath $dest) {
        Assert-File $dest $Manifest.control.output
        Write-Host 'PASS: existing title/icon update verified.'
        return
    }
    $parent = [IO.Path]::GetDirectoryName($dest)
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    $dest = Safe-Path $parent ([IO.Path]::GetFileName($dest))
    $partial = Safe-Path $parent ([IO.Path]::GetFileName($dest) + '.partial')
    & $exe -f -d -s $original (Safe-Path $PSScriptRoot $Manifest.control.patch) $partial
    if ($LASTEXITCODE -ne 0) { throw 'Title/icon xdelta failed' }
    Assert-File $partial $Manifest.control.output
    Move-Item -LiteralPath $partial -Destination $dest
    Write-Host "PASS: title/icon update saved to $dest"
}
function Copy-DecodedFile($Reader, [long]$Size, [string]$Partial, $Expected, $WholeHasher) {
    $hasher = [Security.Cryptography.SHA256]::Create()
    $writer = $null
    try {
        if ($Partial) { $writer = [IO.File]::Open($Partial, [IO.FileMode]::Create, [IO.FileAccess]::Write, [IO.FileShare]::None) }
        $buffer = New-Object byte[] (8 * 1024 * 1024)
        $left = $Size
        while ($left -gt 0) {
            $n = $Reader.Read($buffer, 0, [int][Math]::Min($left, [long]$buffer.Length))
            if ($n -le 0) { throw 'Truncated xdelta output' }
            $hasher.TransformBlock($buffer, 0, $n, $null, 0) | Out-Null
            $WholeHasher.TransformBlock($buffer, 0, $n, $null, 0) | Out-Null
            if ($writer) { $writer.Write($buffer, 0, $n) }
            $left -= $n
        }
        $hasher.TransformFinalBlock((New-Object byte[] 0), 0, 0) | Out-Null
        $hash = [BitConverter]::ToString($hasher.Hash).Replace('-', '').ToLowerInvariant()
        if ($hash -ne $Expected.sha256) { throw 'Decoded game file SHA-256 mismatch' }
    } finally { if ($writer) { $writer.Dispose() }; $hasher.Dispose() }
}

$savedXdelta = $env:XDELTA
$lock = $null
$decoder = $null
$decoderStarted = $false
$diagnostic = $null
$stage = $null
$completed = 0
try {
    $env:XDELTA = $null
    $manifestPath = Join-Path $PSScriptRoot 'manifest.json'
    $m = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($m.version -ne '0.92' -or $m.schema -ne 2) { throw 'Unsupported package manifest' }
    $exe = Safe-Path $PSScriptRoot $m.tool.path
    Assert-File $exe $m.tool
    if ($ControlOnly) {
        if (!$UpdateNsp) { throw '-ControlOnly requires -UpdateNsp' }
        Invoke-Control $UpdateNsp $Out $m
        exit 0
    }
    if (!$Source) { throw 'Specify -Source with the original extracted game folder' }
    $sourceRoot = (Resolve-Path -LiteralPath $Source).Path.TrimEnd('\','/')
    $destination = [IO.Path]::GetFullPath($Out).TrimEnd('\','/')
    if ($destination -eq $sourceRoot -or $destination.StartsWith($sourceRoot + '\', [StringComparison]::OrdinalIgnoreCase) -or $sourceRoot.StartsWith($destination + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Source and output directories must not overlap' }
    $packageHash = Get-SHA $manifestPath
    $parent = [IO.Path]::GetDirectoryName($destination)
    $leaf = [IO.Path]::GetFileName($destination)
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    $destination = Safe-Path $parent $leaf
    $stage = Safe-Path $parent ('.' + $leaf + '.v092-stage')
    $diagnostic = Safe-Path $parent ('.' + $leaf + '.v092-diagnostic.json')
    $lockPath = Safe-Path $parent ('.' + $leaf + '.v092-lock')
    $lock = [IO.File]::Open($lockPath, [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    $marker = [ordered]@{ package_sha256=$packageHash; layout=$Layout; source=$sourceRoot; version='0.92' }
    if (Test-Path -LiteralPath $destination) {
        $priorMarker = Join-Path $destination 'package-id.json'
        if (!(Test-Path -LiteralPath $priorMarker -PathType Leaf)) { throw 'Output folder already exists and is not this installer output. Choose another -Out path.' }
        $old = Get-Content -LiteralPath $priorMarker -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($old.package_sha256 -ne $packageHash -or $old.layout -ne $Layout -or $old.source -ne $sourceRoot) { throw 'Existing output belongs to another installation' }
        foreach ($target in $m.targets) { Assert-File (Target-Path $destination $target.path) $target }
        if ($UpdateNsp) { Invoke-Control $UpdateNsp (Join-Path $destination $m.control.target_name) $m }
        Write-Host 'PASS: existing installation verified.'
        exit 0
    }
    Write-Host 'Checking original files and game.xdelta...'
    $inputs = @{}
    foreach ($row in $m.files) { $inputs[$row.source] = Find-Source $row }
    $delta = Safe-Path $PSScriptRoot $m.bundle.patch.path
    Assert-File $delta $m.bundle.patch
    if ($UpdateNsp) {
        Assert-File (Resolve-Path -LiteralPath $UpdateNsp).Path $m.control.source
        Assert-File (Safe-Path $PSScriptRoot $m.control.patch) $m.control.delta
    }
    if (Test-Path -LiteralPath $stage) {
        $stageMarker = Join-Path $stage 'package-id.json'
        if (!(Test-Path -LiteralPath $stageMarker -PathType Leaf)) { throw 'Unrecognized staging folder; choose another -Out path' }
        $old = Get-Content -LiteralPath $stageMarker -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($old.package_sha256 -ne $packageHash -or $old.layout -ne $Layout -or $old.source -ne $sourceRoot) { throw 'Staging folder belongs to another installation' }
    } else {
        New-Item -ItemType Directory -Path $stage | Out-Null
        Save-JSON (Join-Path $stage 'package-id.json') $marker
    }
    $sourceBundle = Safe-Path $stage '.original-stream.bin'
    if (!(Test-File $sourceBundle $m.bundle.source)) {
        Write-Host 'Preparing original file stream (byte copy only)...'
        $temporary = Safe-Path $stage '.original-stream.bin.partial'
        $writer = [IO.File]::Open($temporary, [IO.FileMode]::Create, [IO.FileAccess]::Write, [IO.FileShare]::None)
        try {
            foreach ($row in $m.files) {
                if ($writer.Position -ne $row.source_offset) { throw 'Invalid source stream order' }
                $reader = [IO.File]::OpenRead($inputs[$row.source])
                try { $reader.CopyTo($writer, 8 * 1024 * 1024) } finally { $reader.Dispose() }
            }
        } finally { $writer.Dispose() }
        Assert-File $temporary $m.bundle.source
        Move-Item -LiteralPath $temporary -Destination $sourceBundle -Force
    }
    Write-Host 'Applying game.xdelta...'
    $info = New-Object Diagnostics.ProcessStartInfo
    $info.FileName = $exe
    $info.Arguments = '-d -c -s "' + $sourceBundle + '" "' + $delta + '"'
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $decoder = New-Object Diagnostics.Process
    $decoder.StartInfo = $info
    if (!$decoder.Start()) { throw 'Could not start xdelta3' }
    $decoderStarted = $true
    $stderrTask = $decoder.StandardError.ReadToEndAsync()
    $decoded = $decoder.StandardOutput.BaseStream
    $wholeHasher = [Security.Cryptography.SHA256]::Create()
    $offset = [long]0
    try {
        foreach ($row in $m.files) {
            if ($offset -ne $row.target_offset) { throw 'Invalid target stream order' }
            $primary = Target-Path $stage $row.destinations[0]
            New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($primary)) | Out-Null
            $reuse = Test-File $primary $row.output
            $partial = $null
            if (!$reuse) {
                $partial = Safe-Path ([IO.Path]::GetDirectoryName($primary)) ([IO.Path]::GetFileName($primary) + '.partial')
            }
            Copy-DecodedFile $decoded $row.output.size $partial $row.output $wholeHasher
            if (!$reuse) { Move-Item -LiteralPath $partial -Destination $primary -Force }
            foreach ($relative in @($row.destinations | Select-Object -Skip 1)) {
                $secondary = Target-Path $stage $relative
                if (!(Test-File $secondary $row.output)) {
                    New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($secondary)) | Out-Null
                    if (Test-Path -LiteralPath $secondary) { Remove-Item -LiteralPath $secondary }
                    try { New-Item -ItemType HardLink -Path $secondary -Target $primary -ErrorAction Stop | Out-Null }
                    catch { Copy-Item -LiteralPath $primary -Destination $secondary }
                    Assert-File $secondary $row.output
                }
            }
            $offset += $row.output.size
            $completed++
            Save-JSON $diagnostic ([ordered]@{ result='RUNNING'; version='0.92'; completed=$completed; total=@($m.files).Count; item=$row.source })
            Write-Host "[$completed/$(@($m.files).Count)] verified $($row.source)"
        }
        if ($decoded.ReadByte() -ne -1) { throw 'Unexpected extra xdelta output' }
        $decoder.WaitForExit()
        $errorText = $stderrTask.GetAwaiter().GetResult()
        if ($decoder.ExitCode -ne 0) { throw "xdelta failed (exit $($decoder.ExitCode)): $errorText" }
        $wholeHasher.TransformFinalBlock((New-Object byte[] 0), 0, 0) | Out-Null
        $wholeHash = [BitConverter]::ToString($wholeHasher.Hash).Replace('-', '').ToLowerInvariant()
        if ($offset -ne $m.bundle.output.size -or $wholeHash -ne $m.bundle.output.sha256) { throw 'Final decoded stream mismatch' }
    } finally { $wholeHasher.Dispose() }
    foreach ($target in $m.targets) { Assert-File (Target-Path $stage $target.path) $target }
    if ($UpdateNsp) { Invoke-Control $UpdateNsp (Join-Path $stage $m.control.target_name) $m }
    Remove-Item -LiteralPath $sourceBundle
    $report = [ordered]@{ result='PASS'; version='0.92'; content_version='0.9'; package_sha256=$packageHash; layout=$Layout; verified_files=@($m.targets).Count; exact_published_v09_output=$true; files=$m.targets; powershell=$PSVersionTable.PSVersion.ToString() }
    Save-JSON (Join-Path $stage 'install_report.json') $report
    [IO.Directory]::Move($stage, $destination)
    Save-JSON $diagnostic $report
    Write-Host "PASS: all $(@($m.targets).Count) game files match v0.9. Output: $destination"
} catch {
    if ($diagnostic) { Save-JSON $diagnostic ([ordered]@{ result='FAILED'; version='0.92'; completed=$completed; error=$_.Exception.Message }) }
    Write-Error -ErrorAction Continue $_
    if ($stage) { Write-Host "Incomplete files are kept for resume: $stage" }
    exit 1
} finally {
    if ($decoder) { if ($decoderStarted -and !$decoder.HasExited) { $decoder.Kill(); $decoder.WaitForExit() }; $decoder.Dispose() }
    if ($lock) { $lock.Dispose() }
    $env:XDELTA = $savedXdelta
}
