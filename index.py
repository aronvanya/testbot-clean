from flask import Flask, request, jsonify
import os
import requests
import instaloader
import yt_dlp

app = Flask(__name__)

WEBHOOK_URL = "https://testbot-clean.vercel.app/webhook"
TELEGRAM_TOKEN = "7648873218:AAGs6RZlBrVjr1TkmMjO-jvoFT8PxXvSjyM"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data and "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        message_id = message["message_id"]
        text = message.get("text", "")

        # Получаем имя пользователя
        user_name = message["from"].get("username", "пользователь")

        # Обработка команды /start
        if text == "/start":
            send_message(chat_id, (
                "👋 *Привет!*\n\n"
                "Этот бот поможет вам скачать видео из Instagram Reels и YouTube Shorts. 📹\n\n"
                "Просто отправьте ссылку на Reels или Shorts, и я сделаю всё за вас. ✅\n\n"
                "✨ *Бот также работает в группах!* ✨\n"
                "Добавьте его в группу и дайте ему права администратора для функционирования. 🚀\n\n"
                "После добавления отправьте ссылку, и бот скачает видео для вас. 🎬"
            ), parse_mode="Markdown")
            return jsonify({"message": "Start command processed"}), 200

        # Обработка ссылки на Reels
        if 'instagram.com/reel/' in text:
            processing_message_id = send_message(chat_id, "⏳ Обрабатываю ссылку, подождите...")

            success = send_reels_video(chat_id, text.strip(), user_name)
            if success:
                delete_message(chat_id, processing_message_id)
                delete_message(chat_id, message_id)
            else:
                send_message(chat_id, "❌ Не удалось скачать видео. Проверьте ссылку.")
            return jsonify({"message": "Reels link processed"}), 200

        # Обработка ссылки на Shorts
        if 'youtube.com/shorts/' in text or 'youtu.be/' in text:
            processing_message_id = send_message(chat_id, "⏳ Обрабатываю ссылку, подождите...")

            success = send_shorts_video(chat_id, text.strip(), user_name)
            if success:
                delete_message(chat_id, processing_message_id)
                delete_message(chat_id, message_id)
            else:
                send_message(chat_id, "❌ Не удалось скачать видео. Проверьте ссылку.")
            return jsonify({"message": "Shorts link processed"}), 200

        # Игнорируем все остальные сообщения
        return jsonify({"message": "Message ignored"}), 200

    return jsonify({"message": "Webhook received!"}), 200

@app.route('/')
def index():
    return "Server is running", 200

def send_message(chat_id, text, parse_mode=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    response = requests.post(url, json=payload)
    return response.json().get("result", {}).get("message_id")

def delete_message(chat_id, message_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteMessage"
    payload = {"chat_id": chat_id, "message_id": message_id}
    requests.post(url, json=payload)

def send_reels_video(chat_id, reels_url, user_name):
    try:
        loader = instaloader.Instaloader()
        shortcode = reels_url.split("/")[-2]
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        video_url = post.video_url

        if video_url:
            video_content = requests.get(video_url).content
            send_video_as_stream(chat_id, video_content, user_name)
            return True
    except Exception as e:
        print(f"Error sending Reels video: {e}")
    return False

def send_shorts_video(chat_id, shorts_url, user_name):
    try:
        ydl_opts = {
            'quiet': True,
            'format': 'mp4',
            'outtmpl': '/tmp/%(id)s.%(ext)s',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(shorts_url, download=False)
            video_url = info.get('url')

        if video_url:
            video_content = requests.get(video_url).content
            send_video_as_stream(chat_id, video_content, user_name)
            return True
    except Exception as e:
        print(f"Error sending Shorts video: {e}")
    return False

def send_video_as_stream(chat_id, video_content, user_name):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo"
    files = {"video": ("video.mp4", video_content)}
    data = {
        "chat_id": chat_id,
        "caption": f"📹 Видео от @{user_name} 🚀",
        "supports_streaming": True
    }
    requests.post(url, data=data, files=files)

if __name__ == '__main__':
    app.run(debug=True)
