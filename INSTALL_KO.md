# v0.9 설치 안내

Windows x64와 Python 3.10 이상이 필요합니다. 설치 패키지 전체를 같은 폴더에 풀어 주세요.

본인이 보유한 일본어판 Base v0와 Update v786432(1.12.0)를 합친 **원본 추출본**, 그리고 **원본 Update NSP**가 필요합니다. Base RomFS에 업데이트 파일을 단순히 복사한 폴더는 올바른 추출본이 아닙니다. 이 설치기는 NSP를 복호화하거나 콘솔 키를 요청하지 않습니다.

원본 추출 폴더 구조:

```text
원본추출/
  effective/exefs/main
  effective/romfs/cdvdroot/RES00.RDI
  effective/romfs/cdvdroot/RES00.RDB, RES11.RDB ... RES18.RDB
  effective/romfs/cdvdroot/html_document/manual.htdocs/index.html
  effective/romfs/cdvdroot/html_document/manual.htdocs/img/pc_page_1.jpg ... pc_page_9.jpg
  program1/exefs/main
```

원본 파일의 정확한 크기·SHA-256은 `manifest.json`에 있습니다. 출력을 저장할 드라이브에 약 16GB의 여유 공간을 확보하세요. NTFS에서 동일 RomFS는 하드링크로 공유합니다. 가장 큰 출력 파일은 4GB를 초과하므로 FAT32에 복사할 수 없습니다.

```bat
install.cmd --source "D:\원본추출" --update-nsp "D:\게임업데이트.nsp" --output "C:\프로스피한글패치" --layout eden
```

원본·차분·복원 결과의 SHA-256을 검사한 뒤 완료 폴더를 확정합니다. 원본은 덮어쓰지 않습니다. xdelta 차분으로 압축 전 데이터 차이를 복원하고, 동봉한 압축 구조 정보로 검증된 압축 바이트를 그대로 조립합니다. 사용자 환경에서 게임 데이터를 다시 압축하지 않습니다.

## Eden 등 에뮬레이터

완료 결과의 `0100F88012E34000/KoreanPatch`와 `0100F88012E34001/KoreanPatch`를 각각 해당 title ID의 모드 폴더에 복사합니다. 두 프로그램을 함께 설치하세요. 기존 한국어 모드와 중복 적용하지 마세요.

게임 제목과 아이콘까지 적용하려면 결과에 생성된 `eBASEBALL_2021_v1.12.0_Korean_Control_v0.9.nsp`를 게임 업데이트로 설치합니다. 원본 업데이트의 프로그램 데이터는 유지하고 Control·메타데이터만 바꾼 파일입니다.

Eden 0.2.1 Windows에서 NSP 설치 버튼을 누르면 종료되는 문제가 원본 업데이트 설치에서도 관측됐습니다. 이 경우 Eden을 완전히 종료한 후 아래 보조 설치기를 사용할 수 있습니다. Eden 사용자 폴더에서 실제 `nand/user/Contents/registered` 경로를 지정하세요. 기존 1.12.0 업데이트가 설치되어 있어야 하며, 해당 파일의 해시가 맞아야 적용됩니다. 기존 Control과 메타데이터는 옆 폴더에 백업됩니다.

```bat
python install_eden_control.py --patch-output "C:\프로스피한글패치" --registered "C:\Eden사용자폴더\nand\user\Contents\registered"
```

되돌릴 때는 같은 명령 끝에 `--restore`를 붙입니다.

## Atmosphère

명령 끝의 `--layout eden`을 `--layout atmosphere`로 바꿉니다. 결과의 `atmosphere` 폴더를 SD 카드 루트에 복사합니다. 제목·아이콘은 위에서 생성된 수정 업데이트 NSP를 설치해야 반영됩니다. 수정된 콘텐츠를 실행할 수 있는 환경이 필요합니다. Nintendo Switch 본체에서의 설치·장시간 플레이는 이번 자동 검증 범위에 포함되지 않습니다.

## 중단·재실행·제거

중단됐다면 같은 명령으로 다시 실행합니다. 출력 옆의 `.출력이름.eb2-v09-stage`에서 해시가 일치하는 완료 항목을 이어서 사용합니다. 다른 패키지·기존 사용자 폴더는 덮어쓰지 않습니다. 오류 상태는 출력 옆 `.출력이름.diagnostic.json`에 기록됩니다.

제거할 때는 이번 KoreanPatch 모드만 제거하거나 비활성화하고, 제목·아이콘을 되돌리려면 원본 1.12.0 업데이트를 다시 설치합니다. 게임 원본이나 세이브는 삭제하지 마세요. 패치 적용 전 기존 저장 데이터를 별도로 백업하세요.
