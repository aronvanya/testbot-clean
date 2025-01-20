from flask import Flask, request, jsonify
import os
import logging

from telegram import Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

app = Flask(__name__)

# Telegram Bot initialization
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, use_context=True)

# Logging setup
logging.basicConfig(level=logging.INFO)

# Handlers for the bot
def start(update, context):
    update.message.reply_text("Привет! Я бот Telegram.")

def echo(update, context):
    update.message.reply_text(f"Вы сказали: {update.message.text}")

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

@app.route("/webhook", methods=["POST"])
def webhook():
    if request.method == "POST":
        update = request.get_json()
        if update:
            logging.info(f"Received update: {update}")
            dispatcher.process_update(update)
        return jsonify({"status": "ok"})
    return jsonify({"error": "Method not allowed"}), 405

@app.route("/")
def index():
    return "Server is running", 200
