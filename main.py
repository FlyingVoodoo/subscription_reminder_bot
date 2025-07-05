from dotenv import load_dotenv
load_dotenv()      
import os
import logging
import datetime
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
    await update.message.reply_text('Отлично! Добавим новую подпискую Введите название сервиса:')
    return ADD_SERVICE_NAME 

async def add_service_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Getiing name of serv and asking user for summ"""
    context.user_data['service_name'] = update.message.text
    await update.message.reply_text(f'Хорошо, "{context.user_data["service_name"]}". Теперь введите сумму платежа (например), "9.99"):')
    return ADD_AMOUNT
async def add_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        ammount = float(update.message.text.replace('.', '.'))
        context.user_data['amount'] = ammount
        await update.message.reply_text('Понял. Теперь введите дату следующей оплаты в формате ГГГГ-ММ-ДД (например, "2025-07-15"):')
        return ADD_DATE
    except ValueError:
        await update.message.reply_text('Это не похоже на число. Пожалуйста, введите сумму цифрами (например, "9.99"):')
        return ADD_AMOUNT
    
async def add_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    date_str = update.message.text.strip()
    logging.info(f"Получена строка даты от пользователя '{date_str}'")

    try:
        parsed_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        logging.info(f"Дата успешно репарсена: {parsed_date}")

        if parsed_date < datetime.date.today():
            await update.message.reply_text("Дата оплаты не может быть в прошлом. Пожалуйста, введите корректную дату.")
            return ADD_DATE
        
        add_subscription(
            user_id=update.effective_user.id,
            service_name=context.user_data['service_name'],
            amount=context.user_data['amount'],
            next_payment_date=date_str
        )
        await update.message.reply_text(
            f"Отлично! Подписка '{context.user_data['service_name']}' на сумму {context.user_data['amount']} rub. "
            f"со следующей оплатой {date_str} добавлена."
        )
        return ConversationHandler.END
    except ValueError as e:
        logging.info(f"Ошибка парсинга даты '{date_str}': {e}")
        await update.message.reply_text('Неверный формат даты. Пожалуйста, введите дату в формате ГГГГ-ММ-ДД:')
        return ADD_DATE
    
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Операция отменена. Теперь можете начать заново.')
    return ConversationHandler.END

def main():
    create_table()
    logging.info("База данных и таблица подписок проверены.созданы.")

    if TOKEN is None:
        print("Ошибка: Токен бота не найденю Установите переменную окружения")
        return
    
    application = ApplicationBuilder().token(TOKEN).build()

    start_handler = CommandHandler('start', start)
    help_handler = CommandHandler('help', help)
    add_conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('add', add_start)],
        states={
            ADD_SERVICE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_service_name)],
            ADD_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_amount)],
            ADD_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_date)],
        },
        fallbacks=[CommandHandler('cancel', cancel_command)]
    )

    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(add_conversation_handler)

    logging.info("Бот запущен. Ctrl+C для остановки работы.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()