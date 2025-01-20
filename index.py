from flask import Flask, request, jsonify

app = Flask(__name__)
WEBHOOK_URL = "https://testbot-clean.vercel.app/webhook"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data:
        # Обработка полученных данных
        print(f"Received data: {data}")
    return jsonify({"message": "Webhook received!"}), 200

@app.route('/')
def index():
    return "Server is running", 200
