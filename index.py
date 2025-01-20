from flask import Flask, request, jsonify
import os
import logging
import requests
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

app = Flask(__name__)

# Переменные окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0)

logging.basicConfig(level=logging.INFO)

# Обработчики команд
def start(update: Update, context):
    update.message.reply_text("Привет! Я бот Telegram.")

def echo(update: Update, context):
    update.message.reply_text(f"Вы сказали: {update.message.text}")

# Добавление обработчиков
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

# Маршрут для Webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    if request.method == "POST":
        data = request.get_json(force=True)
        if data:
            logging.info(f"Update received: {data}")
            update = Update.de_json(data, bot)
            dispatcher.process_update(update)
        return jsonify({"status": "ok"}), 200
    return jsonify({"error": "Method not allowed"}), 405

# Корневой маршрут
@app.route("/")
def index():
    return "Server is running", 200

# Установка Webhook
def set_webhook():
    if TELEGRAM_TOKEN and WEBHOOK_URL:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={WEBHOOK_URL}/webhook"
        response = requests.post(url)
        if response.status_code == 200:
            logging.info(f"Webhook set successfully: {response.json()}")
        else:
            logging.error(f"Failed to set webhook: {response.text}")

if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=5000)
