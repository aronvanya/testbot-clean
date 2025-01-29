from flask import Flask, request, jsonify
import os
import requests
import instaloader
import tempfile
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
                print("Видео слишком большое, отправляем как документ.")
                send_video_as_document(chat_id, video_content, user_name)
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

def get_video_metadata(video_content):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
        temp_video.write(video_content)
        temp_video_path = temp_video.name
    
    command = [
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,duration", "-of", "csv=p=0", temp_video_path
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        os.remove(temp_video_path)
        width, height, duration = map(float, result.stdout.strip().split(","))
        return int(width), int(height), int(duration)
    except:
        os.remove(temp_video_path)
        return 720, 1280, 10  # Значения по умолчанию (9:16 видео)

def send_video_as_stream(chat_id, video_content, user_name, width, height, duration):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo"
    files = {"video": ("fixed_video.mp4", video_content, "video/mp4")}
    data = {
        "chat_id": chat_id,
        "caption": f"📹 Видео от @{user_name} 🚀",
        "width": width,
        "height": height,
        "duration": duration,
        "supports_streaming": False
    }
    requests.post(url, data=data, files=files, timeout=TIMEOUT)

def send_video_as_document(chat_id, video_content, user_name):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    files = {"document": ("original_video.mp4", video_content, "video/mp4")}
    caption = f"📁 Видео от @{user_name} (отправлено как файл, чтобы избежать искажения)"
    data = {"chat_id": chat_id, "caption": caption}
    response = requests.post(url, data=data, files=files, timeout=TIMEOUT)
    if response.status_code == 413:
        send_message(chat_id, "❌ Файл слишком большой для отправки в Telegram.")
    elif response.status_code != 200:
        print(f"Ошибка при отправке документа: {response.status_code}")

if __name__ == '__main__':
    app.run(debug=True)
