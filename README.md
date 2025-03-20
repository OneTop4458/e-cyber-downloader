# ECyberDownloader

![ECyberDownloader Logo](assets/downloadfolderblank_99350.ico)

ECyberDownloader는 가톨릭대학교 e-Cyber 강의 자료를 자동으로 다운로드하는 프로그램입니다.

## 🔥 기능
- Selenium을 활용한 자동 로그인 및 강의 페이지 탐색
- 동영상 강의 다운로드 및 MP3 변환 지원
- PyQt5 GUI 인터페이스 제공
- 로그인 정보 암호화 저장 (cryptography 모듈 사용)
- 버전 자동 업데이트 체크 기능
- Chrome Headless Mode 지원

## 📦 설치 및 실행 방법

### 1️⃣ 필수 의존성 설치
Python 3.8+ 버전이 필요합니다.
```bash
pip install -r requirements.txt
```

### 2️⃣ 실행
```bash
python src/main.py
```

### 3️⃣ EXE 파일 생성 (선택)
PyInstaller를 사용하여 exe 파일을 생성할 수 있습니다.
```bash
build_exe.bat
```

## 📁 프로젝트 폴더 구조
```
ECyberDownloader/
│── 📂 src/
│   ├── main.py  # 실행 파일
│   ├── mainwindow.py  # 메인윈도우(UI)
│   ├── encryption.py  # 암호화 관련
│   ├── downloader.py  # Selenium 제어 로직
│   ├── worker.py  # QThread 기반 작업자
│── 📂 assets/  # 아이콘, 리소스 폴더
│── requirements.txt  # 의존성 목록
│── README.md  # 프로젝트 설명서
```

## 📝 사용법
1. 실행 후 로그인 정보 입력
2. 다운로드할 강의 선택 후 시작

## 📝 빌드 방법
```bash
cd src
pyinstaller main.py ^
  --onefile --noconsole ^
  --icon=..\assets\downloadfolderblank_99350.ico ^
  --paths=. ^
  --hidden-import=mainwindow ^
  --hidden-import=worker ^
  --hidden-import=downloader ^
  --hidden-import=encryption
```

## 🛠 문제 해결
- 문제 발생 시 Issue 생성 혹은 PR 부탁드립니다.

## 📜 라이선스
MIT License
