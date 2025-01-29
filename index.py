from flask import Flask, request, jsonify
import os
import requests
import instaloader
import io
import subprocess

app = Flask(__name__)

WEBHOOK_URL = "https://testbot-clean.vercel.app/webhook"
TELEGRAM_TOKEN = "7648873218:AAGs6RZlBrVjr1TkmMjO-jvoFT8PxXvSjyM"
MAX_VIDEO_SIZE_MB = 50  # Максимальный размер для sendVideo (в МБ)
MAX_DOC_SIZE_MB = 2000  # Максимальный размер для sendDocument (2 ГБ)
TIMEOUT = 600  # Увеличенный таймаут для загрузки больших файлов

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
            processing_message_id = send_message(chat_id, "⏳ Обрабатываю ссылку, подождите...")
            success = send_reels_video(chat_id, text.strip(), user_name)
            if success:
                delete_message(chat_id, processing_message_id)
                delete_message(chat_id, message_id)
            else:
                send_message(chat_id, "❌ Не удалось скачать видео. Проверьте ссылку.")
            return jsonify({"message": "Reels link processed"}), 200

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
            response = requests.get(video_url, stream=True)
            response.raise_for_status()
            video_content = response.content

            video_size_mb = len(video_content) / (1024 * 1024)  # Размер в МБ
            print(f"Видео загружено, размер: {video_size_mb:.2f} MB")

            if video_size_mb > MAX_DOC_SIZE_MB:
                send_message(chat_id, "❌ Видео слишком большое (более 2 ГБ). Telegram не поддерживает такие файлы.")
                return False
            elif video_size_mb > MAX_VIDEO_SIZE_MB:
                print("Видео слишком большое, загружаем на временный сервер.")
                temp_url = upload_to_temp_server(video_content)
                if temp_url:
                    send_document_via_url(chat_id, temp_url, user_name)
                else:
                    send_message(chat_id, "❌ Ошибка при загрузке видео.")
            else:
                width, height, duration = get_video_metadata(video_content)
                send_video_as_stream(chat_id, video_content, user_name, width, height, duration)
            return True
        else:
            print("Видео не найдено в посте.")
            return False
    except Exception as e:
        print(f"Ошибка при загрузке видео: {e}")
        return False

def upload_to_temp_server(video_content):
    temp_server_url = "https://transfer.sh/original_video.mp4"
    try:
        response = requests.put(temp_server_url, data=video_content)
        if response.status_code == 200:
            return response.text.strip()
        else:
            print(f"Ошибка загрузки на сервер: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        print(f"Ошибка загрузки видео на сервер: {e}")
        return None

def send_document_via_url(chat_id, file_url, user_name):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    data = {
        "chat_id": chat_id,
        "document": file_url,
        "caption": f"📁 Видео от @{user_name} (отправлено как файл, чтобы избежать искажения)",
        "allow_sending_without_reply": True
    }
    response = requests.post(url, json=data, timeout=TIMEOUT)
    if response.status_code != 200:
        print(f"Ошибка при отправке документа через URL: {response.status_code}, {response.text}")

if __name__ == '__main__':
    app.run(debug=True)
