from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
import datetime
import requests
import threading
import time
import smtplib
import config
from waitress import serve  # Добавляем Waitress для запуска сервера

app = Flask(__name__)

# Подключение к базе данных
def connect_db():
    return sqlite3.connect("database.db")

# Автоудаление заявок старше 7 дней
def delete_old_logs():
    conn = connect_db()
    cursor = conn.cursor()
    seven_days_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("DELETE FROM network_logs WHERE created_at < ?", (seven_days_ago,))
    conn.commit()
    conn.close()

# Создание таблицы
def create_table():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS network_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        issue TEXT NOT NULL,
        status TEXT DEFAULT 'Новая',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

create_table()
delete_old_logs()

# Проверка доступности сайтов
def check_website(url):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return "Работает"
        else:
            return "Ошибка"
    except requests.exceptions.RequestException:
        return "Не доступен"

# Уведомления через выбранный мессенджер
def send_notification(message):
    if config.MESSENGER == "telegram":
        telegram_url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
        requests.post(telegram_url, data={"chat_id": config.TELEGRAM_CHAT_ID, "text": message})
    
    elif config.MESSENGER == "whatsapp":
        whatsapp_url = f"{config.WHATSAPP_API_URL}&text={message}"
        requests.get(whatsapp_url)
    
    elif config.MESSENGER == "email":
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.EMAIL_SENDER, config.EMAIL_PASSWORD)
            server.sendmail(config.EMAIL_SENDER, config.EMAIL_ADMIN, f"Subject: Ошибка сети\n\n{message}")

# Мониторинг сайтов и запись ошибок
def monitor_sites():
    sites = ["https://example.com", "https://google.com"]
    conn = connect_db()
    cursor = conn.cursor()

    for site in sites:
        status = check_website(site)
        if status != "Работает":
            error_message = f"❌ {site} не работает!"
            cursor.execute("INSERT INTO network_logs (issue, status) VALUES (?, ?)", (error_message, "Ошибка"))
            send_notification(error_message)  # Отправляем сообщение админу

    conn.commit()
    conn.close()

# Запуск автоматического мониторинга (каждые 5 минут)
def start_monitoring():
    while True:
        monitor_sites()
        time.sleep(300)  # 5 минут

thread = threading.Thread(target=start_monitoring)
thread.daemon = True
thread.start()

# Главная страница (новые заявки сверху)
@app.route('/')
def index():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, issue, status, created_at FROM network_logs ORDER BY created_at DESC")
    logs = cursor.fetchall()
    conn.close()
    
    return render_template("incidents.html", logs=logs)

# Форма отправки ошибки
@app.route('/report', methods=["GET", "POST"])
def report():
    if request.method == "POST":
        issue = request.form["issue"]
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO network_logs (issue) VALUES (?)", (issue,))
        conn.commit()
        conn.close()
        return redirect("/")
    return render_template("report.html")

# Обновление статуса ошибки
@app.route('/update_status/<int:id>', methods=["POST"])
def update_status(id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE network_logs SET status = 'Решена' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "Решена"})

# Удаление заявки
@app.route('/delete_issue/<int:id>', methods=["POST"])
def delete_issue(id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM network_logs WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"deleted": True})

# Запуск сервера на Waitress
if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=5000)
