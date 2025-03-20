import os
from moviepy.editor import VideoFileClip, concatenate_videoclips


def find_videos(path="."):
    """현재 디렉터리 및 하위 디렉터리에서 mp4 동영상 찾기"""
    video_files = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(".mp4"):
                video_files.append(os.path.join(root, file))
    return video_files


def concatenate_videos(video_files, output_file):
    """여러 동영상을 하나로 합치기"""
    clips = [VideoFileClip(vf) for vf in video_files]
    concatenated_clip = concatenate_videoclips(clips)
    concatenated_clip.write_videofile(output_file)


def convert_videos_to_audio(video_files):
    """여러 동영상에서 오디오 추출하기"""
    for video_file in video_files:
        video = VideoFileClip(video_file)
        audio = video.audio
        output_audio = os.path.splitext(video_file)[0] + ".mp3"
        audio.write_audiofile(output_audio)
        print(f"'{output_audio}'에 오디오가 저장되었습니다.")


def main():
    while True:
        directory_path = input("동영상을 찾을 디렉터리 경로를 입력하세요 (기본: 현재 디렉터리): ")
        directory_path = directory_path or "."

        print("\n1: 동영상 합치기")
        print("2: 동영상에서 오디오 추출하기")
        print("3: 종료")
        choice = input("원하는 기능을 선택하세요 (1/2/3): ")

        video_files = find_videos(directory_path)
        if not video_files:
            print("해당 디렉터리에 동영상 파일을 찾을 수 없습니다.")
            continue

        if choice == "1":
            print("\n[동영상 목록]")
            for idx, video in enumerate(video_files, 1):
                print(f"{idx}. {video}")

            selected = input("\n합칠 동영상 번호를 공백으로 구분하여 입력하세요 (예: 1 2 3): ")
            selected_videos = [video_files[int(i) - 1] for i in selected.split()]

            output_file = input("출력 동영상 파일명을 입력하세요 (예: output.mp4): ")
            concatenate_videos(selected_videos, output_file)
            print(f"'{output_file}'에 동영상이 저장되었습니다.")

        elif choice == "2":
            print("\n[동영상 목록]")
            for idx, video in enumerate(video_files, 1):
                print(f"{idx}. {video}")

            selected = input("\n오디오를 추출할 동영상 번호를 공백으로 구분하여 입력하세요 (예: 1 2 3): ")
            selected_videos = [video_files[int(i) - 1] for i in selected.split()]

            convert_videos_to_audio(selected_videos)

        elif choice == "3":
            print("프로그램을 종료합니다.")
            break


if __name__ == "__main__":
    main()
