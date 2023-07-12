import os
import re
import requests
from bs4 import BeautifulSoup
import openai
from PyPDF2 import PdfReader
from dotenv import load_dotenv
import tiktoken
from text_to_voice import speechify

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

MODEL = "gpt-4"

encoding = tiktoken.encoding_for_model(MODEL)


def get_token_count(text: str) -> int:
    return len(list(encoding.encode(text)))


def truncate_text(text: str, max_length: int) -> str:
    # if text is longer then max_length, truncate it to max_length
    return text[:max_length]


def extract_text_from_pdf(pdf_path):
    pdf = PdfReader(pdf_path)
    text = " ".join(page.extract_text() for page in pdf.pages)
    return text


# def truncate_text(text: str, max_tokens: int) -> str:
#     tokens = list(encoding.encode(text))
#     if len(tokens) > max_tokens:
#         return "".join(tokens[:max_tokens])
#     return text


def main():
    os.makedirs("./pdfs", exist_ok=True)
    os.makedirs("./output", exist_ok=True)

    # Download the webpage
    response = requests.get(
        "https://arxiv.org/search/advanced?advanced=1&terms-0-operator=AND&terms-0-term=&terms-0-field=title&classification-computer_science=y&classification-physics_archives=all&classification-include_cross_list=include&date-filter_by=all_dates&date-year=&date-from_date=&date-to_date=&date-date_type=submitted_date&abstracts=show&size=100&order=-announced_date_first"
    )
    soup = BeautifulSoup(response.content, "html.parser")

    # Parse the HTML to find the articles
    articles = soup.find_all("li", {"class": "arxiv-result"})

    for article in articles:
        title_element = article.find("p", {"class": "title is-5 mathjax"})
        title = title_element.text.strip()
        abstract = article.find(
            "span", {"class": "abstract-full has-text-grey-dark mathjax"}
        ).text.strip()

        # Find all 'a' tags and keep only those that contain 'pdf' in their text
        all_links = article.find_all("a")
        pdf_links = [link for link in all_links if "pdf" in link.text.lower()]

        # If no PDF link is found, move to the next article
        if not pdf_links:
            continue

        # If there are multiple PDF links, this takes the URL of the first one
        pdf_url = pdf_links[0]["href"]

        # Sanitize the title by replacing invalid characters
        sanitized_title = re.sub(r'[\/:*?"<>|]', "", title)
        pdf_path = os.path.join("./pdfs", f"{sanitized_title}.pdf")

        if os.path.exists(pdf_path):
            # If the PDF already exists, skip it
            print(f"Skipping {pdf_path}")
            continue

        print(f"Downloading {pdf_path}")

        # Download the PDF
        response = requests.get(pdf_url)
        with open(pdf_path, "wb") as f:
            f.write(response.content)

        # Use GPT-3 to determine if the paper is related to AI or generative AI
        chat = openai.ChatCompletion.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": f"This is a paper titled '{title}' and its abstract is '{abstract}'. Is it related to generative AI and is applicable to existing modlels?",
                },
            ],
        )

        if "yes" in chat.choices[0].message["content"].lower():
            # Extract text from the PDF
            text = extract_text_from_pdf(pdf_path)

            print(f"Extracted {get_token_count(text)} tokens from {pdf_path}")

            # Truncate the text if it exceeds 7000 tokens
            text = truncate_text(text, 20000)

            # Use GPT-3 to create a summary
            with open("system.txt", "r") as f:
                system_prompt = f.read()
            chat = openai.ChatCompletion.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
            )
            summary = chat.choices[0].message["content"]

            # Save the summary
            with open(f"./output/{sanitized_title}.md", "w") as f:
                f.write(summary)

            print(f"Saved summary for {pdf_path}")

            destination = f"./output/{sanitized_title}.mp3"

            print(f"Generating audio for {pdf_path}")

            speechify.text_to_voice(
                sanitized_title, summary, os.getenv("SPEECHIFY_TOKEN"), destination
            )

            print(f"Playing audio for {pdf_path}")

            os.system(f'afplay "{destination}"')
        else:
            print(f"Skipping {title}, as it's not related to generative AI")


if __name__ == "__main__":
    main()
