from flask import Flask, request, jsonify
import os
import requests
import instaloader
from collections import defaultdict

app = Flask(__name__)

WEBHOOK_URL = "https://testbot-clean.vercel.app/webhook"
TELEGRAM_TOKEN = "7648873218:AAGs6RZlBrVjr1TkmMjO-jvoFT8PxXvSjyM"

# Хранилище языковых настроек пользователей
user_languages = defaultdict(lambda: "ru")  # По умолчанию русский язык

# Сообщения на разных языках
messages = {
    "start": {
        "ru": "Привет! Выберите язык:",
        "en": "Hello! Please choose a language:",
        "vi": "Xin chào! Vui lòng chọn ngôn ngữ:"
    },
    "language_set": {
        "ru": "Язык успешно установлен: Русский.",
        "en": "Language set to: English.",
        "vi": "Ngôn ngữ đã được chọn: Tiếng Việt."
    },
    "processing": {
        "ru": "Обрабатываю ссылку, подождите...",
        "en": "Processing your link, please wait...",
        "vi": "Đang xử lý liên kết của bạn, vui lòng đợi..."
    },
    "error": {
        "ru": "Не удалось скачать видео. Пожалуйста, проверьте ссылку.",
        "en": "Failed to download the video. Please check the link.",
        "vi": "Không tải được video. Vui lòng kiểm tra liên kết."
    }
}

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print(f"Received data: {data}")  # Лог входящего запроса

    if data and "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "").strip().lower()
        print(f"Chat ID: {chat_id}, Text: {text}")  # Лог ID чата и текста сообщения

        # Команда /start
        if text == "/start":
            send_language_selection(chat_id)
            return jsonify({"message": "Start command processed"}), 200

        # Выбор языка
        if text in ["русский", "english", "vietnamese"]:
            lang = "ru" if text == "русский" else "en" if text == "english" else "vi"
            user_languages[chat_id] = lang
            print(f"Language set for {chat_id}: {lang}")  # Лог выбора языка

            send_message(chat_id, messages["language_set"][lang])
            return jsonify({"message": "Language set"}), 200

        # Обработка ссылки на Reels
        if 'instagram.com/reel/' in text:
            lang = user_languages[chat_id]
            send_message(chat_id, messages["processing"][lang])
            success = send_reels_video(chat_id, text.strip())
            if not success:
                send_message(chat_id, messages["error"][lang])
        else:
            send_message(chat_id, "⚠️ Отправьте ссылку на Reels.")

    return jsonify({"message": "Webhook received!"}), 200

@app.route('/')
def index():
    return "Server is running", 200

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    response = requests.post(url, json=payload)
    print(f"Sent message to {chat_id}: {text}")  # Лог отправленного сообщения
    return response

def send_language_selection(chat_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": messages["start"]["ru"],
        "reply_markup": {
            "keyboard": [
                [{"text": "Русский"}],
                [{"text": "English"}],
                [{"text": "Vietnamese"}]
            ],
            "one_time_keyboard": True,
            "resize_keyboard": True
        }
    }
    response = requests.post(url, json=payload)
    print(f"Sent language selection to {chat_id}")  # Лог отправки выбора языка
    return response

def send_reels_video(chat_id, reels_url):
    try:
        loader = instaloader.Instaloader()
        shortcode = reels_url.split("/")[-2]
        print(f"Parsed shortcode: {shortcode}")  # Лог shortocode

        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        video_url = post.video_url
        print(f"Video URL: {video_url}")  # Лог URL видео

        if video_url:
            response = requests.get(video_url, stream=True)
            response.raise_for_status()

            video_content = response.content
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo"
            files = {"video": ("reels_video.mp4", video_content)}
            data = {"chat_id": chat_id, "supports_streaming": True}
            requests.post(url, data=data, files=files)
            return True
        else:
            print("Видео не найдено в посте.")
            return False
    except Exception as e:
        print(f"Error sending video: {e}")
        return False

if __name__ == '__main__':
    app.run(debug=True)
