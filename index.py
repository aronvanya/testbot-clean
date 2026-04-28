from flask import Flask, request, jsonify
import os
import requests
import re

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

REEL_PATTERN = r"(https?://(?:www\.)?(?:instagram\.com|instagr\.am)/reel/[^\s]+)"


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()

    if data and "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        message_id = message["message_id"]
        text = message.get("text", "")
        thread_id = message.get("message_thread_id")

        # 👇 получаем пользователя
        user = message.get("from", {})
        user_name = get_user_name(user)

        if text == "/start":
            send_message(chat_id, (
                "👋 Привет!\n\n"
                "Отправь ссылку на Instagram Reels — я дам ссылку для скачивания. 📥\n\n"
                "Работает и в группах 🚀"
            ), thread_id=thread_id)
            return jsonify({"message": "Start command processed"}), 200

        matches = re.findall(REEL_PATTERN, text)

        if matches:
            for link in matches:
                # пропускаем если уже kksav
                if "kksav" in link:
                    continue

                new_link = convert_to_kksave(link)

                # 👇 сообщение с ником
                text_to_send = f"Это видео прислал Осёл - {user_name}\n{new_link}"

                send_message(chat_id, text_to_send, thread_id=thread_id)

            # удаляем сообщение пользователя (если есть права)
            try:
                delete_message(chat_id, message_id)
            except:
                pass

            return jsonify({"message": "Reels link converted"}), 200

    return jsonify({"message": "Webhook received"}), 200


@app.route('/', methods=['GET'])
def home():
    return "Server is running", 200


# 👇 функция получения имени
def get_user_name(user):
    username = user.get("username")
    first_name = user.get("first_name", "")
    last_name = user.get("last_name", "")

    if username:
        return f"@{username}"

    full_name = f"{first_name} {last_name}".strip()
    return full_name if full_name else "кто-то"


def convert_to_kksave(url):
    return re.sub(r"instagram\.com", "kksav.com", url)


def send_message(chat_id, text, thread_id=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if thread_id:
        payload["message_thread_id"] = thread_id

    response = requests.post(url, json=payload)
    return response.json().get("result", {}).get("message_id")


def delete_message(chat_id, message_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteMessage"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id
    }
    requests.post(url, json=payload)
