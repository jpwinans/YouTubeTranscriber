import os
import sys
import concurrent.futures

from pytube import YouTube
from utils import to_linux_filename


def stream_downloaded(output_dir, stream, video_id):
    filename = stream.download(output_dir)
    filepath = os.path.join(output_dir, filename)
    return filepath


def download_audio(video_url, output_dir, video_id):
    yt = YouTube(video_url)
    title = yt.title
    audio_file_path = os.path.join(output_dir, "{}.mp4".format(to_linux_filename((title))))

    if not os.path.exists(audio_file_path):

        streams = yt.streams.filter(only_audio=True).order_by("abr").desc()

        if streams:
            with concurrent.futures.ProcessPoolExecutor() as executor:
                for stream in streams:
                    old_filepath = executor.submit(stream_downloaded, output_dir, stream, video_id)
            print(f"Downloaded audio files to: {output_dir}")

            # Remove .webm file
            if old_filepath.result().endswith(".webm"):
                os.remove(old_filepath.result())

        else:
            print("No audio stream found")
            sys.exit(1)
    else:
        print(f"Audio file already exists at: {output_dir}")

    return audio_file_path
