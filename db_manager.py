import aiosqlite
import datetime

DB_NAME = 'subscription.db'

async def create_table():
    async with aiosqlite.connect(DB_NAME) as con:
        await con.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                service_name TEXT NOT NULL,
                amount REAL,
                next_payment_date TEXT NOT NULL,
                reminder_status INTEGER DEFAULT 0 -- 0-ничего, 1-за 3 дня, 2-за 1 день, 3-просрочка
            )
        ''')
        await con.commit()
    print(f"Таблица 'subscriptions' проверена/создана в {DB_NAME}.")
    

async def add_subscription(user_id: int, service_name: str, amount: float, next_payment_date: str) -> None:
    async with aiosqlite.connect(DB_NAME) as con:
        await con.execute('''
            INSERT INTO subscriptions (user_id, service_name, amount, next_payment_date)
            VALUES (?, ?, ?, ?)
        ''', (user_id, service_name, amount, next_payment_date))
        await con.commit()
    print(f"Добавлена подписка для user_id {user_id}: {service_name}")


async def get_subscribtion_by_user(user_id: int) -> list[tuple]:
    async with aiosqlite.connect(DB_NAME) as con:
        cur = await con.cursor()
        await cur.execute("SELECT id, service_name, amount, next_payment_date FROM subscriptions WHERE user_id = ?", (user_id,))
        subscriptions = await cur.fetchall()
    return subscriptions

async def delete_subscription(user_id: int, sub_id: int) -> bool:
    """
    Удаляет подписку по user_id и ID подписки.
    Возвращает True, если подписка была удалена, иначе False.
    """
    async with aiosqlite.connect(DB_NAME) as con:
        cur = await con.cursor()
        await cur.execute("DELETE FROM subscriptions WHERE user_id = ? AND id = ?", (user_id, sub_id))
        rows_affected = cur.rowcount 
        await con.commit() 
    return rows_affected > 0 

async def update_subscription_after_payment(user_id: int, sub_id: int) -> tuple[bool, str, str]:
    async with aiosqlite.connect(DB_NAME) as con: 
        cur = await con.cursor() 
        await cur.execute("SELECT next_payment_date, service_name FROM subscriptions WHERE user_id = ? AND id = ?", (user_id, sub_id))
        result = await cur.fetchone() 

    if not result:
        con.close()
        return False, None, None # Подписка не найдена или не принадлежит пользователю

    current_date_str, service_name = result
    
    try:
        current_date = datetime.datetime.strptime(current_date_str, '%Y-%m-%d').date()
        year = current_date.year
        month = current_date.month + 1
        day = current_date.day
        if month > 12:
            month = 1
            year += 1
        
        try:
            new_payment_date = datetime.date(year, month, day)
        except ValueError:
            new_payment_date = datetime.date(year, month, 1) + datetime.timedelta(days=-1)

        new_date_str = new_payment_date.strftime('%Y-%m-%d')

        cur.execute('''
            UPDATE subscriptions
            SET next_payment_date = ?, reminder_status = 0
            WHERE user_id = ? AND id = ?
        ''', (new_date_str, user_id, sub_id))
        con.commit()
        con.close()
        return True, service_name, new_date_str
    except Exception as e:
        print(f"Ошибка при обновлении даты платежа: {e}")
        con.close()
        return False, None, None

async def get_subscriptions_for_reminders(days_before: int) -> list[tuple]:
    """
    Возвращает список подписок, для которых пора отправить напоминание.
    days_before: количество дней до даты оплаты.
    """
    async with aiosqlite.connect(DB_NAME) as con:
        cur = await con.cursor()
        
        today = datetime.date.today()
        target_date = today + datetime.timedelta(days=days_before)
        target_date_str = target_date.strftime('%Y-%m-%d')

        query = """
            SELECT id, user_id, service_name, amount, next_payment_date, reminder_status
            FROM subscriptions
            WHERE next_payment_date = ?
        """
        
        if days_before == 3:
            query += " AND reminder_status = 0"
        elif days_before == 1:
            query += " AND reminder_status = 1"
        
        await cur.execute(query, (target_date_str,)) 
        subscriptions = await cur.fetchall() 
    return subscriptions

async def update_reminder_status(sub_id: int, new_status: int) -> None:
    """Обновляет статус напоминания для конкретной подписки."""
    async with aiosqlite.connect(DB_NAME) as con:
        await con.execute("UPDATE subscriptions SET reminder_status = ? WHERE id = ?", (new_status, sub_id)) 
        await con.commit()
