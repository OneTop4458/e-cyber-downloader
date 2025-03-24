# -*- coding: utf-8 -*-
import datetime
import os
import subprocess
import json
import re
import time
import random
import requests
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QMessageBox

from encryption import fernet
from worker import DownloaderWorker
from downloader import CURRENT_VERSION, VERSION_URL

# 지원 학교 목록
SCHOOLS_URL = "https://raw.githubusercontent.com/OneTop4458/e-cyber-downloader/refs/heads/main/schools.json"


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
        self.headless = False
        self.school_name = ""
        self.school_code = ""
        self.school_domain = ""
        self.weather_effect_widget = None

        # UI 초기화
        self.setup_ui()
        self.load_config()

        # 날씨 효과가 켜져 있다면 위젯 생성 (옵션 기본 on)
        if self.weather_effect_action.isChecked():
            self.create_weather_effect_widget()

        # 최초 실행 시 (또는 config에 학교 정보가 없을 경우)에만 학교 선택 다이얼로그 표시
        if not self.school_code:
            dlg = SchoolSelectionDialog(self)
            if dlg.exec_() == QtWidgets.QDialog.Accepted:
                self.school_name, self.school_code, self.school_domain = dlg.get_values()
                self.append_log(f"[INFO] 학교 선택: {self.school_name} ({self.school_code}, {self.school_domain})")
                self.save_config()
            else:
                # 선택 취소 시 기본값 적용
                self.school_name, self.school_code, self.school_domain = "가톨릭대학교", "catholic", "e-cyber.catholic.ac.kr"
                self.append_log("[INFO] 학교 선택이 취소되어 기본값이 적용되었습니다.")
                self.save_config()

        # 자격증명 로드
        if os.path.exists("credentials.json"):
            self.save_credentials_checkbox.setChecked(True)
            self.load_credentials()

        # 프로그램 시작 시 버전 체크
        self.check_for_update()

    def setup_ui(self):
        """
        UI 레이아웃 및 메뉴바 구성 (진행바 및 개선된 스타일 시트 포함)
        """
        # 스타일시트 (Light/Dark 모드 모두에 QProgressBar 스타일 추가)
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
            QProgressBar {
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                text-align: center;
                background-color: #f7f7f7;
            }
            QProgressBar::chunk {
                background-color: #0078D7;
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
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 4px;
                text-align: center;
                background-color: #3c3f41;
            }
            QProgressBar::chunk {
                background-color: #0099ff;
            }
        """

        self.setStyleSheet(self.light_style)

        # 메뉴바 구성
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

        # 날씨 효과 토글
        self.weather_effect_action = QtWidgets.QAction("날씨 효과", self)
        self.weather_effect_action.setCheckable(True)
        self.weather_effect_action.setChecked(True)  # 기본 on
        self.weather_effect_action.triggered.connect(self.toggle_weather_effects)
        options_menu.addAction(self.weather_effect_action)

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

        # 오픈소스 라이선스 정보
        license_action = QtWidgets.QAction("오픈소스 라이선스 정보", self)
        license_action.triggered.connect(self.show_license_info)
        help_menu.addAction(license_action)

        # 학교 설정
        school_settings_action = QtWidgets.QAction("학교 설정", self)
        school_settings_action.triggered.connect(self.open_school_settings)
        options_menu.addAction(school_settings_action)

        # 상태바 초기화
        self.statusBar().showMessage("준비됨")

        # 중앙 위젯 및 레이아웃 구성
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

        # 진행바 위젯 (예: 다운로드 진행률 표시)
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        # 다운로드 시작 버튼
        self.start_download_button = QtWidgets.QPushButton("다운로드 시작")
        self.start_download_button.clicked.connect(self.start_download)
        self.start_download_button.setEnabled(False)
        main_layout.addWidget(self.start_download_button)

    def show_license_info(self):
        """
        GitHub에 공개된 LICENSE 파일 내용을 가져와서 표시
        """
        license_url = "https://raw.githubusercontent.com/OneTop4458/e-cyber-downloader/refs/heads/main/LICENSE"
        try:
            response = requests.get(license_url, timeout=10)
            if response.status_code == 200:
                license_text = response.text
            else:
                license_text = "라이선스 정보를 불러올 수 없습니다. (HTTP 상태: {})".format(response.status_code)
        except Exception as e:
            license_text = f"오류 발생: {str(e)}"

        # 스크롤 가능한 다이얼로그 생성
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("오픈소스 라이선스 정보")
        layout = QtWidgets.QVBoxLayout(dialog)

        text_edit = QtWidgets.QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(license_text)
        layout.addWidget(text_edit)

        close_button = QtWidgets.QPushButton("닫기")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)

        dialog.resize(600, 400)
        dialog.exec_()

    def open_school_settings(self):
        """
        학교 설정 표시
        """
        dlg = SchoolSelectionDialog(self, current_school_name=self.school_name,
                                    current_school_code=self.school_code,
                                    current_school_domain=self.school_domain)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self.school_name, self.school_code, self.school_domain = dlg.get_values()
            self.append_log(f"[INFO] 학교 설정 변경: {self.school_name} ({self.school_code}, {self.school_domain})")
            self.save_config()

    def set_log_level(self, level):
        self.log_level = level
        self.append_log(f"[INFO] 로그 레벨이 {level}(으)로 설정되었습니다.")

    def toggle_headless(self, checked):
        self.headless = checked
        self.append_log(f"[INFO] Headless Mode {'사용' if checked else '해제'}됨.")

    def toggle_weather_effects(self, checked):
        """옵션 메뉴에서 날씨 효과 on/off"""
        if checked:
            if not self.weather_effect_widget:
                self.create_weather_effect_widget()
            else:
                self.weather_effect_widget.show()
            self.append_log("[INFO] 날씨 효과 활성화됨.")
        else:
            if self.weather_effect_widget:
                self.weather_effect_widget.hide()
            self.append_log("[INFO] 날씨 효과 비활성화됨.")
        self.save_config()

    def create_weather_effect_widget(self):
        """중앙 위젯 위에 날씨 효과 위젯을 오버레이로 추가"""
        self.weather_effect_widget = WeatherEffectWidget(self.centralWidget())
        self.weather_effect_widget.setGeometry(self.centralWidget().rect())
        self.weather_effect_widget.show()

    def append_log(self, message):
        """
        개선된 UI 로그창 출력:
        - 타임스탬프 추가
        - 로그 레벨에 따라 색상 지정
        - 다크테마일 경우 기본 텍스트 색상을 흰색 계열로 지정
        - 각 로그 항목에 여백 추가
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if message.startswith("[DEBUG]"):
            color = "gray"
        elif message.startswith("[INFO]"):
            color = "green"
        elif message.startswith("[WARNING]"):
            color = "red"
        else:
            # 다크 테마이면 흰색 계열로, 그렇지 않으면 검정색으로 지정
            if self.dark_theme_action.isChecked():
                color = "#E0E0E0"
            else:
                color = "black"
        formatted_message = (
            f'<div style="margin:4px 0;">'
            f'<span style="color:#888888; font-size:12px;">{timestamp}</span> '
            f'<span style="color:{color};">{message}</span>'
            f'</div>'
        )
        self.log_text.append(formatted_message)
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
            "6. Options 메뉴에서 Chrome 강제 종료, Headless Mode, 날씨 효과, 로그 레벨 등을 설정할 수 있습니다.\n"
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
                self.school_name = data.get("school_name", "")
                self.school_code = data.get("school_code", "")
                self.school_domain = data.get("school_domain", "")
                if download_folder and os.path.isdir(download_folder):
                    self.download_dir = download_folder
                    self.dir_label.setText(f"다운로드 폴더: {download_folder}")
                save_credentials = data.get("save_credentials", False)
                self.save_credentials_checkbox.setChecked(save_credentials)
                # 테마 설정
                theme = data.get("theme", "light")
                if theme == "dark":
                    self.setStyleSheet(self.dark_style)
                    self.dark_theme_action.setChecked(True)
                else:
                    self.setStyleSheet(self.light_style)
                    self.dark_theme_action.setChecked(False)
                # 날씨 효과 옵션
                weather_effects = data.get("weather_effects", True)
                self.weather_effect_action.setChecked(weather_effects)
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
            "theme": theme,
            "school_name": self.school_name,
            "school_code": self.school_code,
            "school_domain": self.school_domain,
            "weather_effects": self.weather_effect_action.isChecked()
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
                headless=self.headless,
                school_code=self.school_code,
                school_domain=self.school_domain
            )
            self.downloader_worker.moveToThread(self.worker_thread)
            self.downloader_worker.progress_update_signal.connect(self.progress_bar.setValue)

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

    def resizeEvent(self, event):
        """중앙 위젯 크기 변경시 날씨 효과 위젯도 같이 조정"""
        if self.weather_effect_widget:
            self.weather_effect_widget.setGeometry(self.centralWidget().rect())
        super().resizeEvent(event)

    def closeEvent(self, event):
        """
        메인 윈도우 종료 시 크롬 드라이버 종료 및 쓰레드 정리
        """
        self.append_log("[INFO] 프로그램 종료를 시도합니다...")

        # 1) Worker가 동작 중이면 안전하게 종료 시도
        if self.downloader_worker is not None:
            try:
                self.downloader_worker.quit()
            except Exception as e:
                self.append_log(f"[WARNING] downloader_worker 종료 중 오류: {e}")

        # 2) QThread 종료 (백그라운드 Worker thread)
        if self.worker_thread is not None:
            try:
                self.worker_thread.requestInterruption()
                self.worker_thread.quit()
                if not self.worker_thread.wait(3000):
                    self.append_log("[WARNING] Worker thread가 제시간에 종료되지 않았습니다.")
            except Exception as e:
                self.append_log(f"[WARNING] Worker thread 종료 중 오류: {e}")

        # 3) chromedriver.exe 프로세스 모두 강제 종료
        try:
            subprocess.call("taskkill /f /im chromedriver.exe", shell=True)
        except Exception as e:
            self.append_log(f"[WARNING] chromedriver 종료 중 오류: {e}")

        event.accept()

    def check_for_update(self):
        """
        GitHub에 있는 version.json을 불러와서 현재 버전(CURRENT_VERSION)과 비교하고,
        새 버전이 있으면 현재 실행 파일(자기 자신)을 업데이트 파일로 교체합니다.
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
                        "업데이트 하시겠습니까?"
                    )
                    dlg = QMessageBox(self)
                    dlg.setWindowTitle("업데이트 안내")
                    dlg.setText(msg)
                    dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                    dlg.setWindowFlags(dlg.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
                    ret = dlg.exec_()
                    if ret == QMessageBox.Yes:
                        self.perform_update(download_url, latest_version)
                    else:
                        self.append_log("업데이트가 취소되었습니다.")
                else:
                    self.append_log(f"현재 최신 버전입니다. (v{CURRENT_VERSION})")
            else:
                self.append_log("버전 정보를 불러올 수 없습니다.")
        except Exception as e:
            self.append_log(f"버전 체크 중 오류 발생: {e}")

    def perform_update(self, download_url, latest_version):
        """
        업데이트 파일(자기 자신 새 버전)을 다운로드하여 현재 실행 파일을 교체하는 작업을 진행하는 동안,
        별도의 업데이트 진행 UI를 띄워 진행률과 로그를 출력합니다.
        """
        try:
            # 업데이트 진행 다이얼로그 생성 및 표시
            progress_dialog = UpdateProgressDialog(self)
            progress_dialog.show()

            def update_progress(value):
                progress_dialog.set_progress(value)

            progress_dialog.append_log("업데이트 파일 다운로드 중...")
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()

            import sys
            if getattr(sys, 'frozen', False):
                current_exe = sys.executable
            else:
                current_exe = os.path.abspath(__file__)
            current_dir = os.path.dirname(current_exe)

            update_temp = os.path.join(current_dir, f"update_{latest_version}.exe")
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(update_temp, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percentage = int(downloaded * 100 / total_size)
                            update_progress(percentage)
            progress_dialog.append_log(f"업데이트 파일 다운로드 완료: {update_temp}")

            progress_dialog.append_log("업데이트를 실행합니다...")

            # 배치 파일 생성: 현재 실행 파일 교체 후 재시작
            bat_file = os.path.join(current_dir, "update.bat")
            bat_contents = f"""@echo off
    ping 127.0.0.1 -n 5 > nul
    move /y "{update_temp}" "{current_exe}"
    start "" "{current_exe}"
    del "%~f0"
    """
            with open(bat_file, "w", encoding="utf-8") as f:
                f.write(bat_contents)
            progress_dialog.append_log("업데이트 배치 파일 생성 완료.")

            import ctypes
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", bat_file, None, current_dir, 0
            )
            if ret <= 32:
                progress_dialog.append_log("업데이트 실행 실패. 관리자 권한이 필요합니다.")
            else:
                progress_dialog.append_log("업데이트 실행 성공. 프로그램이 종료됩니다.")
                # 잠시 대기 후 종료
                QtCore.QTimer.singleShot(3000, QtCore.QCoreApplication.quit)
        except Exception as e:
            progress_dialog.append_log(f"업데이트 수행 중 오류 발생: {e}")


class UpdateProgressDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("업데이트 진행 중")
        self.resize(400, 300)
        layout = QtWidgets.QVBoxLayout(self)

        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

    def append_log(self, message):
        self.log_text.append(message)
        # 스크린 갱신
        QtWidgets.QApplication.processEvents()

    def set_progress(self, value):
        self.progress_bar.setValue(value)
        QtWidgets.QApplication.processEvents()


class SchoolSelectionDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, current_school_name="", current_school_code="", current_school_domain=""):
        super().__init__(parent)
        self.setWindowTitle("지원 학교 선택")
        self.resize(400, 500)
        layout = QtWidgets.QVBoxLayout(self)

        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("학교 검색")
        layout.addWidget(self.search_edit)

        self.school_list = QtWidgets.QListWidget()
        layout.addWidget(self.school_list)

        self.count_label = QtWidgets.QLabel("총 지원 학교: 0개")
        layout.addWidget(self.count_label)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(button_box)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        self.schools = []
        self.load_schools()
        self.populate_list()
        self.search_edit.textChanged.connect(self.filter_list)

        # 만약 기존 선택값이 있으면 미리 선택
        if current_school_name:
            items = self.school_list.findItems(current_school_name, QtCore.Qt.MatchExactly)
            if items:
                self.school_list.setCurrentItem(items[0])

    def load_schools(self):
        try:
            response = requests.get(SCHOOLS_URL, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.schools = data.get("schools", [])
            else:
                self.schools = []
        except Exception as e:
            self.schools = []

    def populate_list(self):
        self.school_list.clear()
        for school in self.schools:
            item_text = f"{school.get('name', '')} ({school.get('code', '')})"
            self.school_list.addItem(item_text)
        self.count_label.setText(f"총 지원 학교: {len(self.schools)}개")

    def filter_list(self, text):
        self.school_list.clear()
        filtered = [s for s in self.schools if text.lower() in s.get('name', '').lower() or text.lower() in s.get('code', '').lower()]
        for school in filtered:
            item_text = f"{school.get('name', '')} ({school.get('code', '')})"
            self.school_list.addItem(item_text)
        self.count_label.setText(f"총 지원 학교: {len(filtered)}개")

    def get_values(self):
        current_item = self.school_list.currentItem()
        if current_item:
            selected_text = current_item.text()
            for school in self.schools:
                if school.get('name', '') in selected_text:
                    return school.get('name', ''), school.get('code', ''), school.get('domain', '')
        return "가톨릭대학교", "catholic", "e-cyber.catholic.ac.kr"


class WeatherEffectWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 마우스 이벤트 무시
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)

        # 약 30 FPS (30ms 간격)로 애니메이션 업데이트
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(30)

        self.particles = []
        self.weather_type = "none"  # 기본값: 효과 없음

        # 창이 열리면 즉시 날씨 정보를 가져옴
        QtCore.QTimer.singleShot(0, self.fetch_weather)

    def seasonal_effect(self, month):
        """
        현재 월(month)에 따라 계절별 기본 효과를 반환.
        봄: 벚꽃, 여름: 없음, 가을: 낙엽, 겨울: 눈은 날씨에 따라 처리.
        """
        if month in [3, 4, 5]:
            return "cherry"  # 봄 = 벚꽃
        elif month in [6, 7, 8]:
            return "none"    # 여름 = 없음
        elif month in [9, 10, 11]:
            return "leaves"  # 가을 = 낙엽
        elif month in [12, 1, 2]:
            return "none"    # 겨울, 눈은 날씨에 따라 처리

    def fetch_weather(self):
        """
        wttr.in API를 사용하여 경기도 성남시의 현재 날씨를 가져오고,
        계절과 날씨 조건에 따라 weather_type을 결정한다.
        """
        now = datetime.datetime.now()
        month = now.month
        try:
            url = "http://wttr.in/%EC%84%B1%EB%82%A8%EC%8B%9C?format=j1"
            response = requests.get(url, timeout=5)
            data = response.json()
            desc = data["current_condition"][0]["weatherDesc"][0]["value"]
            desc_lower = desc.lower()
            if "rain" in desc_lower:
                self.weather_type = "rain"
            elif "snow" in desc_lower:
                if month in [12, 1, 2]:
                    self.weather_type = "snow"
                else:
                    self.weather_type = self.seasonal_effect(month)
            else:
                self.weather_type = self.seasonal_effect(month)
        except Exception:
            self.weather_type = self.seasonal_effect(month)
        self.init_particles()

    def init_particles(self):
        """
        위젯의 크기와 weather_type에 따라 파티클을 초기화한다.
        weather_type이 "none"이면 파티클이 없도록 설정.
        """
        width = self.width() if self.width() > 0 else 500
        height = self.height() if self.height() > 0 else 600
        self.particles = []

        if self.weather_type == "cherry":
            count = 15
        elif self.weather_type == "snow":
            count = 25
        elif self.weather_type == "rain":
            count = 35
        elif self.weather_type == "leaves":
            count = 20
        elif self.weather_type == "none":
            count = 0
        else:
            count = 15

        for _ in range(count):
            x = random.uniform(0, width)
            y = random.uniform(0, height)
            if self.weather_type == "cherry":
                size = random.uniform(10, 20)
                vx = random.uniform(-1, 1)
                vy = random.uniform(1, 3)
                angle = random.uniform(0, 360)
                rotation_speed = random.uniform(-1, 1)
                particle = {
                    "x": x, "y": y, "size": size,
                    "vx": vx, "vy": vy,
                    "angle": angle, "rotation_speed": rotation_speed
                }
            elif self.weather_type == "snow":
                size = random.uniform(5, 10)
                vx = random.uniform(-0.5, 0.5)
                vy = random.uniform(0.5, 2)
                particle = {"x": x, "y": y, "size": size, "vx": vx, "vy": vy}
            elif self.weather_type == "rain":
                size = random.uniform(10, 15)
                vx = random.uniform(-0.2, 0.2)
                vy = random.uniform(4, 8)
                particle = {"x": x, "y": y, "size": size, "vx": vx, "vy": vy}
            elif self.weather_type == "leaves":
                size = random.uniform(8, 16)
                vx = random.uniform(-0.8, 0.8)
                vy = random.uniform(1, 4)
                # leaves에도 회전 효과 추가하면 자연스러울 수 있음
                angle = random.uniform(0, 360)
                rotation_speed = random.uniform(-0.5, 0.5)
                particle = {
                    "x": x, "y": y, "size": size,
                    "vx": vx, "vy": vy,
                    "angle": angle, "rotation_speed": rotation_speed
                }
            else:
                size = 10
                vx = 0
                vy = 1
                particle = {"x": x, "y": y, "size": size, "vx": vx, "vy": vy}
            self.particles.append(particle)

    def update_animation(self):
        """
        각 파티클의 위치와 회전(해당되는 경우)을 업데이트한 후 화면을 다시 그린다.
        """
        width = self.width()
        height = self.height()
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            if self.weather_type in ["cherry", "leaves"] and "angle" in p:
                p["angle"] += p["rotation_speed"]

            if p["y"] > height:
                p["y"] = -p["size"]
                p["x"] = random.uniform(0, width)
            if p["x"] < 0 or p["x"] > width:
                p["x"] = random.uniform(0, width)
        self.update()

    def paintEvent(self, event):
        """
        weather_type에 따라 파티클을 그린다.
        디자인 개선: 벚꽃과 낙엽 효과에 그라데이션 채우기와 드롭 섀도우 효과 적용.
        """
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        is_dark = False
        if self.parent() and hasattr(self.parent(), "dark_theme_action"):
            is_dark = self.parent().dark_theme_action.isChecked()

        for p in self.particles:
            x, y, size = p["x"], p["y"], p["size"]
            if self.weather_type == "cherry":
                # 벚꽃 효과: 드롭 섀도우 효과 추가
                center_x = x + size / 2
                center_y = y + (size * 0.6) / 2
                shadow_offset = 2
                painter.save()
                painter.translate(center_x + shadow_offset, center_y + shadow_offset)
                painter.rotate(p.get("angle", 0))
                painter.setBrush(QtGui.QColor(0, 0, 0, 50))  # 반투명 섀도우
                painter.setPen(QtCore.Qt.NoPen)
                painter.drawEllipse(QtCore.QRectF(-size/2, - (size*0.6)/2, size, size*0.6))
                painter.restore()

                # 벚꽃 효과: 그라데이션 채우기
                gradient = QtGui.QRadialGradient(center_x, center_y, size/2)
                if not is_dark:
                    gradient.setColorAt(0, QtGui.QColor(255, 218, 229))  # 연한 핑크
                    gradient.setColorAt(1, QtGui.QColor(255, 182, 193))  # 진한 핑크
                else:
                    gradient.setColorAt(0, QtGui.QColor(255, 182, 193))
                    gradient.setColorAt(1, QtGui.QColor(255, 105, 180))
                painter.save()
                painter.translate(center_x, center_y)
                painter.rotate(p.get("angle", 0))
                painter.setBrush(gradient)
                painter.setPen(QtCore.Qt.NoPen)
                painter.drawEllipse(QtCore.QRectF(-size/2, - (size*0.6)/2, size, size*0.6))
                painter.restore()

            elif self.weather_type == "snow":
                color = QtGui.QColor(255, 255, 255)
                painter.setBrush(color)
                painter.setPen(QtCore.Qt.NoPen)
                painter.drawEllipse(QtCore.QRectF(x, y, size, size))
            elif self.weather_type == "rain":
                color = QtGui.QColor(173, 216, 230) if not is_dark else QtGui.QColor(30, 144, 255)
                pen = QtGui.QPen(color, 2)
                painter.setPen(pen)
                painter.drawLine(QtCore.QPointF(x, y), QtCore.QPointF(x, y + size))
            elif self.weather_type == "leaves":
                # 낙엽 효과: 드롭 섀도우와 그라데이션 채우기
                center_x = x + size / 2
                center_y = y + (size * 0.8) / 2
                shadow_offset = 2
                painter.save()
                painter.translate(center_x + shadow_offset, center_y + shadow_offset)
                painter.rotate(p.get("angle", 0))
                painter.setBrush(QtGui.QColor(0, 0, 0, 50))
                painter.setPen(QtCore.Qt.NoPen)
                painter.drawEllipse(QtCore.QRectF(-size/2, - (size*0.8)/2, size, size*0.8))
                painter.restore()

                gradient = QtGui.QRadialGradient(center_x, center_y, size/2)
                if not is_dark:
                    gradient.setColorAt(0, QtGui.QColor(255, 228, 181))  # 연한 살구색
                    gradient.setColorAt(1, QtGui.QColor(205, 133, 63))   # 진한 갈색
                else:
                    gradient.setColorAt(0, QtGui.QColor(205, 133, 63))
                    gradient.setColorAt(1, QtGui.QColor(160, 82, 45))
                painter.save()
                painter.translate(center_x, center_y)
                painter.rotate(p.get("angle", 0))
                painter.setBrush(gradient)
                painter.setPen(QtCore.Qt.NoPen)
                painter.drawEllipse(QtCore.QRectF(-size/2, - (size*0.8)/2, size, size*0.8))
                painter.restore()
            # "none"은 그릴 파티클이 없음

    def resizeEvent(self, event):
        """
        위젯 크기 변경 시 파티클을 재초기화한다.
        """
        self.init_particles()
        super().resizeEvent(event)