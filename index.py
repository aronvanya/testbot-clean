from flask import Flask, request, jsonify
import os
import logging
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

# Flask app
app = Flask(__name__)

# Telegram Bot initialization
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0)

# Logging setup
logging.basicConfig(level=logging.INFO)

# Bot handlers
def start(update: Update, context):
    update.message.reply_text("Привет! Я бот Telegram.")

def echo(update: Update, context):
    update.message.reply_text(f"Вы сказали: {update.message.text}")

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

# Webhook endpoint
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

# Root endpoint
@app.route("/")
def index():
    return "Server is running", 200
