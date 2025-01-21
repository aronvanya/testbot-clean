from flask import Flask, request, jsonify
import os
import requests
import instaloader

app = Flask(__name__)

WEBHOOK_URL = "https://testbot-clean.vercel.app/webhook"
TELEGRAM_TOKEN = "7648873218:AAGs6RZlBrVjr1TkmMjO-jvoFT8PxXvSjyM"

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

        # Обработка ссылки на Reels
        if 'instagram.com/reel/' in text:
            send_message(chat_id, "Обрабатываю ссылку, подождите...")
            success = send_reels_video(chat_id, text.strip())
            if not success:
                send_message(chat_id, "Не удалось скачать видео. Проверьте ссылку.")
        else:
            send_message(chat_id, "Отправьте корректную ссылку на Reels.")

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
