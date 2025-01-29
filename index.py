from flask import Flask, request, jsonify
import os
import requests
import instaloader
import subprocess
import tempfile

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

        user_name = message["from"].get("username", "пользователь")

        if text == "/start":
            send_message(chat_id, "👋 *Привет!*\n\nОтправь ссылку на Instagram Reels, и я загружу видео.", parse_mode="Markdown")
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

            file_id = send_video_as_stream(chat_id, video_content, user_name)
            if file_id and is_video_compressed(file_id, video_content):
                delete_message(chat_id, file_id)
                send_video_as_document(chat_id, video_content, user_name)

            return True
        else:
            print("Видео не найдено в посте.")
            return False
    except Exception as e:
        print(f"Error sending video: {e}")
        return False

def send_video_as_stream(chat_id, video_content, user_name):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo"
    files = {"video": ("reels_video.mp4", video_content, "video/mp4")}
    data = {
        "chat_id": chat_id,
        "caption": f"📹 Видео от @{user_name} 🚀",
        "supports_streaming": True
    }
    response = requests.post(url, data=data, files=files).json()
    return response.get("result", {}).get("video", {}).get("file_id")

def is_video_compressed(file_id, original_video_content):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile"
    params = {"file_id": file_id}
    response = requests.get(url, params=params).json()
    file_path = response.get("result", {}).get("file_path", "")

    if file_path:
        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        video_response = requests.get(download_url, stream=True)
        compressed_video_content = video_response.content

        original_resolution = get_video_resolution(original_video_content)
        compressed_resolution = get_video_resolution(compressed_video_content)

        return compressed_resolution != original_resolution
    return False

def get_video_resolution(video_content):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
        temp_video.write(video_content)
        temp_video_path = temp_video.name
    
    command = [
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", temp_video_path
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        os.remove(temp_video_path)
        width, height = map(int, result.stdout.strip().split(","))
        return (width, height)
    except:
        os.remove(temp_video_path)
        return None

def send_video_as_document(chat_id, video_content, user_name):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    files = {"document": ("video_uncompressed.mp4", video_content, "video/mp4")}
    caption = f"📁 Видео от @{user_name} (отправлено как файл, чтобы избежать искажения)"
    data = {"chat_id": chat_id, "caption": caption}
    requests.post(url, data=data, files=files)

if __name__ == '__main__':
    app.run(debug=True)
