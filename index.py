from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return "Server is running"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print(f"Received data: {data}")
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(debug=True)
