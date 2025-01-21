import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Приветствия на трех языках
WELCOME_MESSAGES = {
    "en": "👋 Welcome! This bot helps you download Instagram Reels. Please choose your language:",
    "ru": "👋 Добро пожаловать! Этот бот поможет вам скачать рилсы из Instagram. Пожалуйста, выберите язык:",
    "vi": "👋 Xin chào! Bot này sẽ giúp bạn tải Reels từ Instagram. Vui lòng chọn ngôn ngữ:"
}

INSTRUCTIONS = {
    "en": (
        "You can send me a link directly or add me to a group, and I'll process links shared there.\n\n"
        "Commands:\n"
        "/start - Restart the bot\n"
        "/help - Get instructions"
    ),
    "ru": (
        "Вы можете отправить мне ссылку напрямую или добавить меня в группу, и я обработаю ссылки, которые там будут отправлены.\n\n"
        "Команды:\n"
        "/start - Перезапустить бота\n"
        "/help - Получить инструкции"
    ),
    "vi": (
        "Bạn có thể gửi liên kết trực tiếp hoặc thêm tôi vào nhóm, và tôi sẽ xử lý các liên kết được chia sẻ ở đó.\n\n"
        "Lệnh:\n"
        "/start - Khởi động lại bot\n"
        "/help - Nhận hướng dẫn"
    ),
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
    if chat_id in USER_LANGUAGES:
        lang = USER_LANGUAGES[chat_id]
    else:
        lang = "en"  # Язык по умолчанию

    if text == "/start":
        send_language_selection(chat_id)
    elif text in ["English", "Русский", "Tiếng Việt"]:
        set_user_language(chat_id, text)
    elif text == "/help":
        send_message(chat_id, INSTRUCTIONS[lang])
    elif text.startswith("http"):
        download_reel(chat_id, text, lang)
    else:
        send_message(chat_id, "❓ Sorry, I don't understand. Please send a valid Instagram Reel link or use /help.")


def send_language_selection(chat_id):
    """Отправка кнопок для выбора языка."""
    keyboard = {
        "keyboard": [[{"text": "English"}], [{"text": "Русский"}], [{"text": "Tiếng Việt"}]],
        "one_time_keyboard": True,
        "resize_keyboard": True,
    }
    send_message(chat_id, WELCOME_MESSAGES["en"], keyboard)


def set_user_language(chat_id, language):
    """Установка языка для пользователя."""
    if language == "English":
        USER_LANGUAGES[chat_id] = "en"
    elif language == "Русский":
        USER_LANGUAGES[chat_id] = "ru"
    elif language == "Tiếng Việt":
        USER_LANGUAGES[chat_id] = "vi"

    lang = USER_LANGUAGES[chat_id]
    send_message(chat_id, INSTRUCTIONS[lang])


def send_message(chat_id, text, reply_markup=None):
    """Отправка сообщения в Telegram."""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(url, json=payload)


def download_reel(chat_id, url, lang):
    """Обработка ссылки на рилс и отправка результата."""
    try:
        send_message(chat_id, f"🔗 {url}\n⏳ {INSTRUCTIONS[lang].splitlines()[0]}")  # Сообщение на выбранном языке
        send_message(chat_id, "✅ Reel downloaded successfully! (Example link)")
    except Exception as e:
        send_message(chat_id, f"❌ Failed to process the link. Error: {e}")


@app.route('/')
def index():
    return "Server is running", 200


if __name__ == "__main__":
    app.run(debug=True)
