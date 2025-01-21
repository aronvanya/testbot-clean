from flask import Flask, request, jsonify
import os
import requests
import instaloader

app = Flask(__name__)

WEBHOOK_URL = "https://testbot-clean.vercel.app/webhook"
TELEGRAM_TOKEN = "7648873218:AAGs6RZlBrVjr1TkmMjO-jvoFT8PxXvSjyM"

# Сообщения на разных языках
messages = {
    "start": {
        "ru": "Привет! Этот бот поможет вам скачать видео из Instagram Reels. Просто отправьте ссылку на Reels.",
        "en": "Hello! This bot will help you download videos from Instagram Reels. Just send a link.",
        "vi": "Xin chào! Bot này sẽ giúp bạn tải video từ Instagram Reels. Chỉ cần gửi liên kết."
    },
    "instruction": {
        "ru": "Инструкция: отправьте ссылку на Reels, и вы получите видео в ответ. Вы можете выбрать язык с помощью кнопок ниже.",
        "en": "Instruction: Send a Reels link, and you'll get the video in return. You can change the language using the buttons below.",
        "vi": "Hướng dẫn: Gửi liên kết Reels và bạn sẽ nhận được video. Bạn có thể thay đổi ngôn ngữ bằng cách sử dụng các nút bên dưới."
    }
}

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data and "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "").strip().lower()

        # Команда /start: Приветствие с кнопками выбора языка
        if text == "/start":
            send_language_menu(chat_id)
            return jsonify({"message": "Start command processed"}), 200

        # Обработка выбора языка
        if text in ["русский", "english", "vietnamese"]:
            lang = "ru" if text == "русский" else "en" if text == "english" else "vi"
            send_message(chat_id, messages["start"][lang])
            send_message(chat_id, messages["instruction"][lang])
            return jsonify({"message": "Language selected"}), 200

        # Обработка ссылки на Reels
        if 'instagram.com/reel/' in text:
            send_message(chat_id, "Обрабатываю ссылку, подождите...")
            success = send_reels_video(chat_id, text.strip())
            if not success:
                send_message(chat_id, "Не удалось скачать видео. Проверьте ссылку.")
        else:
            send_message(chat_id, "Отправьте мне ссылку на Reels, и я помогу скачать видео.")

    return jsonify({"message": "Webhook received!"}), 200

@app.route('/')
def index():
    return "Server is running", 200

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

def send_language_menu(chat_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "Выберите язык / Choose a language / Chọn ngôn ngữ:",
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
