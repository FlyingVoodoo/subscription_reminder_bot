import aiosqlite
import datetime
from calendar import monthrange

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
    try:
        async with aiosqlite.connect(DB_NAME) as con:
            await con.execute("PRAGMA journal_mode = WAL;") 
            cur = await con.cursor()

            print(f"[DEBUG-DB] Поиск подписки: user_id={user_id}, sub_id={sub_id}")

            await cur.execute("SELECT next_payment_date, service_name FROM subscriptions WHERE user_id = ? AND id = ?", (user_id, sub_id))
            result = await cur.fetchone() 

            if not result:
                print(f"[DEBUG-DB] Подписка не найдена для user_id={user_id}, sub_id={sub_id}")
                return False, None, None 

            current_date_str, service_name = result
            print(f"[DEBUG-DB] Найдена подписка '{service_name}', текущая дата: {current_date_str}")

            try:
                current_date = datetime.datetime.strptime(current_date_str, '%Y-%m-%d').date()
                year = current_date.year
                month = current_date.month + 1
                day = current_date.day
                if month > 12:
                    month = 1
                    year += 1

                max_day_in_new_month = monthrange(year, month)[1]
                new_day = min(day, max_day_in_new_month)
                new_payment_date = datetime.date(year, month, new_day)

                new_date_str = new_payment_date.strftime('%Y-%m-%d')
                print(f"[DEBUG-DB] Новая дата оплаты для '{service_name}': {new_date_str}")

            except ValueError as ve:
                print(f"[DEBUG-DB] Ошибка при расчете новой даты: {ve}")
                return False, None, None


            await cur.execute('''
                UPDATE subscriptions
                SET next_payment_date = ?, reminder_status = 0
                WHERE user_id = ? AND id = ?
            ''', (new_date_str, user_id, sub_id))

            rows_affected = cur.rowcount
            await con.commit()
            print(f"[DEBUG-DB] Выполнен коммит. Изменено строк: {rows_affected}")

            if rows_affected > 0:
                return True, service_name, new_date_str
            else:
                print(f"[DEBUG-DB] UPDATE не изменил ни одной строки для sub_id={sub_id}, user_id={user_id}")
                return False, None, None

    except Exception as e:
        print(f"Ошибка при обновлении даты платежа: {e}")
        return False, None, None

async def get_subscriptions_for_reminders(days_before: int) -> list[tuple]:

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
            query += " AND reminder_status < 2"
        
        await cur.execute(query, (target_date_str,)) 
        subscriptions = await cur.fetchall() 
    return subscriptions

async def get_overdue_subscriptions() -> list[tuple]:
    async with aiosqlite.connect(DB_NAME) as con:
        cur = await con.cursor()
        today = datetime.date.today()
        today_str = today.strftime('%Y-%m-%d')

        query = """
            SELECT id, user_id, service_name, amount, next_payment_date, reminder_status
            FROM subscriptions
            WHERE next_payment_date < ? AND reminder_status < 3
        """
        await cur.execute(query, (today_str,))
        subscriptions = await cur.fetchall()
    return subscriptions
    

async def update_reminder_status(sub_id: int, new_status: int) -> None:
    async with aiosqlite.connect(DB_NAME) as con:
        await con.execute("UPDATE subscriptions SET reminder_status = ? WHERE id = ?", (new_status, sub_id)) 
        await con.commit()
