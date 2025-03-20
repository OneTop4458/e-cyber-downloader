# ECyberDownloader

![ECyberDownloader Logo](assets/icon.ico)

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
│   ├── downloader.py  # 다운로드 관련 코드
│   ├── encryption.py  # 암호화 기능
│   ├── ui.py  # GUI 코드
│   ├── utils.py  # 기타 유틸리티 함수
│── 📂 assets/  # 아이콘, 리소스 폴더
│── requirements.txt  # 의존성 목록
│── README.md  # 프로젝트 설명서
```

## ⚙ 설정 파일 (`config/config.json`)
```json
{
  "download_folder": "C:/ECyberDownloads",
  "save_credentials": true,
  "theme": "light"
}
```

## 📝 사용법
1. `config.json`을 편집하여 다운로드 폴더 설정
2. 실행 후 로그인 정보 입력
3. 다운로드할 강의 선택 후 시작

## 🛠 문제 해결
- **로그인 오류 발생 시**: `credentials.json`을 삭제하고 다시 시도
- **다운로드 실패**: `Chrome WebDriver`가 최신인지 확인 (`chromedriver_autoinstaller` 사용)
- **exe 실행 오류**: `build_exe.bat` 실행 후 `dist/ECyberDownloader.exe` 확인

## 📜 라이선스
MIT License

