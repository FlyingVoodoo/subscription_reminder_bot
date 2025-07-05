import sqlite3

DB_NAME = 'subscription.db'

def create_table():
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            service_name TEXT NOT NULL,
            amount REAL,
            next_payment_date TEXT NOT NULL,
            reminder_setnt INTEGER DEFAULT 0 -- 0: не отправлено, 1: отправлено (для текущего периода)
        )
    ''')

    con.commit()
    con.close()
    

def add_subscription(user_id: int, service_name: str, amount: float, next_payment_date: str) -> None:
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    cur.execute('''
        INSERT INTO subscriptions (user_id, service_name, amount, next_payment_date)
        VALUES (?, ?, ?, ?)
    ''', (user_id, service_name, amount, next_payment_date))
    con.commit()
    con.close()
    print(f"Добавлена подписка для user_id {user_id}: {service_name}")


def get_subscribtion_by_user(user_id: int) -> list[tuple]:
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    cur.execute("SELECT id, service_name, amount, next_payment_date FROM subscriptions WHERE user_id = ?", (user_id))
    subscriptions = cur.fetchall()
    con.close()
    return subscriptions
if __name__ == '__main__':
    create_table()
    print(f"База данных '{DB_NAME}' и таблица 'subscriptions' проверены/созданы.")

