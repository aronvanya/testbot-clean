import os
from flask import Flask, request, jsonify
import requests
import re
import tempfile
from pathlib import Path

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Приветствия и инструкции на трех языках
MESSAGES = {
    "en": {
        "welcome": "👋 Welcome! This bot helps you download Instagram Reels. Please choose your language:",
        "instruction": (
            "You can send me a link directly or add me to a group, and I'll process links shared there.\n\n"
            "Commands:\n"
            "/start - Restart the bot\n"
            "/help - Get instructions"
        ),
        "language_updated": "✅ Language updated to English.",
        "invalid_link": "❌ This is not a valid Instagram Reel link. Please send a correct link.",
        "processing": "⏳ Processing your request...",
        "success": "✅ Reel downloaded successfully!",
        "error": "❌ Failed to download the Reel. Please try again later.",
    },
    "ru": {
        "welcome": "👋 Добро пожаловать! Этот бот поможет вам скачать рилсы из Instagram. Пожалуйста, выберите язык:",
        "instruction": (
            "Вы можете отправить мне ссылку напрямую или добавить меня в группу, и я обработаю ссылки, которые там будут отправлены.\n\n"
            "Команды:\n"
            "/start - Перезапустить бота\n"
            "/help - Получить инструкции"
        ),
        "language_updated": "✅ Язык обновлен на русский.",
        "invalid_link": "❌ Это не ссылка на рилс из Instagram. Отправьте корректную ссылку.",
        "processing": "⏳ Обработка вашего запроса...",
        "success": "✅ Рилс успешно скачан!",
        "error": "❌ Не удалось скачать рилс. Попробуйте позже.",
    },
    "vi": {
        "welcome": "👋 Xin chào! Bot này sẽ giúp bạn tải Reels từ Instagram. Vui lòng chọn ngôn ngữ:",
        "instruction": (
            "Bạn có thể gửi liên kết trực tiếp hoặc thêm tôi vào nhóm, và tôi sẽ xử lý các liên kết được chia sẻ ở đó.\n\n"
            "Lệnh:\n"
            "/start - Khởi động lại bot\n"
            "/help - Nhận hướng dẫn"
        ),
        "language_updated": "✅ Ngôn ngữ đã được chuyển sang Tiếng Việt.",
        "invalid_link": "❌ Đây không phải là liên kết Instagram Reels hợp lệ. Vui lòng gửi liên kết chính xác.",
        "processing": "⏳ Đang xử lý yêu cầu của bạn...",
        "success": "✅ Tải xuống Reels thành công!",
        "error": "❌ Không tải được Reels. Hãy thử lại sau.",
    },
}

USER_LANGUAGES = {}  # Хранение выбранных языков для пользователей


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if not data:
        return jsonify({"message": "No data received"}), 400

    if "message" in data:
        handle_message(data["message"])

    return jsonify({"message": "OK"}), 200


def handle_message(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    # Проверка, выбрал ли пользователь язык
    lang = USER_LANGUAGES.get(chat_id, "en")  # Язык по умолчанию — английский

    if text == "/start":
        send_start_message(chat_id)
    elif text in ["English", "Русский", "Tiếng Việt"]:
        set_user_language(chat_id, text)
    elif text == "/help":
        send_message(chat_id, MESSAGES[lang]["instruction"])
    elif is_instagram_reel_link(text):
        download_and_send_reel(chat_id, text, lang)
    else:
        # Игнорируем невалидные сообщения
        send_message(chat_id, MESSAGES[lang]["invalid_link"])


def is_instagram_reel_link(text):
    """Проверка, является ли текст ссылкой на Instagram Reel."""
    pattern = r"(https?:\/\/(?:www\.)?instagram\.com\/reel\/[a-zA-Z0-9_-]+)"
    return re.match(pattern, text) is not None


def send_start_message(chat_id):
    """Отправка приветствия, инструкции и кнопки выбора языка."""
    lang = "en"  # Начальный язык по умолчанию
    keyboard = {
        "keyboard": [[{"text": "English"}], [{"text": "Русский"}], [{"text": "Tiếng Việt"}]],
        "one_time_keyboard": True,
        "resize_keyboard": True,
    }
    message = f"{MESSAGES[lang]['welcome']}\n\n{MESSAGES[lang]['instruction']}"
    send_message(chat_id, message, keyboard)


def set_user_language(chat_id, language):
    """Установка языка для пользователя."""
    if language == "English":
        USER_LANGUAGES[chat_id] = "en"
    elif language == "Русский":
        USER_LANGUAGES[chat_id] = "ru"
    elif language == "Tiếng Việt":
        USER_LANGUAGES[chat_id] = "vi"

    lang = USER_LANGUAGES[chat_id]
    message = f"{MESSAGES[lang]['language_updated']}\n\n{MESSAGES[lang]['instruction']}"
    send_message(chat_id, message)


def send_message(chat_id, text, reply_markup=None):
    """Отправка сообщения в Telegram."""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(url, json=payload)


def download_and_send_reel(chat_id, url, lang):
    """Скачивание и отправка рилса."""
    try:
        send_message(chat_id, MESSAGES[lang]["processing"])

        # Здесь используем сторонний сервис для скачивания видео
        response = requests.get(f"https://api.downloadgram.org/?url={url}", stream=True)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    temp_file.write(chunk)
            temp_file_path = temp_file.name

        # Отправка видео
        with open(temp_file_path, "rb") as video_file:
            requests.post(
                f"{TELEGRAM_API_URL}/sendVideo",
                data={"chat_id": chat_id},
                files={"video": video_file},
            )

        send_message(chat_id, MESSAGES[lang]["success"])

    except Exception as e:
        send_message(chat_id, f"{MESSAGES[lang]['error']}\n\nError: {e}")


@app.route('/')
def index():
    return "Server is running", 200


if __name__ == "__main__":
    app.run(debug=True)
