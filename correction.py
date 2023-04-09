import openai
import asyncio
import aiohttp

from utils import open_file

openai.api_key = open_file('openai_key.txt')


def split_text_into_chunks(text, max_tokens):
    tokens = text.split(" ")
    chunks = []
    current_chunk = ""

    for token in tokens:
        if len(current_chunk + token) <= max_tokens:
            current_chunk += token + " "
        else:
            # Remove tokens after the last period
            last_period_idx = current_chunk.rfind('.')
            if last_period_idx != -1:
                remaining_text = current_chunk[last_period_idx + 1:].strip()
                current_chunk = current_chunk[:last_period_idx + 1].strip()
            else:
                remaining_text = current_chunk.strip()

            chunks.append(current_chunk)

            # Add remaining text to the next current_chunk
            current_chunk = remaining_text + " " + token + " "

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def extract_block(text, block_name):
    lines = text.split("\n")
    target_block = []
    start_block = False

    for line in lines:
        if block_name == "TRANSCRIPT" and not start_block:
            start_block = True

        if line.startswith("NOTES:"):
            if block_name == "NOTES":
                start_block = True
                continue
            else:
                break

        if start_block and line:
            target_block.append(line)

    return "\n".join(target_block)


async def gpt_completion(prompt, idx=0, summary=False):
    if summary:
        print("Calling GPT Summarization...")
    else:
        print(f"Calling GPT Correction on chunk {idx}...")

    url = "https://api.openai.com/v1/engines/text-davinci-003/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai.api_key}"
    }
    data = {
        "prompt": prompt,
        "max_tokens": 1648,
        "n": 1,
        "stop": None,
        "temperature": 0.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            result = await response.json()

            if summary:
                print("Received summarization")
            else:
                print(f"Received correction for chunk {idx}")

            return result['choices'][0]['text'].strip()
    

async def correct_chunk(chunk, idx=0):
    prompt = open_file('prompt_correct.txt').replace('<<TRANSCRIPT>>', chunk)
    return await gpt_completion(prompt, idx)


async def summarize_notes(notes):
    prompt = open_file('prompt_summary.txt').replace('<<NOTES>>', '\n'.join(notes))
    return await gpt_completion(prompt, summary=True)


# Function to correct and recombine the final human-readable transcript
async def correct_and_recombine(input_filename, output_filename):
    print(f"Correcting {input_filename} with GPT")

    content = open_file(input_filename)

    chunks = split_text_into_chunks(content, 1500)

    # Create a list of coroutines with previous_chunk and chunk
    coroutines = [correct_chunk(chunk, idx) for idx, chunk in enumerate(chunks)]

    # Run the coroutines concurrently using asyncio.gather
    corrected_chunks = await asyncio.gather(*coroutines)

    # Extract the transcript and notes from the corrected_chunks
    transcripts = [extract_block(chunk, 'TRANSCRIPT') for chunk in corrected_chunks]
    notes = [extract_block(chunk, 'NOTES') for chunk in corrected_chunks]

    with open(output_filename, "w") as output_file:
        for chunk in transcripts:
            output_file.write(chunk)
            output_file.write("\n\n")
        
        output_file.write("NOTES:\n{}\n\n".format('\n'.join(notes)))
        output_file.write("SUMMARY:\n\n")
        output_file.write(await summarize_notes(notes))

    print(f"Corrected transcript saved to {output_filename}")