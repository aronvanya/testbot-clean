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
        "ru": "Не удалось скачать видео. Проверьте ссылку.",
        "en": "Failed to download the video. Please check the link.",
        "vi": "Không tải được video. Vui lòng kiểm tra liên kết."
    },
    "invalid": {
        "ru": "Отправьте корректную ссылку на Reels.",
        "en": "Please send a valid Reels link.",
        "vi": "Vui lòng gửi liên kết Reels hợp lệ."
    }
}

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data and "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "").strip().lower()

        # Команда /start
        if text == "/start":
            send_language_selection(chat_id)
            return jsonify({"message": "Start command processed"}), 200

        # Выбор языка
        if text in ["русский", "english", "vietnamese"]:
            lang = "ru" if text == "русский" else "en" if text == "english" else "vi"
            user_languages[chat_id] = lang
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
            lang = user_languages[chat_id]
            send_message(chat_id, messages["invalid"][lang])

    return jsonify({"message": "Webhook received!"}), 200

@app.route('/')
def index():
    return "Server is running", 200

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    response = requests.post(url, json=payload)
    print(f"Message sent to {chat_id}: {text}")
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
    print(f"Language selection sent to {chat_id}")
    return response

def send_reels_video(chat_id, reels_url):
    try:
        loader = instaloader.Instaloader()

        # Парсим короткий код из ссылки
        shortcode = reels_url.split("/")[-2]
        post = instaloader.Post.from_shortcode(loader.context, shortcode)

        video_url = post.video_url
        if video_url:
            response = requests.get(video_url, stream=True)
            response.raise_for_status()

            video_content = response.content

            # Отправляем видео
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo"
            files = {"video": ("reels_video.mp4", video_content)}
            data = {"chat_id": chat_id, "supports_streaming": True}
            response = requests.post(url, data=data, files=files)

            if response.status_code != 200:
                print(f"Telegram API error: {response.json()}")
                return False

            return True
        else:
            print("Видео не найдено в посте.")
            return False
    except Exception as e:
        print(f"Error sending video: {e}")
        return False

if __name__ == '__main__':
    app.run(debug=True)
