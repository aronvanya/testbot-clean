from flask import Flask, request, jsonify
import os
import requests
import yt_dlp

app = Flask(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
COOKIES_FILE = "cookies.txt"  # Добавьте файл куков, если он был использован в прошлом боте.

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()

    if not data or "message" not in data:
        return jsonify({"error": "Invalid request"}), 400

    message = data["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    if "instagram.com/reel/" not in text:
        send_message(chat_id, "❌ This is not a valid Instagram Reel link.")
        return jsonify({"message": "Not a Reel URL"}), 200

    try:
        # Скачиваем видео
        video_url = download_reel(text)
        if not video_url:
            raise ValueError("Failed to extract video URL.")

        # Отправляем видео
        send_video(chat_id, video_url)
        return jsonify({"message": "Reel downloaded and sent successfully!"}), 200

    except Exception as e:
        print(f"Error: {e}")
        send_message(chat_id, "❌ Failed to download the Reel. Please try again later.")
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return "Server is running", 200

def download_reel(instagram_url):
    """Скачивает видео из Instagram Reels"""
    ydl_opts = {
        'quiet': True,
        'format': 'mp4',
        'outtmpl': '/tmp/%(id)s.%(ext)s',
    }

    # Если используется файл куков, добавляем его
    if os.path.exists(COOKIES_FILE):
        ydl_opts['cookiefile'] = COOKIES_FILE

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(instagram_url, download=False)
            return info.get('url', None)
    except Exception as e:
        print(f"Ошибка в yt_dlp: {e}")
        return None

def send_message(chat_id, text):
    """Отправляет текстовое сообщение в Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

def send_video(chat_id, video_url):
    """Отправляет видео в Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    payload = {"chat_id": chat_id, "video": video_url}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run()
