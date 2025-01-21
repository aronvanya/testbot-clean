from flask import Flask, request, jsonify
import os
import requests
import instaloader
import cv2
import numpy as np
import io

app = Flask(__name__)

# URL вебхука
WEBHOOK_URL = "https://testbot-clean.vercel.app/webhook"
TELEGRAM_TOKEN = "7648873218:AAGs6RZlBrVjr1TkmMjO-jvoFT8PxXvSjyM"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data and "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        message_id = message["message_id"]
        text = message.get("text", "")

        if 'instagram.com/reel/' in text:
            processing_message = send_message(chat_id, "Обрабатываю ссылку, подождите...")
            success = send_reels_video(chat_id, text.strip())

            # Удаляем сообщение "Обрабатываю ссылку" и исходное сообщение с ссылкой
            delete_message(chat_id, processing_message)
            delete_message(chat_id, message_id)

            if not success:
                send_message(chat_id, "Не удалось скачать видео. Пожалуйста, проверьте ссылку.")
        else:
            send_message(chat_id, "Отправьте мне ссылку на Reels, и я помогу скачать видео.")

    return jsonify({"message": "Webhook received!"}), 200

@app.route('/')
def index():
    return "Server is running", 200

# Настройка вебхука при запуске сервера
@app.before_first_request
def setup_webhook():
    if TELEGRAM_TOKEN and WEBHOOK_URL:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
            json={"url": f"{WEBHOOK_URL}"}
        )
        print(f"Webhook setup response: {response.json()}")

# Функция для отправки текстового сообщения
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    response = requests.post(url, json=payload)
    return response.json().get("result", {}).get("message_id")

# Функция для удаления сообщения
def delete_message(chat_id, message_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteMessage"
    payload = {"chat_id": chat_id, "message_id": message_id}
    requests.post(url, json=payload)

# Обработка видео в памяти для соответствия требованиям Telegram
def process_video_in_memory(video_bytes):
    # Чтение видео из байтового потока
    video_array = np.frombuffer(video_bytes, np.uint8)
    input_stream = cv2.VideoCapture(cv2.imdecode(video_array, cv2.IMREAD_COLOR))

    # Проверяем открытие
    if not input_stream.isOpened():
        raise Exception("Не удалось открыть видео для обработки.")

    # Параметры нового видео
    frame_width = 1280
    frame_height = 720
    fps = int(input_stream.get(cv2.CAP_PROP_FPS))

    # Инициализируем выходной поток в память
    output_video = io.BytesIO()
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    output_stream = cv2.VideoWriter(
        "appsrc ! videoconvert ! x264enc tune=zerolatency bitrate=500 speed-preset=ultrafast ! mp4mux ! filesink location=/dev/stdout",
        fourcc, fps, (frame_width, frame_height)
    )

    while True:
        ret, frame = input_stream.read()
        if not ret:
            break

        # Изменяем размер кадра
        resized_frame = cv2.resize(frame, (frame_width, frame_height))
        output_stream.write(resized_frame)

    input_stream.release()
    output_stream.release()

    return output_video.getvalue()

# Функция для загрузки и отправки видео из Reels
def send_reels_video(chat_id, reels_url):
    try:
        loader = instaloader.Instaloader()
        # Парсим короткий код из ссылки
        shortcode = reels_url.split("/")[-2]
        post = instaloader.Post.from_shortcode(loader.context, shortcode)

        video_url = post.video_url
        if video_url:
            response = requests.get(video_url, stream=True)
            response.raise_for_status()

            # Обрабатываем видео перед отправкой
            processed_video = process_video_in_memory(response.content)

            # Отправляем видео
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo"
            files = {"video": ("reels_video.mp4", processed_video, "video/mp4")}
            data = {
                "chat_id": chat_id,
                "supports_streaming": False,
                "caption": "Ваше видео из Instagram Reels 🎥",
            }
            requests.post(url, data=data, files=files)

            return True
        else:
            print("Видео не найдено в посте.")
            return False
    except Exception as e:
        print(f"Error sending video: {e}")
        return False

if __name__ == '__main__':
    app.run(debug=True)
