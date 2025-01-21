from flask import Flask, request, jsonify
import os
import requests
import instaloader
import io
from collections import defaultdict

app = Flask(__name__)

# URL вебхука
WEBHOOK_URL = "https://testbot-clean.vercel.app/webhook"
TELEGRAM_TOKEN = "7648873218:AAGs6RZlBrVjr1TkmMjO-jvoFT8PxXvSjyM"

# Хранилище языковых настроек пользователей
user_languages = defaultdict(lambda: "ru")  # По умолчанию русский язык

# Сообщения на разных языках
messages = {
    "start": {
        "ru": "Привет! Выберите язык: Русский, Английский или Вьетнамский.",
        "en": "Hello! Please choose a language: Russian, English, or Vietnamese.",
        "vi": "Xin chào! Vui lòng chọn ngôn ngữ: Tiếng Nga, Tiếng Anh hoặc Tiếng Việt."
    },
    "language_set": {
        "ru": "Язык успешно установлен: Русский.",
        "en": "Language set to: English.",
        "vi": "Ngôn ngữ đã được chọn: Tiếng Việt."
    },
    "processing": {
        "ru": "Обрабатываю ссылку, подождите...",
        "en": "Processing your link, please wait...",
        "vi": "Đang xử lý liên kết của bạn, vui lòng đợi..."
    },
    "invalid_reels": {
        "ru": "Отправьте мне ссылку на Reels, и я помогу скачать видео.",
        "en": "Send me a Reels link, and I will help you download the video.",
        "vi": "Gửi cho tôi liên kết Reels, tôi sẽ giúp bạn tải video."
    },
    "error": {
        "ru": "Не удалось скачать видео. Пожалуйста, проверьте ссылку.",
        "en": "Failed to download the video. Please check the link.",
        "vi": "Không tải được video. Vui lòng kiểm tra liên kết."
    }
}

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data and "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        message_id = message["message_id"]
        text = message.get("text", "").strip().lower()

        # Команда /start
        if text == "/start":
            send_message(chat_id, messages["start"]["ru"])
            return jsonify({"message": "Start command processed"}), 200

        # Выбор языка
        if text in ["русский", "english", "vietnamese"]:
            if text == "русский":
                user_languages[chat_id] = "ru"
            elif text == "english":
                user_languages[chat_id] = "en"
            elif text == "vietnamese":
                user_languages[chat_id] = "vi"

            lang = user_languages[chat_id]
            send_message(chat_id, messages["language_set"][lang])
            return jsonify({"message": "Language set"}), 200

        # Обработка ссылки на Reels
        if 'instagram.com/reel/' in text:
            lang = user_languages[chat_id]
            processing_message = send_message(chat_id, messages["processing"][lang])
            success = send_reels_video(chat_id, text)

            # Удаляем сообщение "Обрабатываю ссылку" и исходное сообщение с ссылкой
            delete_message(chat_id, processing_message)
            delete_message(chat_id, message_id)

            if not success:
                send_message(chat_id, messages["error"][lang])
        else:
            lang = user_languages[chat_id]
            send_message(chat_id, messages["invalid_reels"][lang])

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

# Функция для проверки требований Telegram к видео
def is_valid_for_telegram(video_content):
    video_size_mb = len(video_content) / (1024 * 1024)
    # Проверяем размер файла
    if video_size_mb > 20:
        return False
    # Дополнительные проверки можно добавить, например, анализ метаданных
    return True

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

            # Проверяем, соответствует ли видео требованиям Telegram
            if is_valid_for_telegram(video_content):
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
                    print(f"Telegram API error when sending video: {response.json()}")
                    return False
            else:
                send_message(chat_id, "⚠️ Видео не соответствует требованиям Telegram. Отправляю как документ для сохранения качества.")
                # Отправляем как документ
                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
                files = {"document": ("reels_video.mp4", video_content)}
                data = {
                    "chat_id": chat_id,
                    "caption": "Ваше видео из Instagram Reels 🎥 (исходное качество сохранено)",
                }
                response = requests.post(url, data=data, files=files)
                if response.status_code != 200:
                    print(f"Telegram API error when sending document: {response.json()}")
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
