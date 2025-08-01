from flask import Flask, request, jsonify
import os
import requests
import instaloader
import io
import time

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
MAX_VIDEO_SIZE_MB = 50
MAX_DOC_SIZE_MB = 2000
TIMEOUT = 600

active_downloads = set()

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data and "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        message_id = message["message_id"]
        text = message.get("text", "")
        user_name = message["from"].get("username", "пользователь")

        if text == "/start":
            send_message(chat_id, (
                "👋 *Привет!*\n\n"
                "Этот бот поможет вам скачать видео из Instagram Reels. 📹\n\n"
                "Просто отправьте ссылку на Reels, и я сделаю всё за вас. ✅\n\n"
                "✨ *Бот также работает в группах!* ✨\n"
                "Добавьте его в группу и дайте ему права администратора для функционирования. 🚀\n\n"
                "После добавления отправьте ссылку на Reels, и бот скачает видео для вас. 🎬"
            ), parse_mode="Markdown")
            return jsonify({"message": "Start command processed"}), 200

        if 'instagram.com/reel/' in text:
            if text in active_downloads:
                print(f"⚠️ Запрос уже выполняется: {text}")
                return jsonify({"message": "Duplicate request ignored"}), 200
            
            active_downloads.add(text)
            processing_message_id = send_message(chat_id, "⏳ Обрабатываю ссылку, подождите...")
            success = send_reels_video(chat_id, text.strip(), user_name)
            active_downloads.remove(text)
            
            if success:
                delete_message(chat_id, processing_message_id)
                delete_message(chat_id, message_id)
            else:
                send_message(chat_id, "❌ Не удалось скачать видео. Проверьте ссылку.")
            return jsonify({"message": "Reels link processed"}), 200

    return jsonify({"message": "Webhook received"}), 200

@app.route('/', methods=['GET'])
def home():
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
            response = requests.get(video_url, stream=True, timeout=TIMEOUT)
            response.raise_for_status()
            video_content = response.content

            video_size_mb = len(video_content) / (1024 * 1024)
            print(f"Видео загружено, размер: {video_size_mb:.2f} MB")

            if video_size_mb > MAX_DOC_SIZE_MB:
                send_message(chat_id, "❌ Видео слишком большое (более 2 ГБ). Telegram не поддерживает такие файлы.")
                return False
            elif video_size_mb > MAX_VIDEO_SIZE_MB:
                send_video_as_document(chat_id, video_content, user_name)
            else:
                send_video_as_stream(chat_id, video_content, user_name)
            return True
        else:
            print("Видео не найдено.")
            return False
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

def send_video_as_stream(chat_id, video_content, user_name):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo"
    files = {"video": ("reels.mp4", video_content, "video/mp4")}
    data = {
        "chat_id": chat_id,
        "caption": f"📹 Видео от @{user_name}",
        "supports_streaming": True
    }
    r = requests.post(url, files=files, data=data, timeout=TIMEOUT)
    if r.status_code != 200:
        print("Ошибка отправки, пробую как документ.")
        send_video_as_document(chat_id, video_content, user_name)

def send_video_as_document(chat_id, video_content, user_name):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    buffer = io.BytesIO(video_content)
    buffer.name = "reels.mp4"
    files = {"document": (buffer.name, buffer, "video/mp4")}
    data = {
        "chat_id": chat_id,
        "caption": f"📁 Видео от @{user_name}"
    }
    requests.post(url, files=files, data=data, timeout=TIMEOUT)
