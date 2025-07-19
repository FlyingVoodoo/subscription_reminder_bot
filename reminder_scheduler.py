import logging
import datetime
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

# Импортируем асинхронные функции из db_manager.py
from db_manager import get_subscriptions_for_reminders, update_reminder_status, get_overdue_subscriptions

logger = logging.getLogger(__name__)

# constants
REMINDER_STATUS_NONE = 0
REMINDER_STATUS_3_DAYS = 1
REMINDER_STATUS_1_DAY = 2
REMINDER_STATUS_OVERDUE = 3

async def check_and_send_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:

    logger.info("Запуск проверки подписок на напоминания...")

    # 3 days before
    subscriptions_3_days = await get_subscriptions_for_reminders(3)
    if subscriptions_3_days:
        logger.info(f"Найдено {len(subscriptions_3_days)} подписок для напоминания за 3 дня.")
        for sub_id, user_id, service_name, amount, next_payment_date, current_status in subscriptions_3_days:
            message = (
                f"⏰ **Напоминание об оплате!** ⏰\n\n"
                f"Сервис: **{service_name}**\n"
                f"Сумма: **{amount:.2f}**\n"
                f"Дата следующей оплаты: **{next_payment_date}** (через 3 дня)\n\n"
                f"Чтобы отметить подписку как оплаченную, используйте команду: `/paid {sub_id}`"
            )
            try:
                await context.bot.send_message(chat_id=user_id, text=message, parse_mode=ParseMode.MARKDOWN)
                await update_reminder_status(sub_id, REMINDER_STATUS_3_DAYS)
                logger.info(f"Напоминание за 3 дня отправлено для подписки ID {sub_id}, user {user_id}")
            except Exception as e:
                logger.error(f"Не удалось отправить напоминание для подписки ID {sub_id}, user {user_id}: {e}")
    else:
        logger.info("Нет подписок для напоминания за 3 дня.")

    # 1 day before
    subscriptions_1_day = await get_subscriptions_for_reminders(1)
    if subscriptions_1_day:
        logger.info(f"Найдено {len(subscriptions_1_day)} подписок для напоминания за 1 день.")
        for sub_id, user_id, service_name, amount, next_payment_date, current_status in subscriptions_1_day:
            message = (
                f"❗️ **Последнее напоминание!** ❗️\n\n"
                f"Завтра, **{next_payment_date}**, наступает срок оплаты подписки:\n"
                f"Сервис: **{service_name}**\n"
                f"Сумма: **{amount:.2f}**\n\n"
                f"Чтобы отметить подписку как оплаченную, используйте команду: `/paid {sub_id}`"
            )
            try:
                await context.bot.send_message(chat_id=user_id, text=message, parse_mode=ParseMode.MARKDOWN)
                await update_reminder_status(sub_id, REMINDER_STATUS_1_DAY)
                logger.info(f"Напоминание за 1 день отправлено для подписки ID {sub_id}, user {user_id}")
            except Exception as e:
                logger.error(f"Не удалось отправить напоминание для подписки ID {sub_id}, user {user_id}: {e}")
    else:
        logger.info("Нет подписок для напоминания за 1 день.")

    overdue_subscriptions = await get_overdue_subscriptions()
    if overdue_subscriptions:
        logger.info(f"Найдено {len(overdue_subscriptions)} просроченных подписок.")
        for sub_id, user_id, service_name, amount, next_payment_date, current_status in overdue_subscriptions:
            message = (
                f"🚨 **Подписка просрочена!** 🚨\n\n"
                f"Срок оплаты подписки **{service_name}** на сумму **{amount:.2f}** истек **{next_payment_date}**.\n\n"
                f"Чтобы отметить подписку как оплаченную и сбросить напоминания, используйте команду: `/paid {sub_id}`"
            )
            try:
                await context.bot.send_message(chat_id=user_id, text=message, parse_mode=ParseMode.MARKDOWN)
                await update_reminder_status(sub_id, REMINDER_STATUS_OVERDUE)
                logger.info(f"Напоминание о просрочке отправлено для подписки ID {sub_id}, user {user_id}")
            except Exception as e:
                logger.error(f"Не удалось отправить напоминание о просрочке для подписки ID {sub_id}, user {user_id}: {e}")
    else:
        logger.info("Нет просроченных подписок.")

