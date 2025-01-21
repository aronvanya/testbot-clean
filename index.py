from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

# URL вебхука
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data and "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")

        if 'instagram.com/reel/' in text:
            send_message(chat_id, "Обрабатываю ссылку, подождите...")
            video_file = download_reels_video(text.strip())

            if video_file:
                send_video(chat_id, video_file)
                os.remove(video_file)
            else:
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
            json={"url": f"{WEBHOOK_URL}/webhook"}
        )
        print(f"Webhook setup response: {response.json()}")

# Функция для отправки текстового сообщения
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

# Функция для отправки видео
def send_video(chat_id, video_path):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo"
    with open(video_path, 'rb') as video:
        files = {"video": video}
        data = {"chat_id": chat_id}
        requests.post(url, data=data, files=files)

# Функция для загрузки видео из Reels
def download_reels_video(reels_url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(reels_url, headers=headers)
        response.raise_for_status()

        # Вставьте здесь логику для извлечения прямой ссылки на видео (например, через парсинг HTML или API Instagram)
        # В примере предполагается, что у вас уже есть готовая функция extract_video_url
        video_url = extract_video_url(response.text)

        if video_url:
            video_response = requests.get(video_url, stream=True)
            video_response.raise_for_status()
            
            file_name = "reels_video.mp4"
            with open(file_name, "wb") as video_file:
                for chunk in video_response.iter_content(chunk_size=1024):
                    video_file.write(chunk)

            return file_name
        else:
            return None
    except Exception as e:
        print(f"Error downloading video: {e}")
        return None

# Заглушка функции для извлечения видео URL (замените своей реализацией)
def extract_video_url(page_content):
    # Парсинг HTML и поиск ссылки на видео
    # Верните прямую ссылку на видео
    return None

if __name__ == '__main__':
    app.run(debug=True)
