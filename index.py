import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Приветствия на трех языках
WELCOME_MESSAGES = {
    "en": (
        "👋 Welcome! This bot helps you download Instagram Reels. "
        "You can send me a link directly or add me to a group, and I'll process links shared there.\n\n"
        "Commands:\n"
        "/start - Restart the bot\n"
        "/help - Get instructions"
    ),
    "ru": (
        "👋 Добро пожаловать! Этот бот поможет вам скачать рилсы из Instagram. "
        "Вы можете отправить мне ссылку напрямую или добавить меня в группу, и я обработаю ссылки, которые там будут отправлены.\n\n"
        "Команды:\n"
        "/start - Перезапустить бота\n"
        "/help - Получить инструкции"
    ),
    "vi": (
        "👋 Xin chào! Bot này sẽ giúp bạn tải Reels từ Instagram. "
        "Bạn có thể gửi liên kết trực tiếp hoặc thêm tôi vào nhóm, và tôi sẽ xử lý các liên kết được chia sẻ ở đó.\n\n"
        "Lệnh:\n"
        "/start - Khởi động lại bot\n"
        "/help - Nhận hướng dẫn"
    ),
}

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

    # Если сообщение из группы, добавить проверку, содержит ли оно ссылку
    if "chat" in message and message["chat"].get("type") in ["group", "supergroup"]:
        if "http" in text:
            download_reel(chat_id, text)
        return  # Игнорируем остальные команды в группах

    # Обработка личных сообщений и команд
    if text == "/start":
        send_message(chat_id, WELCOME_MESSAGES["en"])
    elif text == "/help":
        send_message(chat_id, WELCOME_MESSAGES["en"])  # Default to English
    elif text.startswith("http"):
        download_reel(chat_id, text)
    else:
        send_message(chat_id, "❓ Sorry, I don't understand. Please send a valid Instagram Reel link or use /help.")


def send_message(chat_id, text):
    """Отправка сообщения в Telegram."""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)


def download_reel(chat_id, url):
    """Обработка ссылки на рилс и отправка результата."""
    try:
        # Здесь должна быть ваша логика для скачивания рилсов
        # Для примера отправим сообщение о получении ссылки
        send_message(chat_id, f"🔗 Received link: {url}\n⏳ Processing...")
        # После обработки вы можете отправить ссылку на скачивание
        send_message(chat_id, "✅ Reel downloaded successfully! (Example link)")
    except Exception as e:
        send_message(chat_id, f"❌ Failed to process the link. Error: {e}")


@app.route('/')
def index():
    return "Server is running", 200


if __name__ == "__main__":
    app.run(debug=True)
