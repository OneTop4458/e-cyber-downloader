# -*- coding: utf-8 -*-
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
    progress_update_signal = QtCore.pyqtSignal(int)

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
        # lectures_cache[eclassRoom] = { week_num: [ {title, script}, ... ], ... }
        self.lectures_cache = {}

    def auth_callback(self):
        self.auth_confirmation_needed.emit()
        self.wait_for_auth_confirmation()

    @QtCore.pyqtSlot()
    def setup(self):
        """
        쓰레드 시작 시 1회 호출
        """
        self.downloader = ECyberDownloader(
            log_callback=self.log_signal.emit,
            download_dir=self.download_dir,
            headless=self.headless,
            progress_callback=self.progress_update_signal.emit
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
            self.downloader.update_overlay_message("프로그램에서 원하는 과목을 선택하세요 페이지 임의 조작 금지..")
            self.subjects_signal.emit(subjects)
        except Exception as e:
            self.log_signal.emit(f"[WARNING] 과목 정보 불러오기 오류: {str(e)}")

    @QtCore.pyqtSlot(dict)
    def load_weeks(self, subject_info):
        """
        주차 + 강의(스크립트) 전부 미리 로드하고, UI에는 '사용 가능한 주차'만 보내줌
        """
        eclass_key = subject_info.get("eclassRoom", "")
        if eclass_key in self.lectures_cache:
            # 이미 파싱해놨음
            lectures_map = self.lectures_cache[eclass_key]
            weeks = sorted(lectures_map.keys())
            self.log_signal.emit(f"(캐시) {subject_info['과목']} 주차 정보: {weeks}")
            self.weeks_update_signal.emit(weeks)
            return

        try:
            # 새로 파싱
            lectures_map = self.downloader.get_lectures_by_week(subject_info)
            self.lectures_cache[eclass_key] = lectures_map

            # UI에 표시할 주차 목록
            weeks = sorted(lectures_map.keys())
            self.log_signal.emit(f"{subject_info['과목']} 주차/강의 불러옴 => 주차 {weeks}")
            self.weeks_update_signal.emit(weeks)
        except Exception as e:
            self.log_signal.emit(f"[WARNING] 주차/강의 정보 불러오기 오류 ({subject_info['과목']}): {str(e)}")
            self.weeks_update_signal.emit([])

    @QtCore.pyqtSlot(object, int)
    def perform_download(self, subject_info, start_week):
        """
        start_week:
          0 => 모든 주차
          n => 딱 n 주차만
        """
        eclass_key = subject_info.get("eclassRoom", "")
        lectures_map = self.lectures_cache.get(eclass_key, {})

        if subject_info.get("과목") == "전체":
            for subj in self.all_subjects:
                eclass_key2 = subj["eclassRoom"]
                # 주차 정보가 캐시에 없으면 즉시 수집
                if eclass_key2 not in self.lectures_cache:
                    new_map = self.downloader.get_lectures_by_week(subj)
                    self.lectures_cache[eclass_key2] = new_map

                # 가져온 강의 맵
                map2 = self.lectures_cache.get(eclass_key2, {})
                # 전체 주차 or 특정 주차 필터링
                if start_week == 0:
                    filtered = map2
                else:
                    filtered = {}
                    if start_week in map2:
                        filtered = {start_week: map2[start_week]}

                self.log_signal.emit(
                    f"[전체 과목] {subj['과목']} => 다운로드 주차 {list(filtered.keys())}"
                )
                self.downloader.perform_lectures_actions(subj, filtered)
        else:
            # 단일 과목 다운로드
            # 필요하면 여기서도 캐시를 갱신(사용자가 UI에서 주차 정보를 안 불러왔을 수도 있으므로)
            if not lectures_map:
                new_map = self.downloader.get_lectures_by_week(subject_info)
                self.lectures_cache[eclass_key] = new_map
                lectures_map = new_map

            if start_week == 0:
                filtered_map = lectures_map
            else:
                filtered_map = {}
                if start_week in lectures_map:
                    filtered_map = {start_week: lectures_map[start_week]}

            self.log_signal.emit(
                f"[단일 과목] {subject_info['과목']} => 다운로드 주차 {list(filtered_map.keys())}"
            )
            self.downloader.perform_lectures_actions(subject_info, filtered_map)

        self.finished_signal.emit()

    def quit(self):
        """
        Worker 종료
        """
        if self.downloader:
            self.downloader.quit()
