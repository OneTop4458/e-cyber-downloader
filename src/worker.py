# --- 파일명: worker.py ---
import os
import json
import time
from PyQt5 import QtCore
from downloader import ECyberDownloader


class DownloaderWorker(QtCore.QObject):
    """
    QThread와 분리되어 동작할 실제 Worker.
    """
    # 로그 메시지를 메인 스레드로 전달하기 위한 시그널
    log_signal = QtCore.pyqtSignal(str)
    # 과목 정보 로드 완료 후 전달
    subjects_signal = QtCore.pyqtSignal(list)
    # 주차 정보 로드 완료 후 전달
    weeks_update_signal = QtCore.pyqtSignal(list)
    # 다운로드 완료 시그널
    finished_signal = QtCore.pyqtSignal()
    # 2차 본인인증이 필요할 때
    auth_confirmation_needed = QtCore.pyqtSignal()
    auth_confirmed_signal = QtCore.pyqtSignal()

    def wait_for_auth_confirmation(self):
        loop = QtCore.QEventLoop()
        self.auth_confirmed_signal.connect(loop.quit)
        loop.exec_()

    def __init__(self, username, password, download_dir, headless=False, parent=None):
        super().__init__(parent)
        self.username = username
        self.password = password
        self.download_dir = download_dir
        self.headless = headless

        self.downloader = None
        self.all_subjects = []
        self.weeks_cache = {}

    def auth_callback(self):
        self.auth_confirmation_needed.emit()
        self.wait_for_auth_confirmation()

    @QtCore.pyqtSlot()
    def setup(self):
        """
        쓰레드 시작 시 1회 호출됨
        """
        self.downloader = ECyberDownloader(
            log_callback=self.log_signal.emit,
            download_dir=self.download_dir,
            headless=self.headless
        )
        self.downloader.setup_driver()
        self.downloader.login(self.username, self.password)
        self.downloader.switch_to_regular_subjects_tab()
        self.downloader.auth_confirm_callback = self.auth_callback

    @QtCore.pyqtSlot()
    def load_subjects(self):
        """
        과목 정보 로드
        """
        try:
            subjects = self.downloader.get_subject_info_list()
            self.all_subjects = subjects

            # 오버레이 메시지 업데이트
            self.downloader.update_overlay_message("원하는 과목을 선택하세요")

            self.subjects_signal.emit(subjects)
        except Exception as e:
            self.log_signal.emit(f"[WARNING] 과목 정보 불러오기 오류: {str(e)}")

    @QtCore.pyqtSlot(dict)
    def load_weeks(self, subject_info):
        """
        주차 정보 로드 (캐싱)
        """
        key = subject_info.get("eclassRoom", "")
        if key in self.weeks_cache:
            self.log_signal.emit(f"(캐시) {subject_info['과목']}의 주차 정보: {self.weeks_cache[key]}")
            self.weeks_update_signal.emit(self.weeks_cache[key])
        else:
            try:
                weeks = self.downloader.get_available_weeks(subject_info)
                self.weeks_cache[key] = weeks
                self.log_signal.emit(f"{subject_info['과목']}의 주차 정보 불러옴: {weeks}")
                self.weeks_update_signal.emit(weeks)
            except Exception as e:
                self.log_signal.emit(f"[WARNING] 주차 정보 불러오기 오류 ({subject_info['과목']}): {str(e)}")
                self.weeks_update_signal.emit([])

    @QtCore.pyqtSlot(object, int)
    def perform_download(self, subject_info, start_week):
        """
        다운로드 진행
        """
        if subject_info.get("과목", "") == "전체":
            for subj in self.all_subjects:
                current_start = None if start_week == 0 else start_week
                self.log_signal.emit(
                    f"전체 과목 모드: '{subj['과목']}' 다운로드 시작 (start_week={current_start})"
                )
                self.downloader.perform_subject_actions(
                    subj, start_week=current_start
                )
            self.log_signal.emit("전체 과목 다운로드 완료.")
        else:
            self.downloader.perform_subject_actions(
                subject_info,
                start_week=None if start_week == 0 else start_week
            )
            self.log_signal.emit(f"'{subject_info['과목']}' 다운로드 완료.")

        self.finished_signal.emit()

    def quit(self):
        """
        Worker 종료
        """
        if self.downloader:
            self.downloader.quit()
