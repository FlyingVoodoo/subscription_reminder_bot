from dotenv import load_dotenv
load_dotenv()      
import os
import logging
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler, 
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)

from db_manager import create_table

import handlers

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def post_init(application):
    await create_table()
    logging.info("База данных и таблица подписок проверены/созданы.")

def main():

    if TOKEN is None:
        print("Ошибка: Токен бота не найденю Установите переменную окружения")
        return
    
    application = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

    start_handler = CommandHandler('start', handlers.start)
    help_handler = CommandHandler('help', handlers.help)
    list_handler = CommandHandler('list', handlers.list_subscriptions)
    cancel_in_main_menu_handler = CommandHandler('cancel', handlers.cancel_already_in_main_menu)
    add_conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('add', handlers.add_start)],
        states={
            handlers.ADD_SERVICE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.add_service_name)],
            handlers.ADD_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.add_amount)],
            handlers.ADD_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.add_date)],
        },
        fallbacks=[CommandHandler('cancel', handlers.cancel_command)]
    )
    delete_handler = CommandHandler('delete', handlers.delete_subscription_command)

    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(add_conversation_handler)
    application.add_handler(list_handler)
    application.add_handler(delete_handler)
    application.add_handler(cancel_in_main_menu_handler)

    logging.info("Бот запущен. Ctrl+C для остановки работы.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()