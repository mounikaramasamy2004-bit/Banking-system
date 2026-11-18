import sqlite3
import os
from werkzeug.security import generate_password_hash
import config

def init_database(seed_demo_data=True):
    db_path = config.DB_PATH
    
    # Remove existing db if fresh setup is needed
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    # Create users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT NOT NULL,
        account_number TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        balance REAL NOT NULL DEFAULT 0.0,
        role TEXT NOT NULL DEFAULT 'user',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Create transactions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        amount REAL NOT NULL,
        balance REAL NOT NULL,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    conn.commit()

    if seed_demo_data:
        # Check if users already exist
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        if count == 0:
            print("Seeding sample users and transactions as shown in project report...")
            # 1. Admin user
            admin_pw = generate_password_hash("admin123")
            cursor.execute("""
            INSERT INTO users (name, email, phone, account_number, password_hash, balance, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ("Administrator", "admin@bankease.com", "9876543210", "100000000001", admin_pw, 0.0, "admin", "2026-06-01 09:00:00"))

            # 2. Main Student Demo User from report (Jagath)
            jagath_pw = generate_password_hash("password123")
            cursor.execute("""
            INSERT INTO users (name, email, phone, account_number, password_hash, balance, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ("Jagath", "jagathselva15@gmail.com", "8925005815", "383588248332", jagath_pw, 2500.0, "user", "2026-06-02 04:00:00"))
            jagath_id = cursor.lastrowid

            # 3. Recipient User from report (Varuun Kumar)
            varuun_pw = generate_password_hash("password123")
            cursor.execute("""
            INSERT INTO users (name, email, phone, account_number, password_hash, balance, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ("Varuun Kumar", "varuun@bankease.com", "9843217654", "48485738324", varuun_pw, 12500.0, "user", "2026-06-02 04:05:00"))
            varuun_id = cursor.lastrowid

            # 4. Insert transactions matching Fig 5.1.6
            transactions = [
                (jagath_id, "deposit", 50000.00, 50000.00, "Deposit to account", "2026-06-02 04:13:47"),
                (jagath_id, "withdrawal", 50000.00, 0.00, "Withdrawal from account", "2026-06-02 04:14:18"),
                (jagath_id, "deposit", 25000.00, 25000.00, "Deposit to account", "2026-06-02 04:14:35"),
                (jagath_id, "withdrawal", 20000.00, 5000.00, "Withdrawal from account", "2026-06-02 04:15:35"),
                (jagath_id, "transfer_out", 2500.00, 2500.00, "Transfer to Varuun Kumar (48485738324)", "2026-06-02 04:19:57"),
                (varuun_id, "transfer_in", 2500.00, 12500.00, "Transfer from Jagath (383588248332)", "2026-06-02 04:19:57"),
            ]

            cursor.executemany("""
            INSERT INTO transactions (user_id, type, amount, balance, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, transactions)

            conn.commit()
            print("Sample data populated successfully.")

    conn.close()
    print("Database initialized at:", db_path)

if __name__ == '__main__':
    init_database(seed_demo_data=True)
