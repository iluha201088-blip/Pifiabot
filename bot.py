from flask import Flask, request, jsonify
from binance import Client
import telebot
import threading

# === НАСТРОЙКИ (заполните ниже) ===
API_KEY = ""V6iumjWj1jYafSD7H8p6eDt8jeur7mpxi5kmsOj7ptkMtsuvr1g0hjvqr2i9gxKJ","
API_SECRET = "ITt48AGOXSDMFsyrXYoT0jdnMcosW7oOBBa6pLDjgw3mIkUqM8RN3K24AiQZs88C",
TELEGRAM_TOKEN = "7753186609:AAEuJvOGtTR5yP6kXyaLJjvbKnYgRmebejc"
CHAT_ID = 5203579568
LEVERAGE = 5
SYMBOL = "BTCUSDT"

# Инициализация
client = Client(API_KEY, API_SECRET)
bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

# Устанавливаем плечо
client.futures_change_leverage(symbol=SYMBOL, leverage=LEVERAGE)

# Отправка сообщения в Telegram
def send_telegram(message):
    try:
        bot.send_message(CHAT_ID, message)
    except Exception as e:
        print(f"Telegram error: {e}")

# При старте бота — уведомление
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "✅ Pifia Trader Bot запущен. Готов к работе.")

# Отправляем стартовое сообщение
def send_startup():
    try:
        bot.send_message(CHAT_ID, "🟢 Бот запущен и ожидает сигналы от TradingView")
    except:
        print("Не удалось отправить стартовое сообщение. Проверьте CHAT_ID.")

# Вебхук от TradingView
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    side = data.get('side', '').upper()
    symbol = data.get('symbol', '').upper()

    if symbol != SYMBOL:
        return jsonify({"error": "Wrong symbol"}), 400

    try:
        if side == "BUY":
            # Получаем баланс USDT
            account = client.futures_account()
            usdt_balance = 0
            for asset in account['assets']:
                if asset['asset'] == 'USDT':
                    usdt_balance = float(asset['availableBalance'])
                    break

            if usdt_balance < 1:
                msg = "❌ Недостаточно USDT для открытия позиции"
                send_telegram(msg)
                return jsonify({"error": msg}), 400

            # Рассчитываем объём
            price = float(client.futures_symbol_ticker(symbol=SYMBOL)['price'])
            qty = (usdt_balance * LEVERAGE) / price
            qty = round(qty, 3)

            # Открываем лонг
            client.futures_create_order(
                symbol=SYMBOL,
                side="BUY",
                type="MARKET",
                quantity=qty
            )

            msg = f"🟢 LONG открыт\nСимвол: {SYMBOL}\nОбъём: {qty} BTC\nЦена: {price:.2f}\nБаланс: {usdt_balance:.2f} USDT"
            send_telegram(msg)

        elif side == "SELL":
            positions = client.futures_position_information(symbol=SYMBOL)
            pos = [p for p in positions if p['positionSide'] == 'LONG'][0]
            qty = abs(float(pos['positionAmt']))

            if qty == 0:
                msg = "🟡 Нет позиции для закрытия"
                send_telegram(msg)
                return jsonify({"status": msg})

            price = float(client.futures_symbol_ticker(symbol=SYMBOL)['price'])

            client.futures_create_order(
                symbol=SYMBOL,
                side="SELL",
                type="MARKET",
                quantity=qty
            )

            msg = f"🔴 Позиция закрыта\nСимвол: {SYMBOL}\nОбъём: {qty} BTC\nЦена: {price:.2f}"
            send_telegram(msg)

        else:
            return jsonify({"error": "Invalid side"}), 400

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        error_msg = f"❌ Ошибка: {str(e)}"
        print(error_msg)
        send_telegram(error_msg)
        return jsonify({"error": str(e)}), 500

# Запуск Flask в отдельном потоке
def run_flask():
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    send_startup()
    bot.infinity_polling()