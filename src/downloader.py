# --- 파일명: downloader.py ---
import os
import re
import time
import requests
import tqdm
from moviepy import VideoFileClip

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException, WebDriverException,
    StaleElementReferenceException
)

# 버전 체크용 상수
CURRENT_VERSION = "0.1.0"
VERSION_URL = "https://raw.githubusercontent.com/OneTop4458/e-cyber-downloader/refs/heads/main/version.json"


class ECyberDownloader:
    def __init__(self, log_callback, download_dir, headless=False):
        """
        log_callback: 로그 출력용 함수
        download_dir: 다운로드 받을 폴더 경로
        headless: Chrome headless 모드 사용 여부
        """
        self.log_callback = log_callback
        self.download_dir = download_dir
        self.headless = headless
        self.driver = None
        self.auth_confirm_callback = None  # 2차 인증 콜백

    def log(self, message: str):
        """
        로그 호출
        """
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    def add_overlay(self):
        """
        DOM 위에 오버레이 삽입
        """
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
        """
        오버레이 메시지 업데이트
        """
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
        """
        Selenium Chrome driver 초기화
        """
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
        try:
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

            for week_text, week_num in week_info_list:
                try:
                    self.navigate("https://e-cyber.catholic.ac.kr/ilos/mp/course_register_list_form.acl")
                    js_command = f"eclassRoom('{subject_info['eclassRoom']}');"
                    self.driver.execute_script(js_command)
                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "menu_lecture_weeks"))
                    ).click()
                    time.sleep(2)

                    week_xpath = f'//div[@id="chart"]//div[contains(@class, "wb-week") and normalize-space(text())="{week_text}"]'
                    week_element = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, week_xpath))
                    )

                    week_parent = week_element.find_element(By.XPATH, "..")
                    lesson_info = week_parent.find_element(By.XPATH, "./div[@class='wb-status']").text
                    lesson_total = int(lesson_info.split("/")[1])
                    self.log(f"[주차 {week_num}] 총 강의 수: {lesson_total}")

                    week_element.click()
                    time.sleep(2)

                    lecture_elements = self.driver.find_elements(By.XPATH, '//*[starts-with(@id, "lecture-")]')
                    for lecture_element in lecture_elements:
                        lesson_elements = lecture_element.find_elements(
                            By.XPATH, "./div/ul/li[1]/ol/li[5]/div/div/div[1]/div/span"
                        )
                        for lesson_element in lesson_elements:
                            lesson_title = lesson_element.text
                            js_script = lesson_element.get_attribute("onclick")

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

                            # 출석인정기간 관련 alert
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

                            # 2차 본인인증
                            time.sleep(0.5)
                            try:
                                auth_dialog = WebDriverWait(self.driver, 3).until(
                                    EC.presence_of_element_located((By.ID, "dialog_secondary_auth"))
                                )
                                if auth_dialog.is_displayed():
                                    self.log("본인인증 창이 표시되었습니다. 사용자 확인 대기...")
                                    if callable(self.auth_confirm_callback):
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
        """
        드라이버 종료
        """
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                self.log(f"Chrome driver 종료 중 오류: {str(e)}")
            self.log("Chrome driver 종료.")
