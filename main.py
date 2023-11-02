import os
import re
import time

import requests
import tqdm as tq
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from moviepy.editor import VideoFileClip


def login(username, password):
    driver.get("https://e-cyber.catholic.ac.kr/ilos/main/member/login_form.acl")
    driver.find_element(By.ID, "usr_id").send_keys(username)
    driver.find_element(By.ID, "usr_pwd").send_keys(password)
    driver.find_element(By.ID, "login_btn").click()
    time.sleep(1)


def switch_to_regular_subjects_tab():
    tab_element = driver.find_element(By.ID, "list_tab1")
    tab_element.click()


def get_subject_info_list():
    subjects = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "content-container")))
    subject_info_list = []

    for subject in subjects:
        try:
            subject_title = subject.find_element(By.CLASS_NAME, "content-title").text
            eclass_room_attr = subject.find_element(By.TAG_NAME, "a").get_attribute("onclick")
            eclass_room_value = re.search(r"eclassRoom\('(.+?)'\)", eclass_room_attr).group(1)
            subject_info_list.append({"과목": subject_title, "eclassRoom": eclass_room_value})
            print(f"과목: {subject_title}, eclassRoom: {eclass_room_value}")
        except Exception as e:
            print(f"오류 발생: {e}")

    return subject_info_list


def perform_subject_actions(subject_info, start_week=None):
    driver.get("https://e-cyber.catholic.ac.kr/ilos/mp/course_register_list_form.acl")
    eclass_room_attr = f"eclassRoom('{subject_info['eclassRoom']}');"
    driver.execute_script(eclass_room_attr)
    print("작동 중 과목 정보:", subject_info)

    # Click on 'menu_lecture_weeks'
    driver.find_element(By.ID, "menu_lecture_weeks").click()

    time.sleep(2)

    try:
        week_elements = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.XPATH, '//div[@id="chart"]//div[contains(@class, "wb-week")]')))
        weeks_info = {}

        for week_element in week_elements:
            week_text = week_element.text
            week_num = int(week_text.replace("주", ""))

            if start_week is not None and week_num < start_week:
                continue  # 특정 차시 이후부터 학습하기 위해, 지정한 차시 이전의 주차는 건너뜁니다.

            week_parent_element = week_element.find_element(By.XPATH, '..')
            lesson_info = week_parent_element.find_element(By.XPATH, './div[@class="wb-status"]').text
            lesson_total = int(lesson_info.split('/')[1])

            weeks_info[week_num] = lesson_total

            week_element.click()
            time.sleep(2)

            lecture_elements = driver.find_elements(By.XPATH, f'//*[starts-with(@id, "lecture-")]')

            for lecture_element in lecture_elements:
                lesson_elements = lecture_element.find_elements(By.XPATH, './div/ul/li[1]/ol/li[5]/div/div/div[1]/div/span')

                for lesson_element in lesson_elements:
                    lesson_title = lesson_element.text
                    js_script = lesson_element.get_attribute('onclick')
                    print(f"주차: {week_num}, 제목: {lesson_title}, 학습하기 스크립트: {js_script}")

                    # JS 스크립트 실행
                    driver.execute_script(js_script)

                    # 팝업창 확인 클릭
                    try:
                        WebDriverWait(driver, 10).until(EC.alert_is_present())
                        alert = driver.switch_to.alert
                        alert.accept()
                        time.sleep(5)

                        # 페이지가 바뀌는지 확인
                        WebDriverWait(driver, 10).until(
                            EC.url_to_be("https://e-cyber.catholic.ac.kr/ilos/st/course/online_view_form.acl"))

                        # 재생 버튼을 클릭
                        # "viewer-root" 요소를 찾습니다.
                        viewer = driver.find_element(By.ID, 'contentViewer')

                        # ActionChains 객체를 생성합니다.
                        actions = ActionChains(driver)

                        # "viewer-root" 요소를 클릭하고 스페이스바를 누릅니다. (시작)
                        actions.move_to_element(viewer).click().send_keys(Keys.SPACE).perform()

                        time.sleep(5)

                        # "viewer-root" 요소를 클릭하고 스페이스바를 누릅니다.
                        actions.move_to_element(viewer).click()

                        # iframe을 찾습니다. 이때 iframe의 'src' 속성을 통해 내부 페이지 URL을 알아낼 수 있습니다.
                        iframe = driver.find_element(By.TAG_NAME, 'iframe')
                        iframe_src = iframe.get_attribute('src')

                        # iframe 내부 페이지로 전환합니다.
                        driver.switch_to.frame(iframe)

                        # XPath를 사용하여 영상 요소를 찾습니다.
                        try:
                            video_element = driver.find_element(By.XPATH,
                                                                '//*[@id="syncvideo-play"]/div/div[1]/div[1]/video')
                        except NoSuchElementException:
                            video_element = None

                        # src 속성이 없으면 다음 XPath를 사용하여 다시 동영상 엘리먼트를 찾습니다.
                        if not video_element or not video_element.get_attribute("src"):
                            try:
                                video_element = driver.find_element(By.XPATH,
                                                                    '//*[@id="video-play-video1"]/div[1]/video')
                            except NoSuchElementException:
                                print("영상 엘리먼트를 찾지 못했습니다. | 동영상이 정상적으로 재생 가능한지 확인 해 주세요.")
                                driver.back()
                                time.sleep(2)
                                pass

                        # 동영상의 총 재생 시간을 가져옵니다.
                        total_video_time = driver.find_element(By.XPATH, '/html/head/meta[13]').get_attribute("content")
                        print(f"동영상 총 길이: {total_video_time}")

                        previous_url = None  # 이전에 다운로드한 동영상 URL을 저장합니다.
                        downloaded_duration = 0  # 이전까지 다운로드한 동영상들의 재생 시간을 누적합니다.
                        video_count = 1
                        continuous_fail_count = 0  # 연속해서 받지 못한 URL 개수를 저장합니다.

                        while True:  # 동영상이 끝날 때까지 반복합니다.
                            # 영상 요소의 'src' 속성을 이용하여 mp4 주소를 가져옵니다.
                            video_url = video_element.get_attribute('src')
                            time.sleep(1)

                            if video_url and video_url != previous_url:  # 새로운 동영상 URL을 확인합니다.
                                mp4_filename_alt = f"{subject_info['과목']}_{week_num}_{lesson_title}_{video_count}.mp4"
                                print(f"다운로드 링크: {video_url}")
                                print(f"다운로드 파일명: {mp4_filename_alt}")

                                # 메인 프레임으로 돌아옵니다.
                                driver.switch_to.default_content()
                                time.sleep(2)

                                # 동영상의 위치를 이동시킵니다. (6번 전진)
                                # "viewer-root" 요소를 찾습니다.
                                viewer = driver.find_element(By.ID, 'contentViewer')

                                # ActionChains 객체를 생성합니다.
                                actions = ActionChains(driver)

                                actions.move_to_element(viewer).click().send_keys(Keys.SPACE).perform() # 일시 중지

                                download_mp4(video_url, mp4_filename_alt)

                                # iframe을 찾습니다. 이때 iframe의 'src' 속성을 통해 내부 페이지 URL을 알아낼 수 있습니다.
                                iframe = driver.find_element(By.TAG_NAME, 'iframe')
                                iframe_src = iframe.get_attribute('src')

                                # iframe 내부 페이지로 전환합니다.
                                driver.switch_to.frame(iframe)
                                time.sleep(2)

                                previous_url = video_url  # 이전 URL을 업데이트합니다.
                                video_count += 1
                                continuous_fail_count = 0  # 성공적으로 URL을 받아온 경우, 연속 실패 횟수를 초기화합니다.

                                # 다운로드한 비디오 파일의 재생 시간을 확인합니다.
                                downloaded_video_duration = get_video_duration(mp4_filename_alt)
                                downloaded_duration += int(downloaded_video_duration)
                                print(f"현재까지 받은 시간: {downloaded_duration}")

                                video_url = None

                                # 만약 다운로드한 비디오의 재생 시간이 전체 비디오의 시간과 같거나 크다면, 다운로드를 중지합니다.
                                if int(downloaded_duration) >= int(total_video_time)-1:
                                    print("최종 다운로드 완료.")
                                    break
                            else:  # 다운로드가 중복되거나 오류가 발생한 경우
                                continuous_fail_count += 1
                                if continuous_fail_count >= 999:
                                    print("연속해서 URL을 받아오지 못하여 종료합니다.")
                                    break

                                # 메인 프레임으로 돌아옵니다.
                                driver.switch_to.default_content()
                                time.sleep(2)

                                # 동영상의 위치를 이동시킵니다. (6번 전진)
                                # "viewer-root" 요소를 찾습니다.
                                viewer = driver.find_element(By.ID, 'contentViewer')

                                # ActionChains 객체를 생성합니다.
                                actions = ActionChains(driver)

                                time.sleep(2)

                                for _ in range(6):
                                    actions.move_to_element(viewer).click().send_keys(Keys.ARROW_RIGHT).perform()

                                # iframe을 찾습니다. 이때 iframe의 'src' 속성을 통해 내부 페이지 URL을 알아낼 수 있습니다.
                                iframe = driver.find_element(By.TAG_NAME, 'iframe')
                                iframe_src = iframe.get_attribute('src')

                                # iframe 내부 페이지로 전환합니다.
                                driver.switch_to.frame(iframe)
                                time.sleep(2)

                                # 새로운 비디오를 위해 video_url 초기화
                                video_url = None

                        # 메인 프레임으로 돌아옵니다.
                        driver.switch_to.default_content()
                        time.sleep(2)

                        # 이후 원래 페이지로 돌아가는 로직 (예를 들면, driver.back() 등)
                        driver.back()
                        time.sleep(2)

                    except Exception as e:
                        print("에러가 발생하였습니다.:", str(e))
                    except:
                        print("팝업창 동의 실패.")
                        pass

    except (TimeoutException, NoSuchElementException) as e:
        print("주차 정보를 찾을 수 없습니다.")


def download_mp4(url, file_name):
    try:
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024  # 1 KB
        downloaded_size = 0

        with open(file_name, "wb") as mp4_file:
            with tq.tqdm(total=total_size, unit="B", unit_scale=True, desc=file_name, ascii=True) as progress_bar:
                for data in response.iter_content(block_size):
                    mp4_file.write(data)
                    downloaded_size += len(data)
                    progress_bar.update(len(data))

        print("\n다운로드 완료.")
    except Exception as e:
        print("다운로드 실패:", str(e))

    return downloaded_size


def get_video_duration(file_path):
    clip = VideoFileClip(file_path)
    video_duration = clip.duration
    return video_duration


if __name__ == "__main__":
    with webdriver.Chrome() as driver:
        login("사용자 ID", "사용자 비밀번호")

        driver.get("https://e-cyber.catholic.ac.kr/ilos/mp/course_register_list_form.acl")

        switch_to_regular_subjects_tab()

        subject_info_list = get_subject_info_list()

        unique_subject_titles = set()

        # 과목 목록 출력
        for index, subject_info in enumerate(subject_info_list):
            subject_title = subject_info['과목']
            if subject_title not in unique_subject_titles:
                unique_subject_titles.add(subject_title)
                print(f"{index + 1}. {subject_title}")

        # User input for subject selection
        selected_index = input("실행할 과목의 번호를 선택하세요 (1부터 시작) 또는 0을 입력하면 전체 과목을 선택합니다: ")

        if selected_index == '0':  # All subjects selected
            # User input for specific week selection
            selected_week = input("시작할 주차를 입력하세요 (0을 입력하면 전체 주차를 선택합니다): ")
            selected_week = int(selected_week) if selected_week.isdigit() else None
            for subject_info in subject_info_list:
                perform_subject_actions(subject_info, start_week=selected_week)
        else:  # Single subject selected
            selected_index = int(selected_index)
            selected_subject_info = subject_info_list[selected_index - 1]
            # User input for specific week selection
            selected_week = input("시작할 주차를 입력하세요 (0을 입력하면 전체 주차를 선택합니다): ")
            selected_week = int(selected_week) if selected_week.isdigit() else None
            perform_subject_actions(selected_subject_info, start_week=selected_week)


