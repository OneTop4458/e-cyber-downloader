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
cd src
pyinstaller main.py --onefile --noconsole --icon=../assets/downloadfolderblank_99350.ico --noupx
```

## 📁 프로젝트 폴더 구조
```
ECyberDownloader/
│── 📂 src/
│   ├── main.py         # 실행 파일
│   ├── mainwindow.py   # 메인윈도우(UI)
│   ├── encryption.py   # 암호화 관련
│   ├── downloader.py   # Selenium 제어 로직
│   ├── worker.py       # QThread 기반 작업자
│── 📂 assets/          # 아이콘, 리소스 폴더
│── requirements.txt    # 의존성 목록
│── README.md           # 프로젝트 설명서
│── LICENSE             # 라이선스 정보 (MIT License + 사용된 오픈소스 라이브러리 정보)
```

## 📝 사용법
1. 프로그램 실행 후 로그인 정보를 입력합니다.
2. "과목 정보 불러오기" 버튼을 통해 강의 정보를 가져옵니다.
3. 과목 및 주차를 선택 후 "다운로드 시작" 버튼을 누릅니다.
4. 상단 Help 메뉴에서 "오픈소스 라이선스 정보" 버튼을 통해 사용된 라이브러리의 라이선스 정보를 확인할 수 있습니다.
5. Help 메뉴의 "버전 정보" 버튼을 클릭하면 현재 버전, 빌드 타임, 업데이트 내역 및 책임 경고 문구가 표시됩니다.

## 🛠 문제 해결
- 문제 발생 시 Issue 생성 혹은 PR 부탁드립니다.

## 📜 라이선스
이 프로젝트는 MIT License 하에 배포됩니다.
자세한 라이선스 정보는 프로그램 내 "오픈소스 라이선스 정보" 메뉴 또는 LICENSE 파일을 확인하시기 바랍니다.
