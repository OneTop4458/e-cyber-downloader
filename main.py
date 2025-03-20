import sys
import os
import re
import time
import json
import requests
import tqdm
from moviepy import VideoFileClip

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QMessageBox

# 암호화를 위한 cryptography 모듈 (pip install cryptography)
from cryptography.fernet import Fernet

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException, StaleElementReferenceException

CURRENT_VERSION = "0.1.0"  # 현재 애플리케이션 버전을 설정합니다.
VERSION_URL = "https://raw.githubusercontent.com/OneTop4458/e-cyber-downloader/refs/heads/main/version.json"


# --- 암호화 키 관련 함수 ---
def load_or_generate_key():
    key_file = "secret.key"
    if os.path.exists(key_file):
        with open(key_file, "rb") as f:
            key = f.read()
    else:
        key = Fernet.generate_key()
        with open(key_file, "wb") as f:
            f.write(key)
    return key

FERNET_KEY = load_or_generate_key()
fernet = Fernet(FERNET_KEY)


# --- Selenium 관련 클래스 (Persistent driver 사용) ---
class ECyberDownloader:
    def __init__(self, log_callback, download_dir, headless=False):
        """
        log_callback: 콜백 함수를 통해 UI로 로그 메시지를 전달 (예: log_signal.emit)
        download_dir: 다운로드 받을 폴더 경로
        headless: Chrome headless 모드 사용 여부 (True/False)
        """
        self.log_callback = log_callback
        self.download_dir = download_dir
        self.headless = headless
        self.driver = None
        # 본인인증 처리 콜백 (DownloaderWorker에서 등록)
        self.auth_confirm_callback = None

    def log(self, message: str):
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    def add_overlay(self):
        # MutationObserver를 이용하여 DOM 변화 시에도 오버레이가 항상 인젝션되도록 함.
        script = r"""
        (function(){
            function addOverlay(){
                if (!document.getElementById('automation-overlay')){
                    let overlay = document.createElement('div');
                    overlay.id = 'automation-overlay';
                    overlay.style.position = 'fixed';
                    overlay.style.top = '0';
                    overlay.style.left = '0';
                    overlay.style.width = '100%';
                    overlay.style.height = '100%';
                    overlay.style.backgroundColor = 'rgba(128, 128, 128, 0.5)';
                    overlay.style.color = 'white';
                    overlay.style.fontSize = '24px';
                    overlay.style.display = 'flex';
                    overlay.style.justifyContent = 'center';
                    overlay.style.alignItems = 'center';
                    overlay.style.zIndex = '9999';
                    overlay.style.pointerEvents = 'none';
                    overlay.innerText = '자동 제어 중 입니다 조작 금지...';
                    document.body.appendChild(overlay);
                }
            }
            addOverlay();
            const observer = new MutationObserver(function(mutations) {
                addOverlay();
            });
            observer.observe(document.body, {childList: true, subtree: true});
        })();
        """
        try:
            self.driver.execute_script(script)
        except Exception as e:
            self.log(f"오버레이 인젝션 오류: {str(e)}")

    def update_overlay_message(self, message: str):
        # 오버레이 메시지를 동적으로 변경하는 함수
        script = f"""
        (function(){{
            var overlay = document.getElementById('automation-overlay');
            if (overlay) {{
                overlay.innerText = "{message}";
            }}
        }})();
        """
        try:
            self.driver.execute_script(script)
        except Exception as e:
            self.log(f"오버레이 메시지 업데이트 오류: {str(e)}")

    def setup_driver(self):
        try:
            chrome_options = Options()
            chrome_options.add_argument("window-size=960,1080")
            chrome_options.add_argument("window-position=0,0")
            if self.headless:
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--disable-gpu")
            service = Service()
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.log("Chrome driver 초기화 성공.")
        except WebDriverException as e:
            self.log(f"Chrome driver 초기화 에러: {str(e)}")
            raise

    def navigate(self, url: str):
        self.driver.get(url)
        self.add_overlay()

    def login(self, username: str, password: str):
        try:
            self.navigate("https://e-cyber.catholic.ac.kr/ilos/main/member/login_form.acl")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "usr_id"))
            )
            self.driver.find_element(By.ID, "usr_id").send_keys(username)
            self.driver.find_element(By.ID, "usr_pwd").send_keys(password)
            self.driver.find_element(By.ID, "login_btn").click()
            self.log("로그인 시도 중...")
            time.sleep(0.5)
            self.navigate("https://e-cyber.catholic.ac.kr/ilos/mp/course_register_list_form.acl")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "list_tab1"))
            )
        except TimeoutException:
            self.log("로그인 실패: 로그인 정보가 올바른지 확인해 주세요.")
            raise
        except Exception as e:
            self.log(f"로그인 에러: {str(e)}")
            raise

    def switch_to_regular_subjects_tab(self):
        try:
            tab_element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "list_tab1"))
            )
            tab_element.click()
            self.log("정규 과목 탭으로 전환 완료.")
        except Exception as e:
            self.log(f"탭 전환 에러: {str(e)}")
            raise

    def get_subject_info_list(self):
        """과목 정보만 가져옴 (주차 정보 제외)"""
        subject_info_list = []
        try:
            subjects = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "content-container"))
            )
            for subject in subjects:
                try:
                    subject_title = subject.find_element(By.CLASS_NAME, "content-title").text
                    onclick_attr = subject.find_element(By.TAG_NAME, "a").get_attribute("onclick")
                    match = re.search(r"eclassRoom\('(.+?)'\)", onclick_attr)
                    if match:
                        eclass_room_value = match.group(1)
                        subject_info_list.append({"과목": subject_title, "eclassRoom": eclass_room_value})
                        self.log(f"과목: {subject_title}, eclassRoom: {eclass_room_value}")
                    else:
                        self.log(f"eclassRoom 값 추출 실패 - 과목: {subject_title}")
                except Exception:
                    pass
        except Exception as e:
            self.log(f"과목 정보를 가져오는데 실패: {str(e)}")
            raise
        return subject_info_list

    def get_available_weeks(self, subject_info: dict):
        """
        해당 과목 페이지로 이동하여 사용 가능한 주차(정수 리스트)를 반환합니다.
        각 주차 내 강의들 중, viewGo 함수 호출 시 마지막 인수가 비어있지 않은 강의가 한 개라도 있으면
        그 주차는 학습 가능한 것으로 간주합니다.
        """
        weeks = []
        try:
            self.log("주차 정보 로드를 시작합니다. 잠시 기다려주세요...")
            self.navigate("https://e-cyber.catholic.ac.kr/ilos/mp/course_register_list_form.acl")
            js_command = f"eclassRoom('{subject_info['eclassRoom']}');"
            self.driver.execute_script(js_command)
            self.log("주차 메뉴 버튼 클릭 중...")
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "menu_lecture_weeks"))
            ).click()
            time.sleep(2)
            self.add_overlay()
            self.log("주차 정보를 가져오는 중...")
            week_elements = WebDriverWait(self.driver, 20).until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, '//div[@id="chart"]//div[contains(@class, "wb-week")]')
                )
            )
            for week_element in week_elements:
                cls = week_element.get_attribute("class").lower()
                if "disabled" in cls or "unavail" in cls:
                    self.log(f"주차 '{week_element.text}'은(는) 사용 불가능합니다.")
                    continue
                try:
                    week_num = int(week_element.text.replace("주", ""))
                except Exception:
                    continue
                week_element.click()
                self.log(f"주차 {week_num} 강의 정보 확인 중...")
                time.sleep(1)
                lecture_buttons = self.driver.find_elements(By.XPATH, "//*[contains(@onclick, 'viewGo(')]")
                available = False
                for btn in lecture_buttons:
                    onclick_value = btn.get_attribute("onclick")
                    m = re.search(r"viewGo\([^,]+,[^,]+,[^,]+,[^,]+,'(.*?)'\)", onclick_value)
                    if m:
                        param = m.group(1).strip()
                        if param:
                            available = True
                            break
                if available:
                    self.log(f"주차 {week_num}는 학습 가능으로 판단됩니다.")
                    weeks.append(week_num)
                else:
                    self.log(f"주차 {week_num}는 학습 가능하지 않습니다 (학습하기 스크립트 없음).")
            weeks = sorted(set(weeks))
            self.log(f"최종 사용 가능한 주차 목록: {weeks}")
        except Exception as e:
            self.log(f"주차 정보 가져오기 실패: {str(e)}")
        return weeks

    def perform_subject_actions(self, subject_info: dict, start_week: int = None):
        """
        선택한 과목에 대해 지정한 주차부터 강의 다운로드를 진행합니다.
        만약 강의 클릭 후 2차 본인인증 창(예: id="dialog_secondary_auth")이 나타나면,
        사용자에게 수동 인증 후 Enter 키를 누르도록 안내합니다.
        """
        try:
            # 최초 상태에서 주차 목록(텍스트, 주차번호) 수집
            self.navigate("https://e-cyber.catholic.ac.kr/ilos/mp/course_register_list_form.acl")
            js_command = f"eclassRoom('{subject_info['eclassRoom']}');"
            self.driver.execute_script(js_command)
            self.log(f"작업 중 과목: {subject_info['과목']}")
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "menu_lecture_weeks"))
            ).click()
            time.sleep(2)

            week_elements = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, '//div[@id="chart"]//div[contains(@class, "wb-week")]')
                )
            )
            week_info_list = []
            for elem in week_elements:
                try:
                    week_text = elem.text.strip()  # 예: "3주"
                    week_num = int(week_text.replace("주", ""))
                    if start_week is not None and week_num < start_week:
                        continue
                    week_info_list.append((week_text, week_num))
                except Exception:
                    continue

            self.log(f"처리할 주차 목록: {week_info_list}")

            # 각 주차별로 개별 처리 (매 회 페이지를 새로 로드)
            for week_text, week_num in week_info_list:
                try:
                    # 매 주차 처리 전에 다시 초기 페이지로 네비게이트
                    self.navigate("https://e-cyber.catholic.ac.kr/ilos/mp/course_register_list_form.acl")
                    js_command = f"eclassRoom('{subject_info['eclassRoom']}');"
                    self.driver.execute_script(js_command)
                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "menu_lecture_weeks"))
                    ).click()
                    time.sleep(2)

                    # 주차 요소를 XPath로 다시 조회 (normalize-space로 공백 제거)
                    week_xpath = f'//div[@id="chart"]//div[contains(@class, "wb-week") and normalize-space(text())="{week_text}"]'
                    week_element = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, week_xpath))
                    )
                    # 주차의 부모에서 강의 총 개수를 확인
                    week_parent = week_element.find_element(By.XPATH, "..")
                    lesson_info = week_parent.find_element(By.XPATH, "./div[@class='wb-status']").text
                    lesson_total = int(lesson_info.split("/")[1])
                    self.log(f"[주차 {week_num}] 총 강의 수: {lesson_total}")

                    # 주차 클릭
                    week_element.click()
                    time.sleep(2)

                    # 해당 주차의 강의 요소들을 조회하여 처리
                    lecture_elements = self.driver.find_elements(By.XPATH, '//*[starts-with(@id, "lecture-")]')
                    for lecture_element in lecture_elements:
                        lesson_elements = lecture_element.find_elements(
                            By.XPATH, "./div/ul/li[1]/ol/li[5]/div/div/div[1]/div/span"
                        )
                        for lesson_element in lesson_elements:
                            lesson_title = lesson_element.text
                            js_script = lesson_element.get_attribute("onclick")
                            # 정규표현식으로 '학습하기' 스크립트의 파라미터 확인
                            m = re.search(r"viewGo\([^,]+,[^,]+,[^,]+,[^,]+,'(.*?)'\)", js_script)
                            if not m or not m.group(1).strip():
                                self.log(f"주차 {week_num}, 강의 '{lesson_title}'에 학습하기 스크립트가 없습니다. 스킵합니다.")
                                continue
                            self.log(f"주차 {week_num}, 강의: {lesson_title}")
                            try:
                                self.driver.execute_script(js_script)
                            except Exception as e:
                                self.log(f"JS 실행 오류: {str(e)}")
                                continue

                            # 출석인정기간 관련 alert 처리
                            try:
                                WebDriverWait(self.driver, 3).until(EC.alert_is_present())
                                alert = self.driver.switch_to.alert
                                alert_text = alert.text
                                if "출석인정기간이 지나" in alert_text:
                                    self.log("출석인정기간 경고 alert 발견: 자동 '확인' 처리합니다.")
                                    alert.accept()
                                    time.sleep(2)
                            except TimeoutException:
                                pass

                            # 2차 본인인증 처리
                            time.sleep(0.5)
                            try:
                                auth_dialog = WebDriverWait(self.driver, 3).until(
                                    EC.presence_of_element_located((By.ID, "dialog_secondary_auth"))
                                )
                                if auth_dialog.is_displayed():
                                    self.log("본인인증 창이 표시되었습니다. 사용자 확인 대기...")
                                    if hasattr(self, "auth_confirm_callback") and self.auth_confirm_callback:
                                        self.auth_confirm_callback()
                                        self.log("사용자가 본인인증 확인을 완료하였습니다.")
                                        self.log("잠시 후 동영상을 자동 다운로드 합니다.")
                            except TimeoutException:
                                pass

                            # 동영상 다운로드 처리
                            try:
                                WebDriverWait(self.driver, 10).until(EC.alert_is_present())
                                alert = self.driver.switch_to.alert
                                alert.accept()
                                time.sleep(5)
                                WebDriverWait(self.driver, 10).until(
                                    EC.url_to_be("https://e-cyber.catholic.ac.kr/ilos/st/course/online_view_form.acl")
                                )
                                viewer = self.driver.find_element(By.ID, "contentViewer")
                                actions = ActionChains(self.driver)
                                actions.move_to_element(viewer).click().send_keys(Keys.SPACE).perform()
                                time.sleep(5)
                                actions.move_to_element(viewer).click()
                                iframe = self.driver.find_element(By.TAG_NAME, "iframe")
                                self.driver.switch_to.frame(iframe)
                                try:
                                    video_element = self.driver.find_element(
                                        By.XPATH, "//*[@id='syncvideo-play']/div/div[1]/div[1]/video"
                                    )
                                except NoSuchElementException:
                                    video_element = None
                                if not video_element or not video_element.get_attribute("src"):
                                    try:
                                        video_element = self.driver.find_element(
                                            By.XPATH, "//*[@id='video-play-video1']/div[1]/video"
                                        )
                                    except NoSuchElementException:
                                        self.log("영상 엘리먼트를 찾지 못했습니다. 다음 강의로 넘어갑니다.")
                                        self.driver.back()
                                        time.sleep(2)
                                        continue
                                total_video_time = self.driver.find_element(
                                    By.XPATH, "/html/head/meta[13]"
                                ).get_attribute("content")
                                self.log(f"영상 총 길이: {total_video_time}")

                                previous_url = None
                                downloaded_duration = 0
                                video_count = 1
                                continuous_fail_count = 0

                                while True:
                                    video_url = video_element.get_attribute("src")
                                    time.sleep(1)
                                    if video_url and video_url != previous_url:
                                        filename = f"{subject_info['과목']}_{week_num}_{lesson_title}_{video_count}.mp4"
                                        file_path = os.path.join(self.download_dir, filename)
                                        self.log(f"다운로드 링크: {video_url}")
                                        self.log(f"저장 파일: {file_path}")
                                        self.driver.switch_to.default_content()
                                        time.sleep(2)
                                        viewer = self.driver.find_element(By.ID, "contentViewer")
                                        actions = ActionChains(self.driver)
                                        actions.move_to_element(viewer).click().send_keys(Keys.SPACE).perform()
                                        self.download_mp4(video_url, file_path)
                                        iframe = self.driver.find_element(By.TAG_NAME, "iframe")
                                        self.driver.switch_to.frame(iframe)
                                        previous_url = video_url
                                        video_count += 1
                                        continuous_fail_count = 0
                                        downloaded_video_duration = self.get_video_duration(file_path)
                                        downloaded_duration += int(downloaded_video_duration)
                                        self.log(f"현재까지 다운로드된 시간: {downloaded_duration}")
                                        if int(downloaded_duration) >= int(total_video_time) - 1:
                                            self.log("해당 강의 다운로드 완료.")
                                            break
                                    else:
                                        continuous_fail_count += 1
                                        if continuous_fail_count >= 999:
                                            self.log("연속 URL 실패로 인한 강의 중단.")
                                            break
                                        self.driver.switch_to.default_content()
                                        time.sleep(2)
                                        viewer = self.driver.find_element(By.ID, "contentViewer")
                                        actions = ActionChains(self.driver)
                                        time.sleep(2)
                                        for _ in range(6):
                                            actions.move_to_element(viewer).click().send_keys(Keys.ARROW_RIGHT).perform()
                                        iframe = self.driver.find_element(By.TAG_NAME, "iframe")
                                        self.driver.switch_to.frame(iframe)
                                        time.sleep(2)
                            except Exception as e:
                                self.log(f"강의 처리 중 오류: {str(e)}")
                                continue
                except Exception as e:
                    self.log(f"주차 {week_num} 처리 중 오류: {str(e)}")
                    continue
        except Exception as e:
            self.log(f"과목 작업 수행 중 오류: {str(e)}")

    def download_mp4(self, url: str, file_name: str):
        try:
            response = requests.get(url, stream=True)
            total_size = int(response.headers.get("content-length", 0))
            block_size = 1024
            with open(file_name, "wb") as mp4_file:
                with tqdm.tqdm(total=total_size, unit="B", unit_scale=True, desc=file_name, ascii=True) as progress_bar:
                    for data in response.iter_content(block_size):
                        mp4_file.write(data)
                        progress_bar.update(len(data))
            self.log("다운로드 완료.")
            # MP4 파일 다운로드 후 MP3로 변환
            self.convert_to_mp3(file_name)
        except Exception as e:
            self.log(f"다운로드 실패: {str(e)}")

    def convert_to_mp3(self, mp4_file: str):
        try:
            clip = VideoFileClip(mp4_file)
            mp3_file = os.path.splitext(mp4_file)[0] + ".mp3"
            clip.audio.write_audiofile(mp3_file)
            self.log(f"MP3 파일로 변환 완료: {mp3_file}")
        except Exception as e:
            self.log(f"MP3 변환 오류: {str(e)}")

    def get_video_duration(self, file_path: str):
        try:
            clip = VideoFileClip(file_path)
            return clip.duration
        except Exception as e:
            self.log(f"동영상 길이 확인 오류: {str(e)}")
            return 0

    def quit(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                self.log(f"Chrome driver 종료 중 오류: {str(e)}")
            self.log("Chrome driver 종료.")


# --- DownloaderWorker: persistent Selenium 드라이버를 QThread에서 운영 ---
class DownloaderWorker(QtCore.QObject):
    log_signal = QtCore.pyqtSignal(str)
    subjects_signal = QtCore.pyqtSignal(list)
    weeks_update_signal = QtCore.pyqtSignal(list)
    finished_signal = QtCore.pyqtSignal()
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
        self.downloader = ECyberDownloader(self.log_signal.emit, self.download_dir, headless=self.headless)
        self.downloader.setup_driver()
        self.downloader.login(self.username, self.password)
        self.downloader.switch_to_regular_subjects_tab()
        # 본인인증 콜백 등록
        self.downloader.auth_confirm_callback = self.auth_callback

    @QtCore.pyqtSlot()
    def load_subjects(self):
        try:
            subjects = self.downloader.get_subject_info_list()
            self.all_subjects = subjects
            # 과목 정보를 불러온 후 오버레이 메시지 업데이트
            self.downloader.update_overlay_message("원하는 과목을 선택하세요")
            self.subjects_signal.emit(subjects)
        except Exception as e:
            self.log_signal.emit(f"[WARNING] 과목 정보 불러오기 오류: {str(e)}")

    @QtCore.pyqtSlot(dict)
    def load_weeks(self, subject_info):
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
        if subject_info.get("과목", "") == "전체":
            for subj in self.all_subjects:
                current_start = None if start_week == 0 else start_week
                self.log_signal.emit(f"전체 과목 모드: '{subj['과목']}' 다운로드 시작 (start_week={current_start})")
                self.downloader.perform_subject_actions(subj, start_week=current_start)
            self.log_signal.emit("전체 과목 다운로드 완료.")
        else:
            self.downloader.perform_subject_actions(subject_info, start_week=start_week)
            self.log_signal.emit(f"'{subject_info['과목']}' 다운로드 완료.")
        self.finished_signal.emit()

    def quit(self):
        if self.downloader:
            self.downloader.quit()


# --- MainWindow ---
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ECyber Downloader")
        self.resize(900, 700)
        self.download_dir = os.getcwd()
        self.downloader_worker = None
        self.worker_thread = None
        self.subjects = []
        self.log_level = "DEBUG"
        self.headless = False  # Headless 옵션을 저장할 변수
        self.setup_ui()
        self.load_config()
        if os.path.exists("credentials.json"):
            self.save_credentials_checkbox.setChecked(True)
            self.load_credentials()

    def setup_ui(self):
        # --- 스타일시트 (Modern WinUI3 느낌을 모방) ---
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
            /* 버튼이 비활성화 되었을 때 */
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
            /* 버튼이 비활성화 되었을 때 */
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
        
        # --- 메뉴바 및 옵션 메뉴 ---
        menubar = self.menuBar()
        
        # View 메뉴: 다크테마 토글
        view_menu = menubar.addMenu("View")
        self.dark_theme_action = QtWidgets.QAction("다크테마", self)
        self.dark_theme_action.setCheckable(True)
        self.dark_theme_action.triggered.connect(self.toggle_dark_theme)
        view_menu.addAction(self.dark_theme_action)
        
        # Options 메뉴: chrome 강제 종료, headless mode, 로그 레벨 선택
        options_menu = menubar.addMenu("Options")
        
        chrome_terminate_action = QtWidgets.QAction("Chrome 강제 종료", self)
        chrome_terminate_action.triggered.connect(self.force_stop_chrome)
        options_menu.addAction(chrome_terminate_action)
        
        self.headless_action = QtWidgets.QAction("Headless Mode", self)
        self.headless_action.setCheckable(True)
        self.headless_action.setChecked(self.headless)
        self.headless_action.triggered.connect(self.toggle_headless)
        options_menu.addAction(self.headless_action)
        
        # 로그 레벨 서브메뉴 (액션 그룹으로 구성)
        log_level_menu = options_menu.addMenu("Log Level")
        log_level_group = QtWidgets.QActionGroup(self)
        log_level_debug = QtWidgets.QAction("DEBUG", self, checkable=True)
        log_level_info = QtWidgets.QAction("INFO", self, checkable=True)
        log_level_warning = QtWidgets.QAction("WARNING", self, checkable=True)
        log_level_group.addAction(log_level_debug)
        log_level_group.addAction(log_level_info)
        log_level_group.addAction(log_level_warning)
        # 현재 로그 레벨에 따라 선택 상태 지정
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
        help_action = QtWidgets.QAction("사용법", self)
        help_action.triggered.connect(self.show_usage)
        help_menu.addAction(help_action)
        
        # 상태바
        self.statusBar().showMessage("준비됨")
        
        # --- 중앙 위젯 및 레이아웃 ---
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 로그인 및 옵션 그룹
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
        # 옵션: 과목 선택 및 주차 선택
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
        
        # 다운로드 폴더 선택
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

    def set_log_level(self, level):
        self.log_level = level
        self.append_log(f"[INFO] 로그 레벨이 {level}(으)로 설정되었습니다.")

    def toggle_headless(self, checked):
        self.headless = checked
        self.append_log(f"[INFO] Headless Mode {'사용' if checked else '해제'}됨.")

    def append_log(self, message):
        level_order = {"DEBUG": 0, "INFO": 1, "WARNING": 2}
        msg_level = "INFO"
        if message.startswith("[DEBUG]"):
            msg_level = "DEBUG"
        elif message.startswith("[WARNING]"):
            msg_level = "WARNING"
        if level_order[msg_level] >= level_order[self.log_level]:
            self.log_text.append(message)
        self.statusBar().showMessage(message, 3000)

    def on_save_credentials_changed(self, state):
        if state == QtCore.Qt.Unchecked:
            if os.path.exists("credentials.json"):
                os.remove("credentials.json")
                self.append_log("[INFO] 저장된 로그인 정보 삭제됨.")

    def show_usage(self):
        instructions = (
            "사용법 안내:\n\n"
            "1. 사용자 이름과 비밀번호를 입력하고 '로그인 정보 저장'을 선택하면 암호화되어 저장됩니다.\n"
            "   - 체크 해제 시 즉시 저장된 정보가 삭제됩니다.\n"
            "2. '과목 정보 불러오기' 버튼을 누르면 워커가 persistent Chrome 창에서 로그인 후 전체 과목 목록(주차 정보 제외)을 불러옵니다.\n"
            "3. 특정 과목 선택 시, 워커가 비동기로 사용 가능한 주차(학습 가능한 주차)를 가져와 UI를 업데이트합니다.\n"
            "4. 다운로드 폴더를 지정한 후 '다운로드 시작' 버튼을 누르면 선택한 과목(및 주차부터)로 강의 다운로드가 진행됩니다.\n"
            "5. 진행 상황은 로그 창 및 상태바에서 실시간으로 확인할 수 있습니다.\n"
            "6. Options 메뉴에서 Chrome 강제 종료, Headless Mode, 로그 레벨을 설정할 수 있습니다.\n"
            "7. 2차 본인인증 창이 나타나면, 사용자에게 본인인증 창 확인 후 '확인' 버튼을 누르라는 메시지가 표시됩니다."
        )
        QMessageBox.information(self, "사용법", instructions)

    def load_config(self):
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
                # 테마 정보 로드
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
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "다운로드 폴더 선택", self.download_dir)
        if directory:
            self.download_dir = directory
            self.dir_label.setText(f"다운로드 폴더: {directory}")
            self.save_config()

    def load_subjects(self):
        self.save_credentials()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        if self.downloader_worker is None:
            self.worker_thread = QtCore.QThread()
            self.downloader_worker = DownloaderWorker(username, password, self.download_dir, headless=self.headless)
            self.downloader_worker.moveToThread(self.worker_thread)
            self.downloader_worker.log_signal.connect(self.append_log)
            self.downloader_worker.subjects_signal.connect(self.update_subjects)
            self.downloader_worker.weeks_update_signal.connect(self.update_weeks)
            self.downloader_worker.auth_confirmation_needed.connect(self.show_auth_confirmation_dialog)
            self.worker_thread.started.connect(self.downloader_worker.setup)
            self.worker_thread.start()
            QtCore.QTimer.singleShot(1000, self.downloader_worker.load_subjects)
        else:
            QtCore.QMetaObject.invokeMethod(self.downloader_worker, "load_subjects", QtCore.Qt.QueuedConnection)

    def update_subjects(self, subjects):
        self.subjects = subjects
        self.subject_combo.blockSignals(True)
        self.subject_combo.clear()
        self.subject_combo.addItem("전체 과목")
        for subj in subjects:
            self.subject_combo.addItem(subj.get("과목", ""))
        self.subject_combo.blockSignals(False)
        if subjects:
            self.append_log("[INFO] 과목 정보를 성공적으로 불러왔습니다.")
            # 전체 과목 선택은 주차 정보 없이 바로 다운로드 가능
            self.start_download_button.setEnabled(True)
        else:
            self.append_log("[WARNING] 과목 정보를 불러오지 못했습니다.")
            self.start_download_button.setEnabled(False)
        self.week_combo.clear()
        self.week_combo.setEnabled(False)

    def subject_changed(self, index):
        self.week_combo.clear()
        self.week_combo.setEnabled(False)
        if index == 0:
            self.append_log("전체 과목이 선택되었습니다. (주차 정보는 '전체 주차'로 처리됩니다.)")
            self.start_download_button.setEnabled(True)
        else:
            subject_info = self.subjects[index - 1]
            self.append_log(f"과목 '{subject_info['과목']}'이(가) 선택되었습니다. 주차 정보를 불러옵니다...")
            self.start_download_button.setEnabled(False)
            QtCore.QMetaObject.invokeMethod(self.downloader_worker, "load_weeks",
                                              QtCore.Qt.QueuedConnection,
                                              QtCore.Q_ARG(dict, subject_info))

    def update_weeks(self, weeks):
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
        if not self.download_dir or not os.path.isdir(self.download_dir):
            QMessageBox.warning(self, "다운로드 폴더", "먼저 다운로드 폴더를 지정해 주세요.")
            return
        if self.subject_combo.currentIndex() == 0:
            subject_info = {"과목": "전체", "eclassRoom": ""}
        else:
            subject_info = self.subjects[self.subject_combo.currentIndex() - 1]
        start_week = None
        if self.week_combo.isEnabled() and self.week_combo.currentData() is not None:
            start_week = self.week_combo.currentData()
        else:
            start_week = 0
        self.append_log("다운로드 시작...")
        QtCore.QMetaObject.invokeMethod(self.downloader_worker, "perform_download",
                                        QtCore.Qt.QueuedConnection,
                                        QtCore.Q_ARG(dict, subject_info),
                                        QtCore.Q_ARG(int, start_week))

    def show_auth_confirmation_dialog(self):
        QMessageBox.information(self, "본인인증", "본인인증 창이 표시되었습니다.\n수동 인증 후 '확인' 버튼을 누르세요.")
        self.downloader_worker.auth_confirmed_signal.emit()

    def force_stop_chrome(self):
        if self.downloader_worker:
            self.downloader_worker.quit()
            self.append_log("Chrome driver 강제 종료됨.")
        else:
            self.append_log("실행 중인 Chrome driver가 없습니다.")

    def toggle_dark_theme(self, checked):
        if checked:
            self.setStyleSheet(self.dark_style)
            self.append_log("[INFO] 다크테마 적용됨.")
        else:
            self.setStyleSheet(self.light_style)
            self.append_log("[INFO] 라이트 테마 적용됨.")
        # 테마 변경 후 즉시 저장
        self.save_config()

    def closeEvent(self, event):
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
        GitHub에 호스팅된 version.json 파일을 다운로드하여 현재 버전과 비교합니다.
        업데이트가 필요한 경우, 업데이트 정보를 UI(메시지 박스)로 안내합니다.
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
                    ret = QMessageBox.question(self, "업데이트 안내", msg,
                                               QMessageBox.Yes | QMessageBox.No)
                    if ret == QMessageBox.Yes:
                        # 업데이트 로직 (예: 웹 브라우저에서 다운로드 URL 열기)
                        QtGui.QDesktopServices.openUrl(QtCore.QUrl(download_url))
                    else:
                        self.append_log("업데이트가 취소되었습니다.")
                    return version_info
                else:
                    self.append_log("현재 최신 버전입니다.")
                    return None
            else:
                self.append_log("버전 정보를 불러올 수 없습니다.")
                return None
        except Exception as e:
            self.append_log(f"버전 체크 중 오류 발생: {e}")
            return None

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    # 프로그램 시작 시 버전 체크
    window.check_for_update()
    sys.exit(app.exec())

