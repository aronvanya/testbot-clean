from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

# URL вебхука
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data:
        print(f"Received data: {data}")
        # Здесь можно обработать данные
    return jsonify({"message": "Webhook received!"}), 200

@app.route('/')
def index():
    return "Server is running", 200

# Настройка вебхука при запуске сервера
@app.before_first_request
def setup_webhook():
    token = os.getenv("TELEGRAM_TOKEN")
    if token and WEBHOOK_URL:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/setWebhook",
            json={"url": f"{WEBHOOK_URL}/webhook"}
        )
        print(f"Webhook setup response: {response.json()}")

if __name__ == '__main__':
    app.run(debug=True)
