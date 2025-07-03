# OnBoard OLED Monitor - EXE 빌드 가이드

## 📖 개요

OnBoard OLED Monitor를 독립 실행 파일(EXE)로 빌드하는 자동화 스크립트입니다.

## 🚀 빠른 시작

### 1단계: 빌드 실행
```bash
# Python/OLED_Monitor 폴더에서 실행
build_installer.bat
```

### 2단계: 실행
```bash
# 생성된 run 폴더에서
start_monitor.bat
# 또는
OnBoard_OLED_Monitor.exe
```

## 📁 파일 구조

```
OnBoard_FW/
├── Python/OLED_Monitor/
│   ├── oled_monitor.py       # 메인 프로그램
│   ├── build_installer.bat   # 빌드 스크립트
│   ├── create_icon.py        # 아이콘 생성기
│   └── BUILD_README.md       # 이 파일
└── run/                      # 빌드 결과물
    ├── OnBoard_OLED_Monitor.exe
    ├── start_monitor.bat
    └── README.txt
```

## 🛠️ 빌드 과정

`build_installer.bat` 실행시 다음 단계들이 자동으로 진행됩니다:

### 1. 환경 확인
- Python 설치 여부 확인
- pip 설치 여부 확인
- 경로 설정

### 2. 필수 패키지 설치
- PyInstaller (EXE 빌드 도구)
- Pillow (이미지 처리)
- NumPy (수치 계산)
- pyserial (시리얼 통신)

### 3. run 폴더 생성
- 프로젝트 루트에 `run` 폴더 생성
- 기존 파일 백업 (필요시)

### 4. 아이콘 생성
- `create_icon.py` 실행
- OnBoard OLED Monitor 전용 아이콘 생성
- 실패시 기본 아이콘 없이 진행

### 5. 기존 빌드 파일 정리
- `build`, `dist` 폴더 삭제
- 이전 `.spec` 파일 제거

### 6. EXE 파일 빌드
PyInstaller를 사용하여 독립 실행 파일 생성:
- `--onefile`: 단일 EXE 파일
- `--windowed`: 콘솔 창 숨김
- `--optimize 2`: 최적화 적용
- 필수 모듈들 포함

### 7. 결과 확인
- 생성된 EXE 파일 검증
- 파일 크기 확인

### 8. run 폴더로 이동
- EXE 파일을 `run` 폴더로 복사
- 경로 확인

### 9. 정리 작업
- 임시 빌드 파일들 삭제
- `build`, `dist` 폴더 제거
- `.spec` 파일 삭제

## 📦 생성되는 파일들

### run 폴더 내용:
- **OnBoard_OLED_Monitor.exe**: 메인 실행 파일 (독립 실행)
- **start_monitor.bat**: 실행 헬퍼 스크립트
- **README.txt**: 사용자 가이드

## 💡 사용 방법

### 직접 실행
```bash
OnBoard_OLED_Monitor.exe
```

### 스크립트로 실행
```bash
start_monitor.bat
```

## ⚠️ 주의사항

### Windows Defender
- 처음 실행시 Windows Defender가 차단할 수 있습니다
- "추가 정보" → "실행" 클릭하여 허용
- 또는 예외 목록에 추가

### 시스템 요구사항
- Windows 10/11 (64-bit)
- 4GB RAM 이상 권장
- 시리얼 포트 드라이버

### 문제 해결
1. **실행 안됨**: Windows Defender 설정 확인
2. **COM 포트 없음**: 드라이버 재설치
3. **연결 실패**: 다른 프로그램이 포트 사용 중인지 확인

## 🔧 고급 설정

### 아이콘 커스터마이징
1. `icon.ico` 파일을 직접 제공
2. 또는 `create_icon.py` 수정

### 빌드 옵션 변경
`build_installer.bat`에서 PyInstaller 옵션 수정:
```bash
pyinstaller ^
    --onefile ^           # 단일 파일
    --windowed ^          # 창 모드
    --name "이름" ^       # 실행 파일 이름
    --icon="경로" ^       # 아이콘 파일
    ...
```

## 📋 버전 정보

- **버전**: v1.4 - Request-Response Protocol
- **빌드 도구**: PyInstaller
- **지원 OS**: Windows 10/11
- **파이썬 버전**: 3.8+

## 🐛 문제 보고

빌드나 실행 중 문제가 발생하면:
1. 오류 메시지 확인
2. 로그 파일 확인
3. 시스템 요구사항 재확인

## 📞 지원

- 프로젝트: OnBoard LED Timer
- 도구: OLED Monitor v1.4
- 문의: 개발팀 