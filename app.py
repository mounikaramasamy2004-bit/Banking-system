import io
import csv
import random
import sqlite3
import smtplib
from datetime import datetime
from functools import wraps
from email.message import EmailMessage

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, Response
)
from werkzeug.security import generate_password_hash, check_password_hash

import config

app = Flask(__name__, static_folder='assets', template_folder='templates')
app.secret_key = config.SECRET_KEY


def dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def db_connect():
    try:
        connection = sqlite3.connect(config.DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        connection.row_factory = dict_factory
        connection.execute('PRAGMA foreign_keys = ON')
        return connection
    except sqlite3.Error as exc:
        raise RuntimeError('Unable to open SQLite database. Check DB_PATH in config.py.') from exc


def init_db():
    connection = db_connect()
    with connection:
        cursor = connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT NOT NULL,
                account_number TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                balance REAL DEFAULT 0.0,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                balance REAL NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Pre-seed demo user matching Chapter 5 screenshots if empty
        cursor.execute('SELECT COUNT(*) AS count FROM users')
        if cursor.fetchone()['count'] == 0:
            demo_pass = generate_password_hash('password123')
            # 1. Primary demo user (Jagath - Fig 5.1.1 & Fig 5.1.2)
            cursor.execute('''
                INSERT INTO users (name, email, phone, account_number, password_hash, balance, role)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', ('Jagath', 'jagathselva15@gmail.com', '8925005815', '383588248332', demo_pass, 2500.0, 'user'))
            user_id = cursor.lastrowid
            
            # 2. Recipient account (Varuun Kumar - Fig 5.1.5 & Fig 5.1.6)
            cursor.execute('''
                INSERT INTO users (name, email, phone, account_number, password_hash, balance, role)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', ('Varuun Kumar', 'varuun@bankease.com', '9876543210', '48485738324', demo_pass, 2500.0, 'user'))
            
            # 3. Pre-seed transactions matching Fig 5.1.6
            sample_txs = [
                ('Deposit', 50000.00, 50000.00, 'Deposit to account', '2026-06-02 04:13:47'),
                ('Withdrawal', 50000.00, 0.00, 'Withdrawal from account', '2026-06-02 04:14:18'),
                ('Deposit', 25000.00, 25000.00, 'Deposit to account', '2026-06-02 04:14:35'),
                ('Withdrawal', 20000.00, 5000.00, 'Withdrawal from account', '2026-06-02 04:15:35'),
                ('Transfer Out', 2500.00, 2500.00, 'Transfer to Varuun Kumar (48485738324)', '2026-06-02 04:19:57')
            ]
            for tx in sample_txs:
                cursor.execute('''
                    INSERT INTO transactions (user_id, type, amount, balance, details, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, tx[0], tx[1], tx[2], tx[3], tx[4]))

        connection.commit()


@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if 'role' not in session or session['role'] != 'admin':
            flash('Access restricted to administrators.', 'danger')
            return redirect(url_for('dashboard'))
        return view(**kwargs)
    return wrapped_view


def get_current_user():
    if 'user_id' not in session:
        return None
    connection = db_connect()
    with connection:
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
        return cursor.fetchone()


def send_notification_email(recipient_email, subject, body):
    if not config.MAIL_USERNAME or not config.MAIL_PASSWORD:
        return False
    try:
        message = EmailMessage()
        message['From'] = config.MAIL_USERNAME
        message['To'] = recipient_email
        message['Subject'] = subject
        message.set_content(body)

        if config.MAIL_USE_SSL:
            server = smtplib.SMTP_SSL(config.MAIL_SERVER, config.MAIL_PORT)
        else:
            server = smtplib.SMTP(config.MAIL_SERVER, config.MAIL_PORT)

        if config.MAIL_USE_TLS:
            server.starttls()

        server.login(config.MAIL_USERNAME, config.MAIL_PASSWORD)
        server.send_message(message)
        server.quit()
        return True
    except Exception:
        return False


def record_transaction(connection, user_id, tx_type, amount, balance, details):
    cursor = connection.cursor()
    cursor.execute(
        '''INSERT INTO transactions (user_id, type, amount, balance, details, created_at)
           VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))''',
        (user_id, tx_type, amount, balance, details)
    )


def is_duplicate_transaction(connection, user_id, tx_type, amount, window_seconds=5):
    cursor = connection.cursor()
    cursor.execute(
        '''SELECT created_at FROM transactions
           WHERE user_id = ? AND type = ? AND amount = ?
           AND (strftime('%s', 'now', 'localtime') - strftime('%s', created_at)) < ?''',
        (user_id, tx_type, amount, window_seconds)
    )
    return cursor.fetchone() is not None


@app.errorhandler(RuntimeError)
def runtime_error(error):
    return render_template('error.html', message=str(error)), 500


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
@app.route('/register.html', methods=['GET', 'POST'])
def register():
    suggested_acc = "".join([str(random.randint(0, 9)) for _ in range(12)])
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        account_number = request.form.get('account_number', '').strip() or suggested_acc
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not name or not email or not phone or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        connection = db_connect()
        try:
            with connection:
                cursor = connection.cursor()
                cursor.execute(
                    '''INSERT INTO users (name, email, phone, account_number, password_hash, balance, role)
                       VALUES (?, ?, ?, ?, ?, 0.0, 'user')''',
                    (name, email, phone, account_number, generate_password_hash(password))
                )
                connection.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('An account with this email or account number already exists.', 'danger')

    return render_template('register.html', suggested_acc=suggested_acc)


@app.route('/login', methods=['GET', 'POST'])
@app.route('/login.html', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip()
        password = request.form.get('password', '')

        connection = db_connect()
        with connection:
            cursor = connection.cursor()
            cursor.execute(
                'SELECT * FROM users WHERE email = ? OR account_number = ?',
                (login_id.lower(), login_id)
            )
            user = cursor.fetchone()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['user_name'] = user['name']
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email/account number or password.', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@app.route('/dashboard.html')
@login_required
def dashboard():
    user = get_current_user()
    connection = db_connect()
    with connection:
        cursor = connection.cursor()
        cursor.execute(
            'SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT 5',
            (user['id'],)
        )
        recent_transactions = cursor.fetchall()
        cursor.execute('SELECT COUNT(*) AS total FROM transactions WHERE user_id = ?', (user['id'],))
        total_tx = cursor.fetchone()['total']

    return render_template('dashboard.html', user=user, recent_transactions=recent_transactions, total_tx=total_tx)


@app.route('/account-details')
@app.route('/account_details.html')
@login_required
def account_details():
    user = get_current_user()
    return render_template('account_details.html', user=user)


@app.route('/deposit', methods=['GET', 'POST'])
@app.route('/deposit.html', methods=['GET', 'POST'])
@login_required
def deposit():
    user = get_current_user()
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount', '0') or '0')
        except ValueError:
            amount = 0

        if amount <= 0:
            flash('Enter a valid amount above zero.', 'danger')
            return redirect(url_for('deposit'))

        connection = db_connect()
        if is_duplicate_transaction(connection, user['id'], 'Deposit', amount):
            flash('Duplicate transaction detected. Please wait a few moments before retrying.', 'warning')
            return redirect(url_for('dashboard'))

        with connection:
            new_balance = user['balance'] + amount
            cursor = connection.cursor()
            cursor.execute('UPDATE users SET balance = ? WHERE id = ?', (new_balance, user['id']))
            record_transaction(connection, user['id'], 'Deposit', amount, new_balance, 'Deposit to account')
            connection.commit()

        send_notification_email(
            user['email'],
            'Deposit Successful',
            f'Your deposit of ₹{amount:.2f} was successful. Current balance: ₹{new_balance:.2f}.'
        )
        flash(f'Deposit successful. Current balance is ₹{new_balance:.2f}.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('deposit.html', user=user)


@app.route('/withdraw', methods=['GET', 'POST'])
@app.route('/withdraw.html', methods=['GET', 'POST'])
@login_required
def withdraw():
    user = get_current_user()
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount', '0') or '0')
        except ValueError:
            amount = 0

        if amount <= 0:
            flash('Enter a valid amount above zero.', 'danger')
            return redirect(url_for('withdraw'))
        elif amount > user['balance']:
            flash('Insufficient balance for this withdrawal.', 'danger')
            return redirect(url_for('withdraw'))

        connection = db_connect()
        if is_duplicate_transaction(connection, user['id'], 'Withdrawal', amount):
            flash('Duplicate transaction detected. Please wait a few moments before retrying.', 'warning')
            return redirect(url_for('dashboard'))

        with connection:
            new_balance = user['balance'] - amount
            cursor = connection.cursor()
            cursor.execute('UPDATE users SET balance = ? WHERE id = ?', (new_balance, user['id']))
            record_transaction(connection, user['id'], 'Withdrawal', amount, new_balance, 'Withdrawal from account')
            connection.commit()

        send_notification_email(
            user['email'],
            'Withdrawal Successful',
            f'Your withdrawal of ₹{amount:.2f} was successful. Remaining balance: ₹{new_balance:.2f}.'
        )
        flash(f'Withdrawal successful. Remaining balance is ₹{new_balance:.2f}.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('withdraw.html', user=user)


@app.route('/transfer', methods=['GET', 'POST'])
@app.route('/transfer.html', methods=['GET', 'POST'])
@login_required
def transfer():
    user = get_current_user()
    if request.method == 'POST':
        recipient_account = request.form.get('recipient_account', '').strip()
        try:
            amount = float(request.form.get('amount', '0') or '0')
        except ValueError:
            amount = 0
        notes = request.form.get('notes', '').strip()
        extra_note = f" - {notes}" if notes else ""

        if not recipient_account or amount <= 0:
            flash('Please provide recipient account number and a valid amount.', 'danger')
        elif recipient_account == user['account_number']:
            flash('You cannot transfer to your own account.', 'danger')
        elif amount > user['balance']:
            flash('Insufficient balance for this transfer.', 'danger')
        else:
            connection = db_connect()
            if is_duplicate_transaction(connection, user['id'], 'Transfer Out', amount):
                flash('Duplicate transfer detected. Please wait a few seconds.', 'warning')
                return redirect(url_for('dashboard'))

            with connection:
                cursor = connection.cursor()
                cursor.execute('SELECT id, name, email, balance FROM users WHERE account_number = ?', (recipient_account,))
                recipient = cursor.fetchone()

                if not recipient:
                    flash('Recipient account not found.', 'danger')
                else:
                    new_sender_balance = user['balance'] - amount
                    new_recipient_balance = recipient['balance'] + amount

                    cursor.execute('UPDATE users SET balance = ? WHERE id = ?', (new_sender_balance, user['id']))
                    cursor.execute('UPDATE users SET balance = ? WHERE id = ?', (new_recipient_balance, recipient['id']))

                    record_transaction(
                        connection, user['id'], 'Transfer Out', amount, new_sender_balance,
                        f'Transfer to {recipient["name"]} ({recipient_account}){extra_note}'
                    )
                    record_transaction(
                        connection, recipient['id'], 'Transfer In', amount, new_recipient_balance,
                        f'Transfer from {user["name"]} ({user["account_number"]}){extra_note}'
                    )
                    connection.commit()

                    send_notification_email(
                        user['email'], 'Transfer Successful',
                        f'₹{amount:.2f} was transferred to account {recipient_account}. Your new balance is ₹{new_sender_balance:.2f}.'
                    )
                    flash(f'Transfer successful. ₹{amount:.2f} sent to {recipient["name"]}.', 'success')
                    return redirect(url_for('dashboard'))

    return render_template('transfer.html', user=user)


@app.route('/transactions')
@app.route('/transactions.html')
@login_required
def transactions():
    user = get_current_user()
    tx_type = request.args.get('type', '').strip()
    search = request.args.get('search', '').strip()

    query = 'SELECT * FROM transactions WHERE user_id = ?'
    params = [user['id']]

    if tx_type and tx_type != 'All Types':
        query += ' AND type = ?'
        params.append(tx_type)

    if search:
        query += ' AND (details LIKE ? OR type LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])

    query += ' ORDER BY created_at DESC'

    connection = db_connect()
    with connection:
        cursor = connection.cursor()
        cursor.execute(query, params)
        transactions_list = cursor.fetchall()

    return render_template('transactions.html', user=user, transactions=transactions_list, filter_type=tx_type, search=search)


@app.route('/download-statement')
@login_required
def download_statement():
    user = get_current_user()
    connection = db_connect()
    with connection:
        cursor = connection.cursor()
        cursor.execute(
            'SELECT created_at, type, amount, balance, details FROM transactions WHERE user_id = ? ORDER BY created_at DESC',
            (user['id'],)
        )
        txs = cursor.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Type', 'Amount (INR)', 'Balance (INR)', 'Details'])
    for tx in txs:
        writer.writerow([tx['created_at'], tx['type'], f"{tx['amount']:.2f}", f"{tx['balance']:.2f}", tx['details']])

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=Statement_{user["account_number"]}.csv'}
    )


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
