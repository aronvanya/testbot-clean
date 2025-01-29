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

            processed_video_content = fix_video_metadata(video_content)
            send_video_as_stream(chat_id, processed_video_content, user_name)
            return True
        else:
            print("Видео не найдено в посте.")
            return False
    except Exception as e:
        print(f"Error sending video: {e}")
        return False

def fix_video_metadata(video_content):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_input:
        temp_input.write(video_content)
        temp_input_path = temp_input.name
    
    temp_output_path = temp_input_path.replace(".mp4", "_fixed.mp4")
    
    command = [
        "ffmpeg", "-i", temp_input_path,
        "-c:v", "libx264", "-c:a", "aac", "-strict", "experimental",
        "-movflags", "+faststart",  # Перемещение "moov atom" в начало файла
        "-preset", "fast", "-crf", "23",  # Оптимальный баланс качества
        "-y", temp_output_path
    ]
    
    subprocess.run(command, check=True)
    os.remove(temp_input_path)
    
    with open(temp_output_path, "rb") as f:
        fixed_video_content = f.read()
    os.remove(temp_output_path)
    return fixed_video_content

def send_video_as_stream(chat_id, video_content, user_name):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo"
    files = {"video": ("reels_video.mp4", video_content, "video/mp4")}
    data = {
        "chat_id": chat_id,
        "caption": f"📹 Видео от @{user_name} 🚀"
    }
    requests.post(url, data=data, files=files)

if __name__ == '__main__':
    app.run(debug=True)
