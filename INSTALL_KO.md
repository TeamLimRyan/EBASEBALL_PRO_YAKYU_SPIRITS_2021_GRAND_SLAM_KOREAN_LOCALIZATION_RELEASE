# 프로야구 스피리츠 2021 한국어 패치 v0.93 상세 설치 매뉴얼

대상은 Nintendo Switch 일본어판 **Base v0 + 업데이트 1.12.0 (v786432)**입니다.

**게임용 `game.xdelta`는 NSP/XCI에 직접 적용하는 패치가 아닙니다.** 원본 게임에서 추출한 ExeFS·RomFS 폴더에 동봉한 `install.cmd` 명령으로 적용합니다. v0.93에는 별도 `program1/exefs/main` 원본이 필요 없습니다.

## 1. 준비할 것

- Windows x64 PC. Windows PowerShell과 패키지에 포함된 xdelta3를 사용합니다. Python 설치는 필요 없습니다.
- `eBASEBALL_2021_Korean_v0.93_xdelta.zip` 전체. GitHub의 **Source code (zip)**은 설치 파일이 아닙니다.
- 본인 소유 일본어판 게임에 **1.12.0 업데이트가 실제 적용된 상태**에서 추출한 원본 ExeFS와 RomFS.
- 출력용 NTFS 드라이브와 여유 공간 16GB 이상. 원본·다운로드 ZIP·압축 해제 공간은 별도입니다.

하드링크를 지원하지 않는 드라이브에서는 설치 중 24GB 이상의 여유 공간, 최종 결과 약 14GB가 필요할 수 있습니다. NTFS에서는 두 프로그램의 같은 RomFS 파일을 하드링크로 공유하여 최종 결과가 약 7GB입니다. **출력 `RES00.RDB` 한 파일이 4GB를 넘으므로 FAT32에는 저장할 수 없습니다.**

게임용 패치와 선택 제목·아이콘 패치는 입력이 다릅니다.

| 하고 싶은 작업 | 필요한 입력 | 사용할 명령 |
|---|---|---|
| 게임 화면·텍스트·이미지 한글화 | 업데이트 적용 후 추출한 원본 폴더 | `install.cmd -Source ... -Out ...` |
| 게임 목록 제목·아이콘 변경 | 정확한 일본어판 1.12.0 업데이트 NSP | `install.cmd -ControlOnly -UpdateNsp ... -Out ...` |

기본 게임 한글화에는 **NSP 파일을 설치기에 넣지 않습니다.**

## 2. 다운로드하고 압축 풀기

1. v0.93 릴리스에서 `eBASEBALL_2021_Korean_v0.93_xdelta.zip`을 받습니다.
2. ZIP 전체를 새 폴더에 풉니다. 예: `C:/SpiritsPatch/v0.93`.
3. 다음 파일이 있는 폴더를 엽니다. 압축을 풀 때 폴더가 한 겹 더 생겼다면 `install.cmd`가 실제로 있는 안쪽 폴더를 사용합니다.

```text
v0.93/
  install.cmd
  apply_patch.ps1
  manifest.json
  README.md
  verification.json
  checksums.sha256
  LICENSES.txt
  patch/
    game.xdelta
    control_update.xdelta
  tools/
    xdelta3.exe
```

v0.91 폴더에 일부 파일만 덮어쓰지 마세요. 설치기·manifest·패치 파일이 같은 버전 한 세트여야 합니다.

## 3. 원본 추출 폴더 준비

사용하는 추출 도구 또는 에뮬레이터에서 일본어판 게임의 업데이트가 **1.12.0**인지 확인하고 한국어 모드를 비활성화한 원본 상태에서 ExeFS와 RomFS를 추출합니다. 추출 메뉴 이름과 업데이트 포함 옵션은 도구마다 다릅니다. 이 배포물에는 NSP/XCI 추출기나 키가 포함되지 않습니다.

중요한 점은 **Base 파일 위에 업데이트 폴더를 단순 복사한 것이 아니라, 업데이트가 결합된 실제 게임 파일**이어야 한다는 것입니다. ExeFS만 새 버전이거나 RomFS만 새 버전인 혼합 폴더도 사용할 수 없습니다. 추출 도구가 파일을 재압축·변환했다면 아래 원본 해시와 달라질 수 있습니다.

가장 간단한 입력 구조는 다음과 같습니다.

```text
D:/SpiritsOriginal/
  exefs/
    main
  romfs/
    cdvdroot/
      RES00.RDI
      RES00.RDB
      RES11.RDB
      RES12.RDB
      RES13.RDB
      RES14.RDB
      RES15.RDB
      RES16.RDB
      RES17.RDB
      RES18.RDB
      html_document/
        manual.htdocs/
          index.html
          img/
            pc_page_1.jpg ～ pc_page_9.jpg
```

`exefs`와 `romfs`가 다음과 같이 한 단계 아래 있어도 인식합니다.

```text
D:/SpiritsOriginal/effective/exefs/main
D:/SpiritsOriginal/effective/romfs/cdvdroot/...
```

또는:

```text
D:/SpiritsOriginal/program0/exefs/main
D:/SpiritsOriginal/program0/romfs/cdvdroot/...
```

세 구조 모두 `-Source "D:/SpiritsOriginal"`을 사용합니다. 폴더를 이중으로 넣었다면 `-Source`가 `exefs`·`romfs`, `effective`, `program0` 중 하나를 직접 찾을 수 있도록 위치를 조정하세요. 추출된 원본의 다른 파일이 함께 있어도 됩니다.

**v0.93에는 `program1` 폴더가 필요 없습니다.** 설치기는 본편의 원본 `main` 하나를 입력으로 사용해 두 프로그램 각각의 다른 한글 `main`을 만듭니다. 입력용 `main`을 복제하거나 이름을 바꾸지 마세요.

## 4. 패치 적용

1. `install.cmd`가 있는 폴더에서 PowerShell을 엽니다. 또는 PowerShell에서 다음처럼 이동합니다.

```powershell
Set-Location -LiteralPath 'C:/SpiritsPatch/v0.93'
```

2. 다음 명령에서 원본·출력 경로를 본인 환경에 맞게 바꿉니다.

```powershell
./install.cmd -Source "D:/SpiritsOriginal" -Out "D:/SpiritsKorean_v092"
```

- `-Source`: 위에서 준비한 원본 추출 폴더.
- `-Out`: 새 결과 폴더. 원본 폴더의 안쪽이나 상위 폴더를 출력으로 지정하지 않습니다.
- 공백·한글이 있는 경로는 예시처럼 따옴표로 감쌉니다.
- 명령 끝의 `-Out`에는 `.nsp` 파일명이 아닌 **폴더 이름**을 넣습니다.

설치기는 원본·패치의 크기와 SHA-256을 확인하고, 임시 원본 스트림을 만든 뒤 xdelta를 적용합니다. 결과 파일마다 진행 줄이 표시됩니다. 대형 파일을 처리할 때는 다음 진행 줄까지 시간이 걸릴 수 있습니다.

마지막에 **`PASS: all 42 game files match v0.93.`**가 포함된 메시지가 나오면 파일 생성이 완료된 것입니다. 출력 안의 `install_report.json`에는 배포 버전 `0.93`가 기록됩니다.

## 5. 에뮬레이터에 설치

먼저 실행 중인 게임을 종료합니다. 기존 한국어 모드를 비활성화하고, 같은 위치의 파일을 여러 버전으로 섞지 않습니다.

생성 결과에는 **두 title ID**가 있습니다.

```text
SpiritsKorean_v092/
  0100F88012E34000/
    KoreanPatch/
      exefs/main
      romfs/cdvdroot/...
  0100F88012E34001/
    KoreanPatch/
      exefs/main
      romfs/cdvdroot/...
  install_report.json
  package-id.json
```

각각의 `KoreanPatch` 폴더를 해당 title ID의 모드 폴더로 복사합니다. 결과는 다음 형태여야 합니다.

```text
에뮬레이터 사용자 폴더/load/
  0100F88012E34000/KoreanPatch/exefs/main
  0100F88012E34000/KoreanPatch/romfs/cdvdroot/...
  0100F88012E34001/KoreanPatch/exefs/main
  0100F88012E34001/KoreanPatch/romfs/cdvdroot/...
```

`KoreanPatch/KoreanPatch`처럼 이중 폴더가 되면 안 됩니다. `install_report.json`이나 설치용 `.v092-stage` 폴더를 모드로 넣지 않습니다. 두 `main`은 서로 다른 파일이므로 한쪽을 다른 title ID로 복제하지 않습니다.

PC에서는 에뮬레이터의 모드 폴더 열기 기능이나 사용자 데이터 폴더를 통해 설치합니다. 에뮬레이터 설정에 모드 활성화 항목이 있다면 `KoreanPatch`를 활성화하고 1.12.0 업데이트도 유지합니다.

Odin의 Eden에서 이 프로젝트에 사용한 경로는 아래와 같습니다. 에뮬레이터 종류·패키지명이 다르면 경로도 달라집니다.

```text
/sdcard/Android/data/dev.eden.eden_emulator/files/load/0100F88012E34000/KoreanPatch/
/sdcard/Android/data/dev.eden.eden_emulator/files/load/0100F88012E34001/KoreanPatch/
```

Android의 앱 데이터 폴더 접근이 제한된 경우에는 해당 에뮬레이터가 제공하는 사용자 폴더 접근 방법을 사용합니다. 이 패키지의 설치 명령은 Windows용이므로 Windows에서 결과를 만든 뒤 두 모드 폴더를 기기로 옮깁니다.

## 6. Atmosphère용 결과 만들기

에뮬레이터용 대신 Atmosphère용 폴더 구조가 필요하면 다음처럼 실행합니다.

```powershell
./install.cmd -Source "D:/SpiritsOriginal" -Out "D:/SpiritsKorean_Atmosphere_v092" -Layout atmosphere
```

생성되는 구조:

```text
SpiritsKorean_Atmosphere_v092/
  atmosphere/contents/0100F88012E34000/exefs/main
  atmosphere/contents/0100F88012E34000/romfs/...
  atmosphere/contents/0100F88012E34001/exefs/main
  atmosphere/contents/0100F88012E34001/romfs/...
```

출력의 `atmosphere` 폴더를 저장장치 루트에 맞춰 복사합니다. **대형 RDB 때문에 FAT32에는 복사할 수 없습니다.** 기존 저장장치를 이 작업만을 위해 포맷하거나 세이브를 삭제하지 마세요. 파일 시스템이 맞지 않으면 해당 저장장치에 이 배포 결과를 그대로 설치할 수 없습니다.

## 7. 제목·아이콘 변경 — 선택 사항

이 단계는 게임 목록에 보이는 제목·아이콘을 바꾸기 위한 별도 기능입니다. 기본 게임 한글화 모드를 만들 때는 필요 없습니다.

입력은 본편 NSP가 아니라 정확한 일본어판 **1.12.0 업데이트 NSP**입니다.

```powershell
./install.cmd -ControlOnly -UpdateNsp "D:/Spirits_Update_1.12.0.nsp" -Out "D:/Spirits_Control_v092.nsp"
```

이번 명령의 `-Out`은 폴더가 아니라 **새 NSP 파일 경로**입니다. `PASS` 후 생성된 파일을 에뮬레이터의 업데이트 설치 기능으로 설치합니다. 원본 업데이트를 덮어쓰는 경로를 지정하지 마세요.

원본 업데이트 NSP가 다른 덤프·재패키징 파일이면 버전 표시가 같아도 해시가 다를 수 있으며 설치기가 거부합니다. 해시 검사를 끄지 마세요. 게임용 모드 설치는 이 선택 단계를 생략하고 진행할 수 있습니다.

기존 v0.9/v0.91/v0.92의 제목·아이콘 차분과 같은 파일이므로 이미 설치한 경우 다시 적용할 필요가 없습니다.

## 8. 중단 후 재개와 기존 버전 교체

- 설치 창을 닫았거나 작업이 중단됐다면 **같은 원본·출력 경로·옵션**으로 명령을 다시 실행합니다.
- 출력 옆의 `stage` 임시 작업 폴더는 재개할 때 사용할 수 있도록 그대로 둡니다.
- 완료된 같은 출력 폴더로 재실행하면 기존 결과를 확인합니다.
- v0.91에서 만든 출력·임시 폴더는 v0.93 설치를 이어가는 용도로 사용하지 않습니다. 새 `-Out` 경로를 선택합니다.
- v0.93은 2021 글꼴, 설명서 메뉴 문구, 나이·경력 단위를 수정하고 한국 대표팀 공식 명단·등번호 및 선수 데이터를 반영합니다. v0.9/v0.91/v0.92 사용자는 작은 업데이트 ZIP으로 기존 한국어 설치 결과에서 새 출력 폴더를 만들 수도 있습니다. 자세한 명령은 README.md와 업데이트 ZIP의 README_KO.txt를 따르세요.
- 새 모드를 적용할 때 이전 한국어 모드를 비활성화한 다음 이번 결과를 사용합니다. 세이브는 교체 대상이 아닙니다.

## 9. 오류 메시지별 확인 사항

| 증상·메시지 | 확인할 내용 |
|---|---|
| `install.cmd`를 찾지 못함 | PowerShell이 `install.cmd`가 있는 폴더인지 확인하고 앞에 `./`를 붙입니다. |
| `tools/xdelta3.exe` 또는 `patch/game.xdelta` 누락 | Source code ZIP이 아닌 설치 ZIP 전체를 새 폴더에 풉니다. 일부 파일만 옮기지 않습니다. |
| `Original file missing or wrong version` | `-Source` 위치, ExeFS·RomFS 둘 다 있는지, 일본어판 1.12.0 원본인지 확인합니다. 아래 원본 표와 비교합니다. |
| `program1/exefs/main` 원본을 요구함 | 구버전 v0.91 설치기를 실행 중일 수 있습니다. v0.93 ZIP을 새 폴더에 풀고 그 안의 명령을 사용합니다. |
| `Unsupported package manifest` | 설치기와 manifest 버전이 섞였습니다. 전체 v0.93 ZIP을 다시 풉니다. |
| `Wrong file size or SHA-256` | 오류 경로가 패키지 내부인지 원본인지 확인합니다. 패키지라면 다운로드·압축 해제 상태를, 원본이라면 버전·추출 상태를 확인합니다. |
| `Existing output belongs to another installation` | 다른 버전·원본·설치 방식의 출력입니다. 새 `-Out` 폴더를 선택합니다. |
| `Source and output directories must not overlap` | 원본과 출력이 같거나 서로 포함됩니다. 별도의 형제 폴더처럼 겹치지 않는 경로를 선택합니다. |
| `xdelta failed`, `Truncated xdelta output`, `Decoded ... mismatch` | 창의 전체 오류와 진단 JSON을 보존합니다. 저장 공간·출력 드라이브 파일 시스템·패키지 버전을 확인합니다. 해시 검사를 제거하거나 임시 결과를 설치하지 않습니다. |
| 4GB 부근에서 복사 실패 | FAT32 제한인지 확인합니다. `RES00.RDB`가 4GB보다 큽니다. |
| PASS지만 게임이 일본어임 | 실제 사용 중인 에뮬레이터 사용자 폴더, 두 title ID 경로, 모드 활성화, 이중 폴더 여부와 업데이트 버전을 확인합니다. |
| 한 시즌만 적용되거나 전환 후 문제가 생김 | 두 title ID 모두 설치했는지 확인합니다. 한쪽 `main`을 다른 쪽에 복사하지 않습니다. 알려진 에뮬레이터 제한도 확인합니다. |

## 10. 파일 해시 확인과 오류 제보

원본 `main` 해시를 확인하는 예:

```powershell
Get-FileHash -LiteralPath 'D:/SpiritsOriginal/exefs/main' -Algorithm SHA256
```

패키지 내부 파일별 해시는 `checksums.sha256`, 설치 입력·출력의 크기와 해시는 `manifest.json`에 있습니다. PowerShell 해시가 대문자로 표시되는 것은 문제가 아닙니다.

출력 경로를 `D:/SpiritsKorean_v092`로 지정한 경우 진단 파일은 다음 위치에 생성됩니다.

```text
D:/.SpiritsKorean_v092.v092-diagnostic.json
```

성공 기록은 `D:/SpiritsKorean_v092/install_report.json`입니다. 아주 초기 오류에서는 진단 파일이 아직 없을 수 있으므로 PowerShell 오류 문구도 함께 보존합니다.

제보 시 패치 버전, 실행한 명령의 경로를 가린 사본, 전체 오류 문구, 진단 JSON, 원본 파일 SHA-256, Windows·에뮬레이터 버전을 적어 주세요. **게임 원본·키·펌웨어·세이브는 첨부하지 마세요.**

## 11. 제거와 복구

게임 한글화는 이번에 설치한 두 `KoreanPatch` 모드를 비활성화하거나 제거하면 됩니다. 다른 모드·게임 원본·세이브는 지우지 않습니다. Atmosphère에서는 이번 패치가 추가한 파일만 구분해 제거합니다.

선택 제목·아이콘 변경은 원본 1.12.0 업데이트를 다시 설치하면 되돌릴 수 있습니다. 에뮬레이터의 전체 사용자 데이터나 세이브를 초기화할 필요는 없습니다.

## 12. 지원 범위와 알려진 제한

- 새 게임 xdelta와 기존 한국어 패치용 업데이트 차분을 만듭니다. 정확한 설치·왕복·배포 검증 결과는 동봉 verification.json 및 릴리스 검증 기록에 있습니다.
- 별도 Nintendo 시스템 키보드를 사용하는 온라인 닉네임 경로는 추가 작업 대상입니다.
- PC Eden 0.2.1의 2021 시즌 전환 종료는 일본어 원본에서도 재현된 기록이 있습니다. 이번 xdelta 재빌드가 에뮬레이터 문제를 해결한다는 의미는 아닙니다.
- Eden 0.2.1 Windows에서 업데이트 NSP 설치 중 종료도 원본 업데이트에서 관측됐습니다. 기본 게임용 모드와 선택 제목·아이콘 NSP 설치를 구분합니다.
- 기존 일본어 세이브의 일부 사용자 지정 한자 이름은 다르게 표시될 수 있습니다. 세이브를 백업한 뒤 게임 안에서 이름을 새로 입력하세요.
- 동영상 2개·의성어 효과 이미지 611개 및 원본 유지로 결정한 이미지는 원본입니다. 모든 경기·육성 이벤트의 장시간 전수 플레이를 완료한 것은 아닙니다.

## 부록 A. 필요한 원본 파일 21개

아래 경로는 `effective/`·`program0/`를 제외한 ExeFS·RomFS 기준입니다. `main`은 두 출력 실행 파일의 입력으로 재사용하지만 준비할 원본은 하나입니다.

| 원본 상대 경로 | 크기(bytes) | SHA-256 |
|---|---:|---|
| `exefs/main` | 21985677 | `dbf86017d51b7cff69dca33ea05a93f290cce031ab01e19899a74c3bc05ca809` |
| `romfs/cdvdroot/RES00.RDB` | 4455587840 | `6521eaf9d6c7f8e4ea629240b0894815d4fdbd9b5e42e6a88e796dbaff67004c` |
| `romfs/cdvdroot/RES00.RDI` | 256000 | `eca845300424c915247a5adaa2afd74e49c6d4bc64dc9b436d6a91a6dba10767` |
| `romfs/cdvdroot/RES11.RDB` | 408441344 | `9e60314563b1f01f40cd144c9df1a7a9d3f97c570ee05c687d6bea0748fee2ce` |
| `romfs/cdvdroot/RES12.RDB` | 48382464 | `cb35f60037e15e1de729f7ddbeb99a8ca6635ffe4797a4bdd7ea1dfa448bd0ce` |
| `romfs/cdvdroot/RES13.RDB` | 82171904 | `9873027927c541b527e3ed4afce25320c66e8307b85168d17a41ee9c67ae4dd6` |
| `romfs/cdvdroot/RES14.RDB` | 27355648 | `0d17b24fa21d613b641cc9274481ba5fa1b54efef00e243c40d3eb9fbba62074` |
| `romfs/cdvdroot/RES15.RDB` | 47186944 | `5b83c60694217bdeb02f6adfaae4b4f34ae0592b07938de1694fb25b04f80b86` |
| `romfs/cdvdroot/RES16.RDB` | 49110528 | `fa1fe4d5543b0c501540c4fb599f0e7346515b63765cf07ef61dae43d12d32b9` |
| `romfs/cdvdroot/RES17.RDB` | 725687296 | `dde4a95bfc22540e03d01009af803c9527c4221a681a7996f0266b110ad10f8a` |
| `romfs/cdvdroot/RES18.RDB` | 124851712 | `9416b4a03ae5063ef6275d0e21e6680f46b8968a18da9fdbdc8c951e0b47113c` |
| `romfs/cdvdroot/html_document/manual.htdocs/img/pc_page_1.jpg` | 254475 | `26390b48960311cb6288d13b1c4f9613a68dd72b633e60db997cb9236678c141` |
| `romfs/cdvdroot/html_document/manual.htdocs/img/pc_page_2.jpg` | 821538 | `ce2e967b30071c0b85be5e87b1fca88e0d252ddd447e2a3d8c47b10683136a66` |
| `romfs/cdvdroot/html_document/manual.htdocs/img/pc_page_3.jpg` | 961512 | `9b26e26c3b1330304ea077f7885e2a703ef9445a4fbf6a128cabf113923cf55b` |
| `romfs/cdvdroot/html_document/manual.htdocs/img/pc_page_4.jpg` | 829899 | `69de23c7cf50813f3b7da9c80ef93577eff4e84ea070b054aa9906647647d0ed` |
| `romfs/cdvdroot/html_document/manual.htdocs/img/pc_page_5.jpg` | 819651 | `da51f6741af1b1ba82fb8a5d82d2aa3b64c2c416b5d439065ff2d88b4b4ccd49` |
| `romfs/cdvdroot/html_document/manual.htdocs/img/pc_page_6.jpg` | 1035529 | `1c8e2d275f6bb33fdddf6803741419a9e07a3ae82dd38f83bafdc9dc69bcac14` |
| `romfs/cdvdroot/html_document/manual.htdocs/img/pc_page_7.jpg` | 851321 | `26c64aa8eabae3e72e98b6f73633177d39d697543447994f2c997cbb93d39abd` |
| `romfs/cdvdroot/html_document/manual.htdocs/img/pc_page_8.jpg` | 996875 | `4caf9f628219f46e29c40885deef1390434c27e8207040755662e9358f6d78d1` |
| `romfs/cdvdroot/html_document/manual.htdocs/img/pc_page_9.jpg` | 465384 | `6d8668fa7222abc9f2a59bf3e696dfdc052fec136f34bbddd921285926aaa247` |
| `romfs/cdvdroot/html_document/manual.htdocs/index.html` | 1495 | `f9b107b1f7d9fad2a56d6ee895ff94d529eaaf5c3895f337488357a264123b31` |

## 부록 B. 선택 제목·아이콘 패치 입력

- 원본 업데이트 NSP: 1603224632 bytes
- 원본 SHA-256: `40fd8c9284d45909b03f804653e4ee038d7401c30b34b5726231ce121d244f4a`
- 생성 NSP SHA-256: `555aa6d70370f45d71ddf3e25a4b2d7dfacb7a729b3b3e00413918e90fc2c6b2`

## 다운로드 및 권리 안내

[v0.93 릴리스](https://github.com/TeamLimRyan/EBASEBALL_PRO_YAKYU_SPIRITS_2021_GRAND_SLAM_KOREAN_LOCALIZATION_RELEASE/releases/tag/v0.93) · [설치 ZIP](https://github.com/TeamLimRyan/EBASEBALL_PRO_YAKYU_SPIRITS_2021_GRAND_SLAM_KOREAN_LOCALIZATION_RELEASE/releases/download/v0.93/eBASEBALL_2021_Korean_v0.93_xdelta.zip)

비공식 팬 번역 패치이며 KONAMI 및 원작 권리자와 관계가 없습니다. 원본 게임·키·펌웨어·세이브는 포함하지 않습니다. 도구·글꼴 등의 라이선스는 설치 ZIP의 `LICENSES.txt`를 참고하세요.
