import os
from flask import Flask, request, jsonify
import instaloader
import re
import tempfile
import requests

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Приветствия и инструкции
MESSAGES = {
    "en": {
        "welcome": "👋 Welcome! This bot helps you download Instagram Reels. Please choose your language:",
        "instruction": (
            "You can send me a link directly or add me to a group, and I'll process links shared there.\n\n"
            "Commands:\n"
            "/start - Restart the bot\n"
            "/help - Get instructions"
        ),
        "language_updated": "✅ Language updated to English.",
        "invalid_link": "❌ This is not a valid Instagram Reel link. Please send a correct link.",
        "processing": "⏳ Processing your request...",
        "success": "✅ Reel downloaded successfully!",
        "error": "❌ Failed to download the Reel. Please try again later.",
    },
    # Дополнительные языки можно добавить аналогично
}

USER_LANGUAGES = {}

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if not data:
        return jsonify({"message": "No data received"}), 400

    if "message" in data:
        handle_message(data["message"])

    return jsonify({"message": "OK"}), 200


def handle_message(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    lang = USER_LANGUAGES.get(chat_id, "en")

    if text == "/start":
        send_start_message(chat_id)
    elif is_instagram_reel_link(text):
        download_and_send_reel(chat_id, text, lang)
    else:
        send_message(chat_id, MESSAGES[lang]["invalid_link"])


def is_instagram_reel_link(text):
    """Проверка, является ли текст ссылкой на Instagram Reel."""
    pattern = r"(https?:\/\/(?:www\.)?instagram\.com\/reel\/[a-zA-Z0-9_-]+)"
    return re.match(pattern, text) is not None


def send_start_message(chat_id):
    """Отправка приветствия."""
    lang = "en"
    message = f"{MESSAGES[lang]['welcome']}\n\n{MESSAGES[lang]['instruction']}"
    send_message(chat_id, message)


def send_message(chat_id, text):
    """Отправка сообщения в Telegram."""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)


def download_and_send_reel(chat_id, url, lang):
    """Скачивание и отправка рилса."""
    try:
        send_message(chat_id, MESSAGES[lang]["processing"])

        # Инициализация instaloader
        loader = instaloader.Instaloader(save_metadata=False, download_video_thumbnails=False)
        loader.login(user="your_instagram_username", passwd="your_instagram_password")

        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            loader.download_post(instaloader.Post.from_shortcode(loader.context, url.split("/")[-2]), target=".")

            video_file = next(Path(temp_dir).rglob("*.mp4"))

            # Отправка видео
            with open(video_file, "rb") as video:
                requests.post(
                    f"{TELEGRAM_API_URL}/sendVideo",
                    data={"chat_id": chat_id},
                    files={"video": video},
                )

        send_message(chat_id, MESSAGES[lang]["success"])
    except Exception as e:
        send_message(chat_id, f"{MESSAGES[lang]['error']}\n\nError: {e}")


@app.route('/')
def index():
    return "Server is running", 200


if __name__ == "__main__":
    app.run(debug=True)
