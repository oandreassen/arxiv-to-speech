import requests
from io import BytesIO
import shutil


def text_to_voice(title: str, text: str, token: str, dest: str):
    url = "https://audio.api.speechify.dev/v1/synthesis/get"

    payload = {
        "ssml": f"<speak>This paper is called '{title}'. {text}</speak>",
        "voice": {"name": "Presidential", "engine": "speechify", "language": "en-US"},
        "forcedAudioFormat": "mp3",
    }
    headers = {
        "authorization": f"Bearer {token}",
        "Content-type": "application/json",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
    }

    response = requests.request("POST", url, headers=headers, json=payload)

    if response.status_code != 200:
        print(response.text)

    with open(dest, "wb") as out_file:
        out_file.write(response.content)
