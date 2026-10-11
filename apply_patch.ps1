[CmdletBinding()]
param([string]$BaseNsp,[string]$UpdateNsp,[string]$Out)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Hash-File([string]$p){$s=[IO.File]::OpenRead($p);$h=[Security.Cryptography.SHA256]::Create();try{return [BitConverter]::ToString($h.ComputeHash($s)).Replace('-','').ToLowerInvariant()}finally{$s.Dispose();$h.Dispose()}}
function Assert-File([string]$p,$spec){if(!(Test-Path -LiteralPath $p -PathType Leaf)){throw "File missing: $p"};if((Get-Item -LiteralPath $p).Length -ne $spec.size -or (Hash-File $p) -ne $spec.sha256){throw "Wrong file version or damaged file: $p"}}
function Pick([string]$title){$d=New-Object System.Windows.Forms.OpenFileDialog;$d.Title=$title;$d.Filter='Nintendo Switch package (*.nsp)|*.nsp';if($d.ShowDialog() -ne 'OK'){throw 'Cancelled'};return $d.FileName}
function Save-Json([string]$p,$data){[IO.File]::WriteAllText($p,($data|ConvertTo-Json -Depth 8),(New-Object Text.UTF8Encoding($false)))}
$lock=$null;$oldXdelta=$env:XDELTA
try{
 $env:XDELTA=$null
 $manifest=Join-Path $PSScriptRoot 'manifest.json';$m=Get-Content -LiteralPath $manifest -Raw -Encoding UTF8|ConvertFrom-Json
 if($m.version -ne '1.01' -or $m.schema -ne 'two-nsp-xdelta-v1'){throw 'Wrong package manifest'}
 if(!$BaseNsp -or !$UpdateNsp -or !$Out){Add-Type -AssemblyName System.Windows.Forms}
 if(!$BaseNsp){$BaseNsp=Pick '1/3 - Select Japanese BASE NSP (v0)'}
 if(!$UpdateNsp){$UpdateNsp=Pick '2/3 - Select UPDATE NSP (v786432 / 1.12.0)'}
 if(!$Out){$d=New-Object System.Windows.Forms.SaveFileDialog;$d.Title='3/3 - Save Korean v1.01 NSP';$d.Filter='Nintendo Switch package (*.nsp)|*.nsp';$d.FileName=$m.output.name;if($d.ShowDialog() -ne 'OK'){throw 'Cancelled'};$Out=$d.FileName}
 $BaseNsp=(Resolve-Path -LiteralPath $BaseNsp).Path;$UpdateNsp=(Resolve-Path -LiteralPath $UpdateNsp).Path;$Out=[IO.Path]::GetFullPath($Out)
 if($Out -eq $BaseNsp -or $Out -eq $UpdateNsp){throw 'Output cannot overwrite an input'}
 if([IO.Path]::GetExtension($Out) -ne '.nsp'){throw 'Output must be an .nsp file'}
 $exe=Join-Path $PSScriptRoot 'tools/xdelta3.exe';$delta=Join-Path $PSScriptRoot 'patch/game.xdelta'
 Write-Host '1/4 Checking base, update and patch hashes...';Assert-File $BaseNsp $m.inputs.base;Assert-File $UpdateNsp $m.inputs.update;Assert-File $exe $m.tool;Assert-File $delta $m.delta
 if(Test-Path -LiteralPath $Out){Assert-File $Out $m.output;Write-Host "PASS: existing output verified: $Out";exit 0}
 $parent=[IO.Path]::GetDirectoryName($Out)
 $stage=$Out+'.v1-work';$marker=Join-Path $stage 'owner.json';$identity=Hash-File $manifest
 $walk=$stage;while($walk){if(Test-Path -LiteralPath $walk){if(((Get-Item -LiteralPath $walk -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Links/junctions are not supported for output'}};$walk=[IO.Path]::GetDirectoryName($walk)}
 [IO.Directory]::CreateDirectory($parent)|Out-Null
 if(Test-Path -LiteralPath $stage){if(!(Test-Path -LiteralPath $marker)){throw 'Work folder exists without installer ownership'};$prior=Get-Content -LiteralPath $marker -Raw -Encoding UTF8|ConvertFrom-Json;if($prior.package -ne $identity -or $prior.output -ne $Out){throw 'Work folder belongs to another patch'}}else{[IO.Directory]::CreateDirectory($stage)|Out-Null;Save-Json $marker @{package=$identity;output=$Out}}
 $lock=[IO.File]::Open((Join-Path $stage 'install.lock'),'OpenOrCreate','ReadWrite','None')
 $source=Join-Path $stage 'source.bundle';$sourceOk=Join-Path $stage 'source.verified.json';$partial=Join-Path $stage 'output.partial'
 foreach($p in @($source,$sourceOk,$partial)){if((Test-Path -LiteralPath $p) -and (((Get-Item -LiteralPath $p -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)){throw 'Linked temporary file rejected'}}
 if(Test-Path -LiteralPath $sourceOk){Assert-File $source $m.source_bundle}else{
  Write-Host '2/4 Preparing the two original files...';$w=[IO.File]::Open($source,'Create','Write','None');$done=[long]0;$buf=New-Object byte[] (8MB)
  try{foreach($p in @($BaseNsp,$UpdateNsp)){$r=[IO.File]::OpenRead($p);try{while(($n=$r.Read($buf,0,$buf.Length)) -gt 0){$w.Write($buf,0,$n);$done+=$n;Write-Progress -Activity 'Preparing source' -PercentComplete ($done*100.0/$m.source_bundle.size)}}finally{$r.Dispose()}}}finally{$w.Dispose()}
  Assert-File $source $m.source_bundle;Save-Json $sourceOk @{sha256=$m.source_bundle.sha256}
 }
 Write-Host '3/4 Applying xdelta (this can take several minutes)...'
 & $exe -f -d -s $source $delta $partial
 if($LASTEXITCODE -ne 0){throw "xdelta failed (exit $LASTEXITCODE). Keep the work folder and run again."}
 Write-Host '4/4 Verifying the complete output...';Assert-File $partial $m.output
 [IO.File]::Move($partial,$Out)
 Save-Json ($Out+'.installation.json') @{version='1.01';result='PASS';base_sha256=$m.inputs.base.sha256;update_sha256=$m.inputs.update.sha256;output_sha256=$m.output.sha256;package_sha256=$identity;powershell=$PSVersionTable.PSVersion.ToString();output=$Out}
 # Delete only the installer-owned temporary source file after successful validation.
 [IO.File]::Delete($source);[IO.File]::Delete($sourceOk)
 Write-Host "PASS: $Out"
}catch{Write-Host ('FAILED: '+$_.Exception.Message) -ForegroundColor Red;exit 1}finally{if($lock){$lock.Dispose()};$env:XDELTA=$oldXdelta}
