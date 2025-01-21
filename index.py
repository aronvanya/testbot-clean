from flask import Flask, request, jsonify
import os
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

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
        video_url = download_reel(text)
        if not video_url:
            raise ValueError("Failed to extract video URL.")

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
    """Скачивает видео из Instagram Reels через парсинг страницы"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
    }
    try:
        response = requests.get(instagram_url, headers=headers)
        response.raise_for_status()

        # Парсим HTML-страницу
        soup = BeautifulSoup(response.text, 'html.parser')

        # Ищем тег с ссылкой на видео
        video_tag = soup.find("meta", property="og:video")
        if video_tag and video_tag.get("content"):
            return video_tag["content"]

        raise ValueError("Видео не найдено на странице.")
    except Exception as e:
        print(f"Ошибка при парсинге: {e}")
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
