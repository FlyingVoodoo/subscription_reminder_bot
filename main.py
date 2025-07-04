from dotenv import load_dotenv
load_dotenv()      
import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler, 
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)

from db_manager import add_subscription
from db_manager import create_table

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


ADD_SERVICE_NAME, ADD_AMOUNT, ADD_DATE = range(3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Привет! Я бот-напоминалка o подписках. Используй /add для добавления подписки")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Я умею напоминать o подписах. Команлы: /start, /add, /list, /delete, help.")

# --- Function for command /add (Conversation Handler) ---

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starting add-process and asks for name of serv"""
    await update.message.reply_text('Отлично! Добавим новую подпискую ВВедите название сервиса:')
    return ADD_SERVICE_NAME 

async def add_service_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Getiing name of serv and asking user for summ"""
    context.user_data['service_name'] = update.message.text
    await update.message.reply_text(f'Хорошо, "{context.user_data["service_name"]}". Теперь введите сумму платежа (например), "9.99"):')
    return ADD_AMOUNT
async def add_ammount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        ammount = float(update.message.text.replace('.', '.'))
        context.user_data['amount'] = ammount
        await update.message.reply_text('Понял. Теперь введите дату следующей оплаты в формате ГГГГ-ММ-ДД (например, "2025-07-15"):')
        return ADD_DATE
    except ValueError:
        await update.message.reply_text('Это не похоже на число. Пожалуйста, введите сумму цифрами (например, "9.99"):')
        return ADD_AMOUNT

def main():
    if TOKEN is None:
        print("Ошибка: Токен бота не найденю Установите переменную окружения")
        return
    
    application = ApplicationBuilder().token(TOKEN).build()

    start_handler = CommandHandler('start', start)
    help_handler = CommandHandler('help', help)
    application.add_handler(start_handler)
    application.add_handler(help_handler)

    print("Бот запущен. Ctrl+C для остановки работы.")
    application.run_polling()

if __name__ == '__main__':
    main()