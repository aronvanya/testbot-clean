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
    "welcome": {
        "ru": "Добро пожаловать! Этот бот поможет вам скачать видео из Instagram Reels. Просто отправьте ссылку, и я всё сделаю за вас!",
        "en": "Welcome! This bot will help you download videos from Instagram Reels. Just send a link, and I'll handle the rest!",
        "vi": "Chào mừng! Bot này sẽ giúp bạn tải video từ Instagram Reels. Chỉ cần gửi liên kết, tôi sẽ lo phần còn lại!"
    },
    "instruction": {
        "ru": "Инструкция: отправьте ссылку на Reels, и вы получите видео в ответ. Бот также работает в группах: добавьте его в группу, и отправьте ссылку на Reels.",
        "en": "Instruction: Send a Reels link, and you'll receive the video in return. The bot also works in groups: add it to a group and send a Reels link.",
        "vi": "Hướng dẫn: Gửi liên kết Reels, và bạn sẽ nhận được video. Bot cũng hoạt động trong các nhóm: thêm nó vào nhóm và gửi liên kết Reels."
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
            if text == "русский":
                user_languages[chat_id] = "ru"
            elif text == "english":
                user_languages[chat_id] = "en"
            elif text == "vietnamese":
                user_languages[chat_id] = "vi"

            lang = user_languages[chat_id]
            send_message(chat_id, messages["language_set"][lang])
            send_message(chat_id, messages["welcome"][lang])
            send_message(chat_id, messages["instruction"][lang])
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
            send_message(chat_id, messages["instruction"][lang])

    return jsonify({"message": "Webhook received!"}), 200

@app.route('/')
def index():
    return "Server is running", 200

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

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
    requests.post(url, json=payload)

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
