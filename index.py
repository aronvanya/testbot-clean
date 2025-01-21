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
        "ru": "Привет! Этот бот поможет вам скачать видео из Instagram Reels. Просто отправьте ссылку, и я сделаю всё за вас.",
        "en": "Hello! This bot will help you download videos from Instagram Reels. Just send a link, and I'll handle it for you.",
        "vi": "Xin chào! Bot này sẽ giúp bạn tải video từ Instagram Reels. Chỉ cần gửi liên kết và tôi sẽ xử lý nó."
    },
    "instruction": {
        "ru": "Инструкция: отправьте ссылку на Reels, и вы получите видео в ответ. Чтобы сменить язык, используйте кнопки ниже.",
        "en": "Instruction: Send a Reels link, and you'll get the video in return. Use the buttons below to change the language.",
        "vi": "Hướng dẫn: Gửi liên kết Reels và bạn sẽ nhận được video. Sử dụng các nút bên dưới để thay đổi ngôn ngữ."
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
    print(f"Received data: {data}")  # Лог для диагностики

    if data and "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "").strip().lower()

        # Команда /start
        if text == "/start":
            send_language_menu(chat_id)
            return jsonify({"message": "Start command processed"}), 200

        # Выбор языка
        if text in ["русский", "english", "vietnamese"]:
            lang = "ru" if text == "русский" else "en" if text == "english" else "vi"
            send_message(chat_id, messages["start"][lang])
            send_message(chat_id, messages["instruction"][lang])
            return jsonify({"message": "Language selected"}), 200

        # Обработка ссылки на Reels
        if 'instagram.com/reel/' in text:
            send_message(chat_id, messages["processing"]["ru"])  # По умолчанию русский
            success = send_reels_video(chat_id, text.strip())
            if not success:
                send_message(chat_id, messages["error"]["ru"])
        else:
            send_message(chat_id, messages["invalid"]["ru"])

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

def send_language_menu(chat_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "Choose your language / Выберите язык / Chọn ngôn ngữ:",
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
    print(f"Language menu sent to {chat_id}")
    return response

def send_reels_video(chat_id, reels_url):
    try:
        loader = instaloader.Instaloader()
        shortcode = reels_url.split("/")[-2]
        print(f"Parsed shortcode: {shortcode}")
        post = instaloader.Post.from_shortcode(loader.context, shortcode)

        video_url = post.video_url
        print(f"Video URL: {video_url}")

        if video_url:
            response = requests.get(video_url, stream=True)
            response.raise_for_status()

            video_content = response.content
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
