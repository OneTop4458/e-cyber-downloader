# ECyberDownloader

![ECyberDownloader Logo](assets/downloadfolderblank_99350.ico)

ECyberDownloader는 사이버 캠퍼스(HelloLMS) 강의 영상을 자동으로 다운로드하는 프로그램입니다.

## 🔥 기능
- 사이버 캠퍼스 강의 다운로드 및 MP3 추출

## 🔥 지원학교 목록
ECyberDownloader는 아래의 학교를 지원 합니다다.

- 가톨릭대학교 사이버캠퍼스 (e-cyber.catholic.ac.kr)
- 가톨릭상지대학교 LMS (lms.csj.ac.kr)
- 건국대학교 eCampus (ecampus.konkuk.ac.kr)
- 경남대학교 e-Class system (cyber.kyungnam.ac.kr)
- 경남정보대학교 Smart Campus (lms.kit.ac.kr)
- 경북과학대학교 학습관리시스템 (lms.kbsu.ac.kr)
- 경북도립대학교 LMS (g-lms.gpc.ac.kr)
- 경운대학교 Smart LMS (lms.ikw.ac.kr)
- 계명대학교 의과대학 LMS (medlms.kmu.ac.kr)
- 공주교육대 e-Class System (lms.gjue.ac.kr)
- 구미대학교 e-Class (eclass.gumi.ac.kr)
- 국립경북대학교 학습관리시스템(구. 국립안동대학교) (lms.andong.ac.kr)
- 국제예술대학교 LMS (cybercampus.kua.ac.kr)
- 군산대학교 e-Class system (e-class.kunsan.ac.kr)
- 군장대학교 e-Class (cyber.kunjang.ac.kr)
- 기독간호대학교 LMS (lms.ccn.ac.kr)
- 남서울대학교 LMS (lms.nsu.ac.kr)
- 대경대학교 e-Class system (eclass.tk.ac.kr)
- 대구가톨릭대학교 강의지원시스템 (lms.cu.ac.kr)
- 대구교육대학교 e-Class system (lms.dnue.ac.kr)
- 대구한의대학교 LMS (lms.dhu.ac.kr)
- 대신대학교 LMS (lms.daeshin.ac.kr)
- 대전과학기술대학교 e-Class (lms.dst.ac.kr)
- 동덕여자대학교 Smart Class System (eclass.dongduk.ac.kr)
- 동양대학교e-Class system (eclass.dyu.ac.kr)
- 동의과학대학교 LMS (arete2.dit.ac.kr)
- 명지대학교 e-Learning System (lms.mju.ac.kr)
- 목포가톨릭대학교 e-Learning (lms.mcu.ac.kr)
- 목포과학대학교 e-Class system (lms.msu.ac.kr)
- 문경대학교 Cyber Campus (cyber.mkc.ac.kr)
- 부경대학교 Smart-LMS (lms.pknu.ac.kr)
- 부산경상대학교 LMS (newlms.bsks.ac.kr)
- 부산교육대학교 차세대 LMS (blms.bnue.ac.kr)
- 부산여자대학교 LMS (lms.bwc.ac.kr)
- 삼육대학교 e-Class system (lms.suwings.syu.ac.kr)
- 삼육보건대학교 c-Class (eclass.shu.ac.kr)
- 서울과학기술대학교 e-Class system (eclass.seoultech.ac.kr)
- 서울여자대학교 e-Class system (cyber.swu.ac.kr)
- 서울예술대학교 e-Class System (eclass.seoularts.ac.kr)
- 성공희대학교 e-Class (lms.skhu.ac.kr)
- 세명대학교 강의지원시스템 (edu.semyung.ac.kr)
- 수원과학대학교 e-Class System (lms.ssc.ac.kr)
- 순천제일대학교 LMS (lms.suncheon.ac.kr)
- 신라대학교 e-Class System (cyberedu.silla.ac.kr)
- 아주자동차대학교 LMS (lms.motor.ac.kr)
- 안동과학대학교 e-Class (lms.asc.ac.kr)
- 안산대학교 e-Class system (eclass.ansan.ac.kr)
- 영남대학교 강의포털시스템 (lms.yu.ac.kr)
- 전주비전대학교 e-Class (lms.jvision.ac.kr)
- 조선대학교 Cyber Campus (clc.chosun.ac.kr)
- 진주보건대학교 LMS (lms.jhc.ac.kr)
- 창신대학교 스마트 LMS (lms.cs.ac.kr)
- 청암대학교 LMS (lms.ca.ac.kr)
- 청운대학교 e-Class system (cyber.chungwoon.ac.kr)
- 청주교육대학교 e-Class System (eclass.cje.ac.kr)
- 충신대학교 LMS (lms.csu.ac.kr)
- 춘천교육대학교 e-Class System (eclass.cnue.ac.kr)
- 평택대학교 e-Class system (cyber.ptu.ac.kr)
- 한경국립대학교 사이버캠퍼스 (cyber.hknu.ac.kr)
- 한국공학대학교 e-Class system (eclass.tukorea.ac.kr)
- 한국교원대학교 청람사이버 (et.knue.ac.kr)
- 한국복지대학교 LMS (klms.pt-hknu.ac.kr)
- 한국외국어대학교 e-Class (LMS/TMS) (eclass.hufs.ac.kr)
- 한국체육대학교 e-Class system (eclass.knsu.ac.kr)
- 한세대학교 e-Class system (eclass.hansei.ac.kr)
- 한양여자대학교 e-Class system (lms.hywoman.ac.kr)

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
This project, **e-cyber-downloader**, is licensed under the **GNU General Public License v3.0 (GPLv3)**.

By using PyQt5 (GPLv3), the entire project must also comply with GPLv3. You are free to:

- Use, modify, and redistribute the software
- As long as you also distribute your source code under the same license (GPLv3)

🔗 Full license text is available in the [LICENSE](./LICENSE) file.

### 🧩 Third-Party Libraries and Their Licenses

| Library        | License                   |
|----------------|----------------------------|
| requests       | Apache License 2.0         |
| tqdm           | MIT License                |
| cryptography   | Apache License 2.0 / BSD   |
| moviepy        | MIT License                |
| PyQt5          | **GPL v3** (Main license)  |
| Selenium       | Apache License 2.0         |

All included libraries are compatible with GPLv3.

