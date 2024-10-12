import openai
import nltk
import math
import tiktoken
from nltk.tokenize import sent_tokenize
import sys
import os
import argparse
from dotenv import load_dotenv

load_dotenv()

def count_tokens(text, encoding_name='gpt2'):
    """
    Counts the number of tokens in a text string using the specified encoding.
    """
    print(f"Counting tokens for text: {text[:50]}...")
    encoding = tiktoken.get_encoding(encoding_name)
    tokens = encoding.encode(text)
    print(f"Token count: {len(tokens)}")
    return len(tokens)

def split_text_into_chunks(text, max_tokens, overlap_tokens):
    """
    Splits text into chunks of approximately max_tokens tokens, with overlap.
    """
    print("Splitting text into chunks...")
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)
    sentences = sent_tokenize(text)
    chunks = []
    current_chunk = ''
    current_tokens = 0
    overlap = []
    overlap_token_count = 0

    for sentence in sentences:
        token_count = count_tokens(sentence)
        if current_tokens + token_count <= max_tokens:
            current_chunk += ' ' + sentence
            current_tokens += token_count
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
                print(f"Created chunk of length {current_tokens} tokens.")
            current_chunk = ' '.join(overlap) + ' ' + sentence
            current_tokens = overlap_token_count + token_count
            overlap = []

        # Maintain overlap
        overlap.append(sentence)
        overlap_token_count = count_tokens(' '.join(overlap))
        while overlap_token_count > overlap_tokens:
            overlap.pop(0)
            overlap_token_count = count_tokens(' '.join(overlap))

    if current_chunk:
        chunks.append(current_chunk.strip())
        print(f"Created final chunk of length {current_tokens} tokens.")

    print(f"Total number of chunks: {len(chunks)}")
    return chunks

def summarize_chunk(client, chunk, prompt_instructions="", max_summary_tokens=None):
    """
    Summarizes a text chunk using OpenAI's GPT-3.5 Turbo model.
    """
    print(f"Summarizing chunk: {chunk[:50]}...")
    prompt = f"{prompt_instructions}\n\nText:\n{chunk}\n\nSummary:"
    try:
        response = client.chat.completions.create(
            model='deepseek-chat',  # You can switch to 'gpt-4' if you have access
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=max_summary_tokens,
            temperature=0.7,
        )
        summary = response.choices[0].message.content.strip()
        print(f"Summary generated: {summary[:50]}...")
        return summary
    except Exception as e:
        print(f"An error occurred: {e}")
        return ""

def main():
    # Command line arguments
    parser = argparse.ArgumentParser(description="Chunk-based text summarization script.")
    parser.add_argument('--max-chunk-tokens', type=int, default=2000, help="Maximum tokens per chunk.")
    parser.add_argument('--overlap-tokens', type=int, default=200, help="Number of overlapping tokens between chunks.")
    parser.add_argument('--max-summary-tokens', type=int, help="Maximum tokens per summary.")
    parser.add_argument('--prompt-instructions', type=str, default="Please provide a concise summary of the following text.", help="Prompt instructions for the summarization model.")
    parser.add_argument('--second-level-summarization', type=bool, default=True, help="Whether to perform a second-level summarization.")
    parser.add_argument('--second-level-prompt', type=str, help="Prompt instructions for the second-level summarization.")
    parser.add_argument('--base-url', type=str, default="https://api.deepseek.com", help="Base URL for the API endpoint.")
    args = parser.parse_args()

    # Parameters
    max_chunk_tokens = args.max_chunk_tokens           # Adjust based on the model's token limit
    overlap_tokens = args.overlap_tokens               # Number of overlapping tokens between chunks
    max_summary_tokens = args.max_summary_tokens       # Max tokens for each chunk summary
    prompt_instructions = args.prompt_instructions     # Instructions for the summarization
    second_level_summarization = args.second_level_summarization # Set to False if you don't want a second-level summary
    second_level_prompt = args.second_level_prompt if args.second_level_prompt else prompt_instructions # Second-level prompt instructions
    base_url = args.base_url                           # API base URL

    # Set up OpenAI API key
    print("Loading OpenAI API key from environment...")
    client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'), base_url=base_url)

    # Read the long document from stdin
    print("Reading input text from stdin...")
    text = sys.stdin.read()
    print(f"Input text length: {len(text)} characters.")

    # Split the text into chunks
    chunks = split_text_into_chunks(text, max_chunk_tokens, overlap_tokens)

    print(f"Total chunks created: {len(chunks)}\n")

    # Summarize each chunk
    summaries = []
    for i, chunk in enumerate(chunks):
        print(f"Summarizing chunk {i+1}/{len(chunks)}...")
        summary = summarize_chunk(client, chunk, prompt_instructions, max_summary_tokens)
        summaries.append(summary)

    # Combine summaries
    combined_summary = ' '.join(summaries)
    print("Combined all chunk summaries.")

    # Optional: Second-level summarization
    if second_level_summarization:
        print("\nPerforming second-level summarization...\n")
        final_summary = summarize_chunk(client, combined_summary, second_level_prompt, max_summary_tokens)
    else:
        final_summary = combined_summary

    # Output the final summary
    print("\nFinal Summary:\n")
    print(final_summary)

    # Save the summary to a file
    with open('final_summary.txt', 'w', encoding='utf-8') as file:
        print("Saving the final summary to 'final_summary.txt'...")
        file.write(final_summary)

if __name__ == '__main__':
    main()