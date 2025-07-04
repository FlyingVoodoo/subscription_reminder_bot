import sqlite3

DB_NAME = 'subscription.db'

def create_table():
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMAREY KEY,
            user_id INTEGER NOT NULL,
            amount REAL,
            next_payment_date TEXT NOT NULL,
            reminder_setnt INTEGER DEFAULT 0 -- 0: не отправлено, 1: отправлено (для текущего периода)
        )
    ''')

    con.commit()
    con.close()
if __name__ == '__main__':
    create_table()
    print(f"База данных '{DB_NAME}' и таблица 'subscriptions' проверены/созданы.")