# --- 파일명: mainwindow.py ---
import os
import json
import re
import time
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QMessageBox

from encryption import fernet
from worker import DownloaderWorker
from downloader import CURRENT_VERSION, VERSION_URL

import requests


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ECyber Downloader")
        self.resize(500, 600)

        # 기본값 설정
        self.download_dir = os.getcwd()
        self.downloader_worker = None
        self.worker_thread = None
        self.subjects = []
        self.log_level = "DEBUG"
        self.headless = False  # Headless 옵션을 저장할 변수

        # UI 초기화
        self.setup_ui()

        # 설정 & 자격증명 로드
        self.load_config()
        if os.path.exists("credentials.json"):
            self.save_credentials_checkbox.setChecked(True)
            self.load_credentials()

        # 프로그램 시작 시 버전 체크
        self.check_for_update()

    def setup_ui(self):
        """
        UI 레이아웃 및 메뉴바 구성
        """
        # 스타일시트
        self.light_style = """
            QWidget {
                font-family: "Segoe UI", sans-serif;
                font-size: 14px;
                color: #333333;
                background-color: #ffffff;
            }
            QMainWindow {
                background-color: #f0f0f0;
            }
            QGroupBox {
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                margin-top: 10px;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
                color: #0078D7;
                font-weight: bold;
            }
            QPushButton {
                background-color: #0078D7;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                color: white;
            }
            QPushButton:hover {
                background-color: #005A9E;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #888888;
            }
            QLineEdit, QComboBox, QTextEdit {
                background-color: #ffffff;
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                padding: 4px;
            }
            QTextEdit {
                background-color: #f7f7f7;
            }
            QMenuBar {
                background-color: #0078D7;
                color: white;
            }
            QMenuBar::item {
                background: transparent;
            }
            QMenuBar::item:selected {
                background: #005A9E;
            }
            QMenu {
                background-color: #ffffff;
                border: 1px solid #d0d0d0;
            }
            QMenu::item:selected {
                background-color: #0078D7;
                color: white;
            }
        """

        self.dark_style = """
            QWidget {
                font-family: "Segoe UI", sans-serif;
                font-size: 14px;
                color: #e0e0e0;
                background-color: #2b2b2b;
            }
            QMainWindow {
                background-color: #2b2b2b;
            }
            QGroupBox {
                border: 1px solid #555555;
                border-radius: 6px;
                margin-top: 10px;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
                color: #0099ff;
                font-weight: bold;
            }
            QPushButton {
                background-color: #0099ff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                color: white;
            }
            QPushButton:hover {
                background-color: #007acc;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
            QLineEdit, QComboBox, QTextEdit {
                background-color: #3c3f41;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px;
                color: #e0e0e0;
            }
            QTextEdit {
                background-color: #3c3f41;
            }
            QMenuBar {
                background-color: #3c3f41;
                color: #e0e0e0;
            }
            QMenuBar::item {
                background: transparent;
            }
            QMenuBar::item:selected {
                background: #555555;
            }
            QMenu {
                background-color: #3c3f41;
                border: 1px solid #555555;
            }
            QMenu::item:selected {
                background-color: #0099ff;
                color: white;
            }
        """

        self.setStyleSheet(self.light_style)

        # 메뉴바
        menubar = self.menuBar()

        # View 메뉴
        view_menu = menubar.addMenu("View")
        self.dark_theme_action = QtWidgets.QAction("다크테마", self)
        self.dark_theme_action.setCheckable(True)
        self.dark_theme_action.triggered.connect(self.toggle_dark_theme)
        view_menu.addAction(self.dark_theme_action)

        # Options 메뉴
        options_menu = menubar.addMenu("Options")

        # Chrome 강제 종료
        chrome_terminate_action = QtWidgets.QAction("Chrome 강제 종료", self)
        chrome_terminate_action.triggered.connect(self.force_stop_chrome)
        options_menu.addAction(chrome_terminate_action)

        # Headless Mode
        self.headless_action = QtWidgets.QAction("Headless Mode", self)
        self.headless_action.setCheckable(True)
        self.headless_action.setChecked(self.headless)
        self.headless_action.triggered.connect(self.toggle_headless)
        options_menu.addAction(self.headless_action)

        # 로그 레벨 서브메뉴
        log_level_menu = options_menu.addMenu("Log Level")
        log_level_group = QtWidgets.QActionGroup(self)

        log_level_debug = QtWidgets.QAction("DEBUG", self, checkable=True)
        log_level_info = QtWidgets.QAction("INFO", self, checkable=True)
        log_level_warning = QtWidgets.QAction("WARNING", self, checkable=True)

        log_level_group.addAction(log_level_debug)
        log_level_group.addAction(log_level_info)
        log_level_group.addAction(log_level_warning)

        if self.log_level == "DEBUG":
            log_level_debug.setChecked(True)
        elif self.log_level == "INFO":
            log_level_info.setChecked(True)
        elif self.log_level == "WARNING":
            log_level_warning.setChecked(True)

        log_level_debug.triggered.connect(lambda: self.set_log_level("DEBUG"))
        log_level_info.triggered.connect(lambda: self.set_log_level("INFO"))
        log_level_warning.triggered.connect(lambda: self.set_log_level("WARNING"))

        log_level_menu.addAction(log_level_debug)
        log_level_menu.addAction(log_level_info)
        log_level_menu.addAction(log_level_warning)

        # Help 메뉴
        help_menu = menubar.addMenu("Help")

        # 사용법
        help_action = QtWidgets.QAction("사용법", self)
        help_action.triggered.connect(self.show_usage)
        help_menu.addAction(help_action)

        # 오픈소스 라이선스 정보 (추가 기능)
        license_action = QtWidgets.QAction("오픈소스 라이선스 정보", self)
        license_action.triggered.connect(self.show_license_info)
        help_menu.addAction(license_action)

        # 상태바
        self.statusBar().showMessage("준비됨")

        # 중앙 위젯
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 로그인 그룹
        login_group = QtWidgets.QGroupBox("로그인 및 옵션")
        login_layout = QtWidgets.QFormLayout(login_group)

        self.username_input = QtWidgets.QLineEdit()
        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)

        login_layout.addRow("Username:", self.username_input)
        login_layout.addRow("Password:", self.password_input)

        self.save_credentials_checkbox = QtWidgets.QCheckBox("로그인 정보 저장")
        self.save_credentials_checkbox.stateChanged.connect(self.on_save_credentials_changed)
        login_layout.addRow(self.save_credentials_checkbox)

        self.load_subjects_button = QtWidgets.QPushButton("과목 정보 불러오기")
        self.load_subjects_button.clicked.connect(self.load_subjects)
        login_layout.addRow(self.load_subjects_button)

        # 과목/주차 선택
        options_layout = QtWidgets.QHBoxLayout()
        self.subject_combo = QtWidgets.QComboBox()
        self.subject_combo.setMinimumWidth(250)
        self.subject_combo.addItem("전체 과목")
        self.subject_combo.currentIndexChanged.connect(self.subject_changed)

        options_layout.addWidget(QtWidgets.QLabel("과목 선택:"))
        options_layout.addWidget(self.subject_combo)

        self.week_combo = QtWidgets.QComboBox()
        self.week_combo.setEnabled(False)

        options_layout.addWidget(QtWidgets.QLabel("주차 선택:"))
        options_layout.addWidget(self.week_combo)
        login_layout.addRow(options_layout)

        main_layout.addWidget(login_group)

        # 다운로드 폴더 설정
        folder_group = QtWidgets.QGroupBox("다운로드 설정")
        folder_layout = QtWidgets.QHBoxLayout(folder_group)

        self.dir_label = QtWidgets.QLabel("다운로드 폴더:")
        self.dir_button = QtWidgets.QPushButton("폴더 선택")
        self.dir_button.clicked.connect(self.select_directory)

        folder_layout.addWidget(self.dir_label)
        folder_layout.addWidget(self.dir_button)
        folder_layout.addStretch()
        main_layout.addWidget(folder_group)

        # 로그 출력창
        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200)
        main_layout.addWidget(self.log_text, stretch=1)

        # 다운로드 시작 버튼
        self.start_download_button = QtWidgets.QPushButton("다운로드 시작")
        self.start_download_button.clicked.connect(self.start_download)
        self.start_download_button.setEnabled(False)
        main_layout.addWidget(self.start_download_button)

    def show_license_info(self):
        """
        오픈소스 라이선스 정보 메시지 박스/다이얼로그를 표시한다.
        이 프로그램의 라이선스는 MIT이며, 사용된 주요 라이브러리의 라이선스 정보를 간략히 고지한다.
        """
        msg = (
            "[본 프로그램]\n"
            " - License: MIT License\n\n"
            "[사용 오픈소스 라이브러리]\n"
            "1) requests: Apache License 2.0\n"
            "2) tqdm: MIT License\n"
            "3) cryptography: Apache License 2.0 혹은 BSD License\n"
            "4) moviepy: MIT License\n"
            "5) PyQt5: GPL v3\n"
            "6) Selenium(WebDriver): Apache License 2.0\n\n"
            "각 라이브러리의 자세한 라이선스 전문은 해당 라이브러리 배포본이나 공식 저장소에서 확인하실 수 있습니다."
        )
        QMessageBox.information(self, "오픈소스 라이선스 정보", msg)

    def set_log_level(self, level):
        self.log_level = level
        self.append_log(f"[INFO] 로그 레벨이 {level}(으)로 설정되었습니다.")

    def toggle_headless(self, checked):
        self.headless = checked
        self.append_log(f"[INFO] Headless Mode {'사용' if checked else '해제'}됨.")

    def append_log(self, message):
        """
        현재 설정된 log_level 이하의 중요도를 가진 로그만 출력
        """
        level_order = {"DEBUG": 0, "INFO": 1, "WARNING": 2}
        msg_level = "INFO"
        if message.startswith("[DEBUG]"):
            msg_level = "DEBUG"
        elif message.startswith("[WARNING]"):
            msg_level = "WARNING"
        if level_order[msg_level] >= level_order[self.log_level]:
            self.log_text.append(message)
        self.statusBar().showMessage(message, 3000)

    def toggle_dark_theme(self, checked):
        """
        다크테마 / 라이트테마 전환
        """
        if checked:
            self.setStyleSheet(self.dark_style)
            self.append_log("[INFO] 다크테마 적용됨.")
        else:
            self.setStyleSheet(self.light_style)
            self.append_log("[INFO] 라이트 테마 적용됨.")
        self.save_config()

    def force_stop_chrome(self):
        """
        실행 중인 Selenium(Chrome driver) 종료
        """
        if self.downloader_worker:
            self.downloader_worker.quit()
            self.append_log("Chrome driver 강제 종료됨.")
        else:
            self.append_log("실행 중인 Chrome driver가 없습니다.")

    def show_usage(self):
        """
        사용 안내
        """
        instructions = (
            "사용법 안내:\n\n"
            "1. 사용자 이름과 비밀번호를 입력하고 '로그인 정보 저장'을 선택하면 암호화되어 저장됩니다.\n"
            "2. '과목 정보 불러오기' 버튼을 누르면 워커가 Chrome을 띄워 로그인 후 전체 과목 목록을 불러옵니다.\n"
            "3. 특정 과목 선택 시, 해당 과목의 주차/강의 스크립트를 모두 로드하고, UI에는 '사용 가능한 주차'만 보여줍니다.\n"
            "4. 다운로드 폴더를 지정 후 '다운로드 시작'을 누르면 해당 과목/주차의 강의를 다운로드하며, mp3 변환까지 수행합니다.\n"
            "5. 진행 상황은 로그 창에 표시됩니다.\n"
            "6. Options 메뉴에서 Chrome 강제 종료, Headless Mode, 로그 레벨 등을 설정할 수 있습니다.\n"
            "7. 2차 본인인증 창이 뜨면, 인증 후 확인 버튼을 눌러주세요."
        )
        QMessageBox.information(self, "사용법", instructions)

    def on_save_credentials_changed(self, state):
        if state == QtCore.Qt.Unchecked:
            if os.path.exists("credentials.json"):
                os.remove("credentials.json")
                self.append_log("[INFO] 저장된 로그인 정보 삭제됨.")

    def load_config(self):
        """
        config.json 로드
        """
        config_file = "config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                download_folder = data.get("download_folder", "")
                if download_folder and os.path.isdir(download_folder):
                    self.download_dir = download_folder
                    self.dir_label.setText(f"다운로드 폴더: {download_folder}")

                save_credentials = data.get("save_credentials", False)
                self.save_credentials_checkbox.setChecked(save_credentials)

                theme = data.get("theme", "light")
                if theme == "dark":
                    self.setStyleSheet(self.dark_style)
                    self.dark_theme_action.setChecked(True)
                else:
                    self.setStyleSheet(self.light_style)
                    self.dark_theme_action.setChecked(False)
            except Exception as e:
                self.append_log(f"[WARNING] 설정 로드 에러: {str(e)}")

    def save_config(self):
        """
        config.json 저장
        """
        config_file = "config.json"
        theme = "dark" if self.dark_theme_action.isChecked() else "light"
        data = {
            "download_folder": self.download_dir,
            "save_credentials": self.save_credentials_checkbox.isChecked(),
            "theme": theme
        }
        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as e:
            self.append_log(f"[WARNING] 설정 저장 에러: {str(e)}")

    def load_credentials(self):
        """
        credentials.json 로드 (복호화)
        """
        if os.path.exists("credentials.json"):
            try:
                with open("credentials.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.username_input.setText(fernet.decrypt(data.get("username", "").encode()).decode())
                self.password_input.setText(fernet.decrypt(data.get("password", "").encode()).decode())
                self.append_log("[INFO] 저장된 로그인 정보를 불러왔습니다.")
            except Exception as e:
                self.append_log(f"[WARNING] 자격증명 로드 에러: {str(e)}")

    def save_credentials(self):
        """
        credentials.json 저장 (암호화)
        """
        if self.save_credentials_checkbox.isChecked():
            data = {
                "username": fernet.encrypt(self.username_input.text().strip().encode()).decode(),
                "password": fernet.encrypt(self.password_input.text().strip().encode()).decode()
            }
            try:
                with open("credentials.json", "w", encoding="utf-8") as f:
                    json.dump(data, f)
                self.append_log("[INFO] 로그인 정보를 저장하였습니다.")
            except Exception as e:
                self.append_log(f"[WARNING] 자격증명 저장 에러: {str(e)}")
        else:
            if os.path.exists("credentials.json"):
                os.remove("credentials.json")
                self.append_log("[INFO] 로그인 정보 저장 파일을 삭제하였습니다.")

    def select_directory(self):
        """
        다운로드 폴더 선택
        """
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "다운로드 폴더 선택", self.download_dir)
        if directory:
            self.download_dir = directory
            self.dir_label.setText(f"다운로드 폴더: {directory}")
            self.save_config()

    def load_subjects(self):
        """
        전체 과목 목록 불러오기(Worker.setup -> get_subject_info_list).
        """
        self.save_credentials()

        # 이미 다운 중이면 막아주거나, 또는 반환
        if self.start_download_button.isEnabled():
            self.append_log("[INFO] 이미 다운로드 중이므로 과목을 다시 불러올 수 없습니다.")
            return

        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if self.downloader_worker is None:
            self.worker_thread = QtCore.QThread()
            self.downloader_worker = DownloaderWorker(
                username, password,
                self.download_dir,
                headless=self.headless
            )
            self.downloader_worker.moveToThread(self.worker_thread)

            # 시그널 연결
            self.downloader_worker.log_signal.connect(self.append_log)
            self.downloader_worker.subjects_signal.connect(self.update_subjects)
            self.downloader_worker.weeks_update_signal.connect(self.update_weeks)
            self.downloader_worker.auth_confirmation_needed.connect(self.show_auth_confirmation_dialog)

            # 다운로드 완료 시그널 -> 다운로드 시작 버튼 재활성화
            self.downloader_worker.finished_signal.connect(self.on_download_finished)

            self.worker_thread.started.connect(self.downloader_worker.setup)
            self.worker_thread.start()

            # 살짝 지연 후 load_subjects() 실행
            QtCore.QTimer.singleShot(1000, self.downloader_worker.load_subjects)
        else:
            QtCore.QMetaObject.invokeMethod(
                self.downloader_worker, "load_subjects",
                QtCore.Qt.QueuedConnection
            )

    def update_subjects(self, subjects):
        """
        과목 콤보박스 업데이트
        """
        self.subjects = subjects
        self.subject_combo.blockSignals(True)
        self.subject_combo.clear()
        self.subject_combo.addItem("전체 과목")
        for subj in subjects:
            self.subject_combo.addItem(subj.get("과목", ""))
        self.subject_combo.blockSignals(False)

        if subjects:
            self.append_log("[INFO] 과목 정보를 성공적으로 불러왔습니다.")
            self.start_download_button.setEnabled(True)
        else:
            self.append_log("[WARNING] 과목 정보를 불러오지 못했습니다.")
            self.start_download_button.setEnabled(False)

        # 주차 콤보박스 초기화
        self.week_combo.clear()
        self.week_combo.setEnabled(False)

    def subject_changed(self, index):
        """
        특정 과목 선택 시: Worker에서 주차/강의 정보를 로드 -> UI에 weeks 업데이트
        """
        self.week_combo.clear()
        self.week_combo.setEnabled(False)

        if index == 0:
            # "전체 과목"
            self.append_log("전체 과목이 선택되었습니다. (전체 주차)")
            self.start_download_button.setEnabled(True)
        else:
            subject_info = self.subjects[index - 1]
            self.append_log(f"과목 '{subject_info['과목']}' 로딩 중...")

            # "주차 정보"(실제로는 주차+강의 스크립트) 로드 -> weeks_update_signal
            self.start_download_button.setEnabled(False)
            QtCore.QMetaObject.invokeMethod(
                self.downloader_worker, "load_weeks",
                QtCore.Qt.QueuedConnection,
                QtCore.Q_ARG(dict, subject_info)
            )

    def update_weeks(self, weeks):
        """
        Worker로부터 받은 '사용 가능한 주차 목록'을 UI 콤보박스에 표시
        """
        self.week_combo.blockSignals(True)
        self.week_combo.clear()

        self.week_combo.addItem("전체 주차", userData=0)
        if weeks:
            for w in weeks:
                self.week_combo.addItem(f"{w}주", userData=w)
            self.week_combo.setEnabled(True)
            self.start_download_button.setEnabled(True)
        else:
            self.week_combo.setEnabled(False)
            self.start_download_button.setEnabled(False)

        self.week_combo.blockSignals(False)
        self.append_log(f"사용 가능한 주차: {weeks}")

    def start_download(self):
        """
        선택 과목과 주차에 대한 다운로드 실행
        (이미 Worker 측에서 '주차->강의 스크립트'를 캐싱해 둠)
        """
        if not self.download_dir or not os.path.isdir(self.download_dir):
            QMessageBox.warning(self, "다운로드 폴더", "먼저 다운로드 폴더를 지정해 주세요.")
            return

        # 버튼 비활성화
        self.start_download_button.setEnabled(False)
        self.load_subjects_button.setEnabled(False)
        self.subject_combo.setEnabled(False)
        self.week_combo.setEnabled(False)

        # 과목 정보
        if self.subject_combo.currentIndex() == 0:
            subject_info = {"과목": "전체", "eclassRoom": ""}
        else:
            subject_info = self.subjects[self.subject_combo.currentIndex() - 1]

        # 주차 정보 (0이면 "전체 주차")
        if self.week_combo.isEnabled() and self.week_combo.currentData() is not None:
            start_week = self.week_combo.currentData()
        else:
            start_week = 0

        self.append_log(f"다운로드 시작... (과목={subject_info['과목']}, start_week={start_week})")

        QtCore.QMetaObject.invokeMethod(
            self.downloader_worker, "perform_download",
            QtCore.Qt.QueuedConnection,
            QtCore.Q_ARG(dict, subject_info),
            QtCore.Q_ARG(int, start_week)
        )

    def on_download_finished(self):
        """
        모든 다운로드가 끝났을 때 버튼을 다시 활성화
        """
        self.start_download_button.setEnabled(True)
        self.load_subjects_button.setEnabled(True)
        self.subject_combo.setEnabled(True)
        self.week_combo.setEnabled(True)
        self.append_log("다운로드 작업이 완료되었습니다.")

    def show_auth_confirmation_dialog(self):
        QMessageBox.information(self, "본인인증", "본인인증 창이 표시되었습니다.\n"
        "웹 페이지에서 수동 인증 후 아래 'OK' 버튼을 누르세요.\n"
        "※ 웹 페이지에서 인증 번호 입력 후 확인 버튼 까지 눌러야 합니다.")
        self.downloader_worker.auth_confirmed_signal.emit()

    def closeEvent(self, event):
        """
        메인 윈도우 종료 시 크롬 드라이버 종료 및 쓰레드 정리
        """
        self.force_stop_chrome()
        if self.downloader_worker:
            self.downloader_worker.quit()
        if self.worker_thread:
            self.worker_thread.quit()
            if not self.worker_thread.wait(3000):
                self.append_log("[WARNING] Worker thread가 제시간에 종료되지 않았습니다.")
        event.accept()

    def check_for_update(self):
        """
        GitHub에 있는 version.json을 불러와서 현재 버전(CURRENT_VERSION)과 비교
        """
        try:
            response = requests.get(VERSION_URL, timeout=10)
            if response.status_code == 200:
                version_info = response.json()
                latest_version = version_info.get("version")
                release_date = version_info.get("release_date", "알 수 없음")
                download_url = version_info.get("download_url", "")
                notes = version_info.get("notes", "")

                if latest_version and latest_version != CURRENT_VERSION:
                    msg = (
                        f"새 버전 {latest_version}이(가) {release_date}에 출시되었습니다.\n\n"
                        f"업데이트 노트:\n{notes}\n\n"
                        f"다운로드 URL:\n{download_url}\n\n"
                        "업데이트 하시겠습니까?"
                    )
                    ret = QMessageBox.question(
                        self, "업데이트 안내", msg,
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if ret == QMessageBox.Yes:
                        QtGui.QDesktopServices.openUrl(QtCore.QUrl(download_url))
                    else:
                        self.append_log("업데이트가 취소되었습니다.")
                else:
                    self.append_log(f"현재 최신 버전입니다. (v{CURRENT_VERSION})")
            else:
                self.append_log("버전 정보를 불러올 수 없습니다.")
        except Exception as e:
            self.append_log(f"버전 체크 중 오류 발생: {e}")
