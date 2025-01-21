from flask import Flask, request, jsonify
import os
import requests
import instaloader

app = Flask(__name__)

WEBHOOK_URL = "https://testbot-clean.vercel.app/webhook"
TELEGRAM_TOKEN = "7648873218:AAGs6RZlBrVjr1TkmMjO-jvoFT8PxXvSjyM"

# Сообщения на разных языках
messages = {
    "ru": {
        "start": "Привет! Этот бот поможет вам скачать видео из Instagram Reels. Просто отправьте ссылку на Reels.",
        "instruction": "Инструкция: отправьте ссылку на Reels, и вы получите видео в ответ. Чтобы сменить язык, используйте /start ru, /start en или /start vi.",
        "processing": "Обрабатываю ссылку, подождите...",
        "error": "Не удалось скачать видео. Проверьте ссылку.",
        "invalid": "Отправьте корректную ссылку на Reels."
    },
    "en": {
        "start": "Hello! This bot will help you download videos from Instagram Reels. Just send a link.",
        "instruction": "Instruction: Send a Reels link, and you'll get the video in return. Use /start ru, /start en, or /start vi to change the language.",
        "processing": "Processing your link, please wait...",
        "error": "Failed to download the video. Please check the link.",
        "invalid": "Please send a valid Reels link."
    },
    "vi": {
        "start": "Xin chào! Bot này sẽ giúp bạn tải video từ Instagram Reels. Chỉ cần gửi liên kết.",
        "instruction": "Hướng dẫn: Gửi liên kết Reels và bạn sẽ nhận được video. Sử dụng /start ru, /start en hoặc /start vi để thay đổi ngôn ngữ.",
        "processing": "Đang xử lý liên kết của bạn, vui lòng đợi...",
        "error": "Không tải được video. Vui lòng kiểm tra liên kết.",
        "invalid": "Vui lòng gửi liên kết Reels hợp lệ."
    }
}

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data and "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "").strip().lower()

        # Обработка команды /start
        if text.startswith("/start"):
            lang = text.split(" ")[1] if " " in text else "ru"
            lang = lang if lang in messages else "ru"  # Если язык не распознан, используем русский
            send_message(chat_id, messages[lang]["start"])
            send_message(chat_id, messages[lang]["instruction"])
            return jsonify({"message": "Start command processed"}), 200

        # Обработка ссылки на Reels
        if 'instagram.com/reel/' in text:
            send_message(chat_id, messages["ru"]["processing"])  # По умолчанию русский
            success = send_reels_video(chat_id, text.strip())
            if not success:
                send_message(chat_id, messages["ru"]["error"])
        else:
            send_message(chat_id, messages["ru"]["invalid"])

    return jsonify({"message": "Webhook received!"}), 200

@app.route('/')
def index():
    return "Server is running", 200

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
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
