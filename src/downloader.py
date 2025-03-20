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
    NoSuchElementException, TimeoutException, WebDriverException
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

    def get_lectures_by_week(self, subject_info: dict):
        """
        해당 과목의 “학습 가능한” 주차와 강의(onclick 스크립트, 제목 등)를 모두 수집
        결과:
        {
          3: [ {"title": "...", "script": "viewGo(...)"}, ...],
          4: [ ... ],
          ...
        }
        """
        # 과목 페이지 진입
        lectures_map = {}
        try:
            self.log(f"{subject_info['과목']} 강의 목록 로드를 시작합니다.")
            self.navigate("https://e-cyber.catholic.ac.kr/ilos/mp/course_register_list_form.acl")
            time.sleep(0.5)
            js_command = f"eclassRoom('{subject_info['eclassRoom']}');"
            self.driver.execute_script(js_command)
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "menu_lecture_weeks"))
            ).click()
            time.sleep(2)
            self.add_overlay()

            # 모든 주차 DOM
            week_elements = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, '//div[@id="chart"]//div[contains(@class, "wb-week")]')
                )
            )

            for week_element in week_elements:
                cls = week_element.get_attribute("class").lower()
                if "disabled" in cls or "unavail" in cls:
                    # 사용 불가능한 주차
                    self.log(f"주차 '{week_element.text}'은(는) 사용 불가. 스킵.")
                    continue

                try:
                    week_num = int(week_element.text.replace("주", ""))
                except ValueError:
                    continue

                # 주차 클릭
                week_element.click()
                time.sleep(1)

                # 학습하기 스크립트 가져오기
                lecture_buttons = self.driver.find_elements(By.XPATH, "//*[contains(@onclick, 'viewGo(')]")
                collected = []
                for btn in lecture_buttons:
                    onclick_value = btn.get_attribute("onclick")
                    # 예: viewGo(…,'abc123')
                    m = re.search(r"viewGo\([^,]+,[^,]+,[^,]+,[^,]+,'(.*?)'\)", onclick_value)
                    if m:
                        param = m.group(1).strip()
                        if param:  # 빈 문자열 아니면 학습 가능
                            # 강의 제목 추출
                            # (이 버튼 바로 상위/옆의 DOM 등을 뒤져볼 수 있으나, 일단 간단히 .text)
                            title = btn.text.strip()
                            if not title:
                                # 만약 버튼 text가 없다면, 상위 엘리먼트에서 찾는 로직 등 추가 가능
                                title = "강의(제목미상)"
                            collected.append({
                                "title": title,
                                "script": onclick_value
                            })

                if collected:
                    lectures_map[week_num] = collected
                    self.log(f"{week_num}주 => 학습 가능 강의 {len(collected)}개 수집.")
                else:
                    self.log(f"{week_num}주 => 학습 가능 강의 없음.")

            self.log(f"최종 수집 결과: {lectures_map}")
        except Exception as e:
            self.log(f"강의 목록 로드 중 오류: {str(e)}")

        return lectures_map

    def perform_lectures_actions(self, subject_info: dict, lectures_map: dict):
        """
        ‘lectures_map[week] = [ {title, script} ...]’ 형태로 전달받아,
        주차별로 반복하며, 각 강의를 다운로드
        DOM을 다시 파싱하지 않고, script를 그대로 execute_script()로 실행
        """
        self.log(f"{subject_info['과목']} 다운로드 시작 - 주차 목록: {list(lectures_map.keys())}")

        for week_num in sorted(lectures_map.keys()):
            # 주차 이동
            try:
                self.navigate("https://e-cyber.catholic.ac.kr/ilos/mp/course_register_list_form.acl")
                time.sleep(0.5)
                js_command = f"eclassRoom('{subject_info['eclassRoom']}');"
                self.driver.execute_script(js_command)
                WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "menu_lecture_weeks"))
                ).click()
                time.sleep(2)

                # 주차 DOM 찾아 클릭
                week_xpath = f'//div[@id="chart"]//div[contains(@class, "wb-week") and normalize-space(text())="{week_num}주"]'
                week_element = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, week_xpath))
                )
                week_element.click()
                time.sleep(1)
            except Exception as e:
                self.log(f"[주차 {week_num}] 페이지 이동 중 오류: {str(e)}")
                continue

            lectures = lectures_map[week_num]
            self.log(f"[주차 {week_num}] 강의 {len(lectures)}개 다운로드 진행...")

            for lecture_info in lectures:
                title = lecture_info["title"]
                script = lecture_info["script"]
                self.log(f"[주차 {week_num}] 강의: {title}")

                # 실제로 viewGo() 스크립트 실행
                try:
                    self.driver.execute_script(script)
                except Exception as e:
                    self.log(f"JS 실행 오류: {str(e)}")
                    continue

                # 출석인정기간 관련 alert
                try:
                    WebDriverWait(self.driver, 3).until(EC.alert_is_present())
                    alert = self.driver.switch_to.alert
                    if "출석인정기간이 지나" in alert.text:
                        self.log("출석인정기간 경고: 자동 확인.")
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
                        self.log("본인인증 창 표시됨. 사용자 확인 대기...")
                        if callable(self.auth_confirm_callback):
                            self.auth_confirm_callback()
                            self.log("본인인증 완료.")
                except TimeoutException:
                    pass

                # 동영상 플레이어 페이지 로딩
                try:
                    WebDriverWait(self.driver, 10).until(EC.alert_is_present())
                    alert = self.driver.switch_to.alert
                    alert.accept()
                    time.sleep(4)
                    WebDriverWait(self.driver, 10).until(
                        EC.url_to_be("https://e-cyber.catholic.ac.kr/ilos/st/course/online_view_form.acl")
                    )
                except Exception as e:
                    self.log(f"동영상 페이지 진입 중 오류: {str(e)}")
                    continue

                # 영상 다운로드 로직
                self.handle_video_download(subject_info["과목"], week_num, title)

        self.log(f"{subject_info['과목']} 다운로드 완료.")

    def handle_video_download(self, subject_name, week_num, lesson_title):
        """
        iframe 안의 동영상 src를 추출해 mp4 다운로드 + mp3 변환
        """
        try:
            viewer = self.driver.find_element(By.ID, "contentViewer")
            actions = ActionChains(self.driver)
            actions.move_to_element(viewer).click().send_keys(Keys.SPACE).perform()
            time.sleep(3)
            actions.move_to_element(viewer).click()

            iframe = self.driver.find_element(By.TAG_NAME, "iframe")
            self.driver.switch_to.frame(iframe)

            # 동영상 element 찾기
            video_element = None
            try:
                video_element = self.driver.find_element(
                    By.XPATH, "//*[@id='syncvideo-play']/div/div[1]/div[1]/video"
                )
            except NoSuchElementException:
                pass
            if not video_element or not video_element.get_attribute("src"):
                try:
                    video_element = self.driver.find_element(
                        By.XPATH, "//*[@id='video-play-video1']/div[1]/video"
                    )
                except NoSuchElementException:
                    self.log("영상 엘리먼트를 찾지 못했습니다. 스킵.")
                    self.driver.switch_to.default_content()
                    return

            # 총 길이
            total_video_time = None
            try:
                total_video_time = self.driver.find_element(
                    By.XPATH, "/html/head/meta[13]"
                ).get_attribute("content")
            except:
                pass
            if not total_video_time:
                total_video_time = "99999"  # 혹시 실패 시 큰 값

            self.log(f"영상 총 길이: {total_video_time}")

            previous_url = None
            downloaded_duration = 0
            video_count = 1
            continuous_fail_count = 0

            while True:
                video_url = video_element.get_attribute("src")
                time.sleep(1)
                if video_url and video_url != previous_url:
                    filename = f"{subject_name}_{week_num}_{lesson_title}_{video_count}.mp4"
                    safe_filename = re.sub(r'[\\/*?:"<>|]', '_', filename)  # 윈도우 금칙문자 등 치환
                    file_path = os.path.join(self.download_dir, safe_filename)

                    self.log(f"다운로드 링크: {video_url}")
                    self.log(f"저장 파일: {file_path}")

                    self.driver.switch_to.default_content()
                    time.sleep(1)
                    # 다운로드
                    self.download_mp4(video_url, file_path)

                    # 다시 iframe
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
                    time.sleep(1)
                    # 키보드 화살표 키로 앞부분 탐색
                    for _ in range(6):
                        actions.move_to_element(viewer).click().send_keys(Keys.ARROW_RIGHT).perform()
                    iframe = self.driver.find_element(By.TAG_NAME, "iframe")
                    self.driver.switch_to.frame(iframe)
                    time.sleep(1)

        except Exception as e:
            self.log(f"동영상 다운로드 처리 중 오류: {str(e)}")
        finally:
            self.driver.switch_to.default_content()

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
