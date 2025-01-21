from flask import Flask, request, jsonify
import os
import requests
import instaloader
import io

app = Flask(__name__)

# URL вебхука
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

        if 'instagram.com/reel/' in text:
            processing_message = send_message(chat_id, "Обрабатываю ссылку, подождите...")
            success = send_reels_video(chat_id, text.strip())

            # Удаляем сообщение "Обрабатываю ссылку" и исходное сообщение с ссылкой
            delete_message(chat_id, processing_message)
            delete_message(chat_id, message_id)

            if not success:
                send_message(chat_id, "Не удалось скачать видео. Пожалуйста, проверьте ссылку.")
        else:
            send_message(chat_id, "Отправьте мне ссылку на Reels, и я помогу скачать видео.")

    return jsonify({"message": "Webhook received!"}), 200

@app.route('/')
def index():
    return "Server is running", 200

# Настройка вебхука при запуске сервера
@app.before_first_request
def setup_webhook():
    if TELEGRAM_TOKEN and WEBHOOK_URL:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
            json={"url": f"{WEBHOOK_URL}"}
        )
        print(f"Webhook setup response: {response.json()}")

# Функция для отправки текстового сообщения
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    response = requests.post(url, json=payload)
    return response.json().get("result", {}).get("message_id")

# Функция для удаления сообщения
def delete_message(chat_id, message_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteMessage"
    payload = {"chat_id": chat_id, "message_id": message_id}
    requests.post(url, json=payload)

# Функция для загрузки и отправки видео из Reels

def send_reels_video(chat_id, reels_url):
    try:
        loader = instaloader.Instaloader()
        # Парсим короткий код из ссылки
        shortcode = reels_url.split("/")[-2]
        post = instaloader.Post.from_shortcode(loader.context, shortcode)

        video_url = post.video_url
        if video_url:
            response = requests.get(video_url, stream=True)
            response.raise_for_status()

            video_content = response.content

            # Проверка параметров видео
            video_size_mb = len(video_content) / (1024 * 1024)
            if video_size_mb > 50 or video_size_mb < 10:
                send_message(chat_id, "⚠️ Telegram может изменить качество видео. Отправляю его как документ.")
                # Отправляем как документ
                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
                files = {"document": ("reels_video.mp4", video_content)}
                data = {
                    "chat_id": chat_id,
                    "caption": "Ваше видео из Instagram Reels 🎥 (исходное качество сохранено)",
                }
                response = requests.post(url, data=data, files=files)
            else:
                # Отправляем как видео
                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo"
                files = {"video": ("reels_video.mp4", video_content)}
                data = {
                    "chat_id": chat_id,
                    "supports_streaming": True,  # Включена поддержка потокового воспроизведения
                    "caption": "Ваше видео из Instagram Reels 🎥",
                    "parse_mode": "HTML"  # Опционально для форматирования текста
                }
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
