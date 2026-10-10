# 프로야구 스피리츠 2021 그랜드슬램 한국어 패치 v0.93

일본어판 Base v0 + Update **1.12.0 (v786432)** 전용 피드백 수정판입니다.

- 2021 시즌의 글꼴 처리 오류를 수정했습니다.
- 설명서 메뉴의 `수동` 오역을 `설명서`로 바꿨습니다.
- 나이와 프로 경력 단위를 `세`, `년 차`로 수정했습니다.
- 한국 대표팀 공식 명단·등번호 및 선수 데이터를 반영했습니다. 24명 대조표는 [ROSTER_KO.md](ROSTER_KO.md)에서 확인할 수 있습니다.
- 설명서·스타플레이어 종료 제보는 시험 구간에서 재현되지 않았습니다. 확인 범위는 KNOWN_ISSUES.md에 기록했습니다.

## 다운로드 선택

**처음 설치하거나 원본에서 다시 만들 때:** `eBASEBALL_2021_Korean_v0.93_xdelta.zip`

```powershell
.\install.cmd -Source "D:\원본추출" -Out "D:\한국어패치_v0.93"
```

`Source`에는 업데이트 1.12.0을 적용해 추출한 일본어 원본 ExeFS·RomFS를 지정합니다. NSP/XCI를 직접 지정하는 방식이 아닙니다. 이전 한국어 패치도 전체 패키지의 입력으로 쓸 수 없습니다.

**v0.9·v0.91·v0.92를 이미 설치했다면:** 작은 `eBASEBALL_2021_Korean_v0.93_from_v0.92.zip`

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Source "D:\기존_한국어패치" -Out "D:\한국어패치_v0.93"
```

업데이트 패키지의 `Source`는 기존 한국어 모드의 두 title ID가 들어 있는 상위 폴더입니다. 설치 결과의 `0100F88012E34000/KoreanPatch`와 `0100F88012E34001/KoreanPatch`를 각각 적용하고, 이전 모드와 중복 적용하지 마세요. 입력은 보존하며 새 출력 폴더를 사용하세요.

Windows PowerShell과 동봉 xdelta3를 사용하며 Python 설치는 필요 없습니다. Atmosphère 출력은 두 방식 모두 명령 끝에 `-Layout atmosphere`를 추가합니다. 제목·아이콘용 Control 업데이트 내용은 v0.92와 같아 기존 적용자는 다시 설치할 필요가 없습니다.

상세 원본 구조·제목 아이콘·복구 방법은 [INSTALL_KO.md](INSTALL_KO.md), 검증 범위와 제한은 [KNOWN_ISSUES.md](KNOWN_ISSUES.md), 파일 해시는 `SHA256SUMS.txt` 및 `manifest.json`을 확인하세요.

원본 게임·콘솔 키·펌웨어·세이브는 포함하지 않습니다. GitHub의 Source code ZIP은 설치 패키지가 아닙니다.
