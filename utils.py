import re


def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()


def to_linux_filename(s, max_length=255):
    # Replace invalid characters with underscores
    s = re.sub(r'[\/:*?"<>|,]', '', s)

    # Convert the string to bytes to account for non-ASCII characters
    s_bytes = s.encode('utf-8')

    # Truncate the filename if it's too long
    if len(s_bytes) > max_length:
        s_bytes = s_bytes[:max_length]
        # Convert back to string
        s = s_bytes.decode('utf-8', 'ignore')

    return s


def extract_video_id(video_url):
    video_id_pattern = r"(?:v=|\/)([0-9A-Za-z_-]{10}[048AEIMQUYcgkosw])"
    match = re.search(video_id_pattern, video_url)

    if match:
        video_id = match.group(1)
        return video_id
    else:
        raise ValueError(f"Invalid YouTube video URL: {video_url}")


def combine_transcripts(video_id, transcripts, output_filename="combined_transcript.txt"):
    with open(output_filename, "w") as output_file:
        for transcript in transcripts:
            if transcript and transcript != "None":  # Check if the transcript is not None and not the string "None"
                output_file.write(transcript)
                output_file.write("\n\n")  # Add an empty line between transcripts for readability

    print(f"Combined transcript saved to {output_filename}")
