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

from db_manager import add_subscription, create_table, get_subscribtion_by_user, delete_subscription

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


ADD_SERVICE_NAME, ADD_AMOUNT, ADD_DATE = range(3)

DELETE_ID, DELETE_CONFIRMATION = range(3, 5)


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
            f"Отлично! Подписка '{context.user_data['service_name']}' на сумму {context.user_data['amount']} RUB. "
            f"со следующей оплатой {date_str} добавлена."
        )
        return ConversationHandler.END
    except ValueError as e:
        logging.info(f"Ошибка парсинга даты '{date_str}': {e}")
        await update.message.reply_text('Неверный формат даты. Пожалуйста, введите дату в формате ГГГГ-ММ-ДД:')
        return ADD_DATE
    
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Отменяет текущую операцию (если она в ConversationHandler) и завершает его.
    Очищает временные данные пользователя, связанные с текущим диалогом.
    """
    logging.info(f"Операция отменена пользователем {update.effective_user.id}")
    
    if 'service_name' in context.user_data:
        del context.user_data['service_name']
    if 'amount' in context.user_data:
        del context.user_data['amount']
    
    await update.message.reply_text('Операция отменена. Вы вернулись в главное меню. Теперь можете начать заново.')
    return ConversationHandler.END

async def cancel_already_in_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Сообщает пользователю, что он уже находится в главном меню,
    если команда /cancel введена вне активного диалога.
    """
    await update.message.reply_text('Вы уже находитесь в главном меню. Нет активных операций для отмены.')
    
async def list_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    subscriptions = get_subscribtion_by_user(user_id)

    if not subscriptions:
        await update.message.reply_text("У вас пока нет активных подписок. Используйте /add для добавления первой!")
        return
    
    message_text = "Ваши подписки:\n\n"
    for sub_id, service_name, amount, next_payment_date in subscriptions:
        message_text += f"**ID {sub_id}**\n" \
                        f"Сервис: {service_name}\n" \
                        f"Сумма: {amount: .2f}\n" \
                        f"Дата оплаты: {next_payment_date}\n\n"
    await update.message.reply_text(message_text, parse_mode='Markdown')

async def delete_subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает команду /delete.
    Принимает ID подписки в качестве аргумента.
    Пример: /delete 123
    """
    user_id = update.effective_user.id
    args = context.args

    if not args:
        await update.message.reply_text(
            "Пожалуйста, укажите ID подписки, которую хотите удалить. "
            "Чтобы узнать ID, используйте команду /list.\n"
            "Пример: `/delete 123`"
        )
        return

    try:
        sub_id_to_delete = int(args[0])
    except ValueError:
        await update.message.reply_text(
            "Неверный формат ID. Пожалуйста, введите числовой ID подписки. "
            "Чтобы узнать ID, используйте команду /list.\n"
            "Пример: `/delete 123`"
        )
        return

    deleted_successfully = delete_subscription(user_id, sub_id_to_delete)

    if deleted_successfully:
        await update.message.reply_text(f"Подписка с ID **{sub_id_to_delete}** успешно удалена.")
    else:
        await update.message.reply_text(f"Подписка с ID **{sub_id_to_delete}** не найдена в вашем списке.")

def main():
    create_table()
    logging.info("База данных и таблица подписок проверены.созданы.")

    if TOKEN is None:
        print("Ошибка: Токен бота не найденю Установите переменную окружения")
        return
    
    application = ApplicationBuilder().token(TOKEN).build()

    start_handler = CommandHandler('start', start)
    help_handler = CommandHandler('help', help)
    list_handler = CommandHandler('list', list_subscriptions)
    cancel_in_main_menu_handler = CommandHandler('cancel', cancel_already_in_main_menu)
    add_conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('add', add_start)],
        states={
            ADD_SERVICE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_service_name)],
            ADD_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_amount)],
            ADD_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_date)],
        },
        fallbacks=[CommandHandler('cancel', cancel_command)]
    )
    delete_handler = CommandHandler('delete', delete_subscription_command)

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