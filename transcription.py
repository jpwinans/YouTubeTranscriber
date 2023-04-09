import grpc
import os
import random
import time
import aiofile
import io
import asyncio

from google.cloud import speech_v1p1beta1 as speech
from pathlib import Path
from pydub import AudioSegment
from pydub import silence
from google.api_core.exceptions import InvalidArgument

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = 'client_secrets.json'


async def async_transcribe_audio(input_file, content, max_retries=3, retry_interval=5):
    print(f"Transcribing {input_file}")
    client = speech.SpeechAsyncClient()

    # Set up the request
    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-US",
        enable_automatic_punctuation=True,
    )

    retries = 0
    while retries < max_retries:
        try:
            response = await client.recognize(config=config, audio=audio)
            break
        except InvalidArgument as e:
            # If the error is "RecognitionAudio not set", return None as the transcript
            if "RecognitionAudio not set" in str(e):
                print(f"{input_file} has no audio data: returning None")
                return None
            else:
                raise e
        except grpc.aio._call.AioRpcError as e:
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                print(f"Error: {e.details()}. Retrying {input_file} transcription...")
                retries += 1
                time.sleep(retry_interval + random.uniform(-1, 1))
            else:
                raise e
    else:
        print(f"Failed to transcribe {input_file} after {max_retries} retries.")
        return None

    transcript = ""
    if response.results:
        for result in response.results:
            alternatives = result.alternatives
            for alternative in alternatives:
                transcript += alternative.transcript + " "

    return transcript.strip() if transcript else None

async def async_process_audio_chunk_and_transcribe(video_id, audio, current_time, split_time, output_dir, chunk_index):
    file_name = f"{video_id}_chunk_{chunk_index}"
    output_file = os.path.join(output_dir, f"{file_name}.wav")
    if not os.path.exists(output_file):
        sub_audio_segment = audio[current_time:(current_time + split_time)]

        # Convert the sub_audio_segment to mono 16 kHz WAV
        sub_audio_segment = sub_audio_segment.set_channels(1).set_frame_rate(16000)
        sub_audio_segment.export(output_file, format="wav")

    # Read the binary data from the output_file
    with io.open(output_file, "rb") as audio_file:
        content = audio_file.read()

    transcript_file = os.path.join(output_dir, f"{video_id}_chunk_{chunk_index}_transcript.txt")
    if not os.path.exists(transcript_file):
        transcript = await async_transcribe_audio(output_file, content)
        async with aiofile.AIOFile(transcript_file, "w") as f:
            await f.write(str(transcript))
    else:
        async with aiofile.AIOFile(transcript_file, "r") as f:
            transcript = await f.read()
    return transcript


async def split_audio(video_id, input_audio_path, cache_dir):
    CHUNK_DURATION = 60000

    audio_segment = AudioSegment.from_file(input_audio_path, input_audio_path.split('.')[-1])

    audio_segment = audio_segment.set_frame_rate(16000)
    audio_segment = audio_segment.set_channels(1)
    audio_segment = audio_segment.set_sample_width(2)

    current_time = 0
    chunk_index = 1

    tasks = []

    def get_middle_of_silent_interval(audio_segment, min_silence_length=1000, silence_threshold=-16):
        segment_length = 5000  # 20 seconds
        current_position = len(audio_segment)

        while current_position > 0:
            start_position = max(0, current_position - segment_length)
            current_segment = audio_segment[start_position:current_position]

            silent_ranges = silence.detect_silence(
                current_segment, min_silence_len=min_silence_length, silence_thresh=silence_threshold)

            if len(silent_ranges) > 0:
                start_silence, end_silence = silent_ranges[-1]
                middle_silence = (start_silence + end_silence) // 2
                middle_silence += start_position
                return middle_silence

            current_position -= segment_length

        return None

    def create_task(start, duration):
        nonlocal chunk_index
        tasks.append(
            async_process_audio_chunk_and_transcribe(
                video_id,
                audio_segment,
                start,
                duration,
                cache_dir,
                chunk_index,
            )
        )
        chunk_index += 1

    while current_time < len(audio_segment):
        if current_time == 0:
            end_time = CHUNK_DURATION
        else:
            end_time = min(current_time + CHUNK_DURATION, len(audio_segment))
        sub_audio_segment = audio_segment[current_time:end_time]

        middle_silence = get_middle_of_silent_interval(sub_audio_segment)

        if middle_silence is not None:
            chunk_end_time = current_time + middle_silence

            # If it's the first chunk, add the initial part as a separate chunk
            if current_time == 0:
                create_task(current_time, middle_silence)
                current_time = chunk_end_time
                continue

            create_task(current_time, chunk_end_time - current_time)

            current_time = chunk_end_time  # Update the current_time to the middle of the last detected silence
        else:
            create_task(current_time, CHUNK_DURATION)
            current_time += CHUNK_DURATION

    # Add the last chunk if there's any remaining audio
    if current_time < len(audio_segment):
        create_task(current_time, len(audio_segment) - current_time)

    transcripts = await asyncio.gather(*tasks)
    return transcripts
