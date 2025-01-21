from flask import Flask, request, jsonify
from instaloader import Instaloader, Post
import os
import requests

app = Flask(__name__)
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()

    # Проверка, что запрос содержит сообщение с текстом
    if not data or "message" not in data:
        return jsonify({"error": "Invalid request"}), 400

    message = data["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    # Проверяем, содержит ли текст ссылку на Reels
    if "instagram.com/reel/" not in text:
        send_message(chat_id, "❌ This is not a valid Instagram Reel link.")
        return jsonify({"message": "Not a Reel URL"}), 200

    try:
        # Инициализация Instaloader
        loader = Instaloader()
        shortcode = text.split("/")[-2]
        post = Post.from_shortcode(loader.context, shortcode)

        # Загружаем Reel
        video_url = post.video_url
        if not video_url:
            raise ValueError("No video found in the Reel.")

        # Отправляем видео в Telegram
        send_video(chat_id, video_url)
        return jsonify({"message": "Reel downloaded and sent successfully!"}), 200

    except Exception as e:
        print(f"Ошибка загрузки: {e}")
        send_message(chat_id, "❌ Failed to download the Reel. Please try again later.")
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return "Server is running", 200

def send_message(chat_id, text):
    """Функция для отправки текстового сообщения в Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

def send_video(chat_id, video_url):
    """Функция для отправки видео в Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    payload = {"chat_id": chat_id, "video": video_url}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run()
