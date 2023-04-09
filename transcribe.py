import asyncio
import os
import sys

from correction import correct_and_recombine
from pathlib import Path
from transcription import split_audio
from utils import combine_transcripts
from utils import extract_video_id
from video import download_audio
from warnings import simplefilter

simplefilter("ignore", UserWarning)
simplefilter("ignore", FutureWarning)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <video_url>")
        sys.exit(1)

    video_url = sys.argv[1]
    video_id = extract_video_id(video_url)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(current_dir, "audio_files")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    input_audio_path = download_audio(video_url, output_dir, video_id)

    cache_dir = os.path.join(output_dir, video_id)
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    transcripts = asyncio.run(split_audio(video_id, input_audio_path, cache_dir))

    output_filename = f"{current_dir}/transcriptions/{video_id}_transcript.txt"
    combine_transcripts(video_id, transcripts, output_filename)

    output_filename = f"{current_dir}/transcriptions/{video_id}_transcript.txt"
    corrected_output_filename = f"{current_dir}/transcriptions/{video_id}_corrected_transcript.txt"
    asyncio.run(correct_and_recombine(output_filename, corrected_output_filename))
