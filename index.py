from flask import Flask, request, jsonify
import os
import requests
from bs4 import BeautifulSoup  # Парсинг HTML для извлечения ссылки на видео

app = Flask(__name__)

# URL вебхука
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Invalid request"}), 400

    message = data["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    if "instagram.com/reel/" in text:
        video_url = download_reel(text)
        if video_url:
            send_video(chat_id, video_url)
            return jsonify({"message": "Reel sent successfully"}), 200
        else:
            send_message(chat_id, "❌ Unable to download the video. Please try again later.")
            return jsonify({"error": "Failed to download Reel"}), 500

    send_message(chat_id, "❌ Please send a valid Instagram Reel link.")
    return jsonify({"message": "Not a valid Reel URL"}), 200

@app.route('/')
def index():
    return "Server is running", 200

@app.before_first_request
def setup_webhook():
    token = os.getenv("TELEGRAM_TOKEN")
    if token and WEBHOOK_URL:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/setWebhook",
            json={"url": f"{WEBHOOK_URL}/webhook"}
        )
        print(f"Webhook setup response: {response.json()}")

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
    token = os.getenv("TELEGRAM_TOKEN")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

def send_video(chat_id, video_url):
    """Отправляет видео в Telegram"""
    token = os.getenv("TELEGRAM_TOKEN")
    url = f"https://api.telegram.org/bot{token}/sendVideo"
    payload = {"chat_id": chat_id, "video": video_url}
    requests.post(url, json=payload)

if __name__ == '__main__':
    app.run(debug=True)
