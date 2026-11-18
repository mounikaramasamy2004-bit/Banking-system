"""
Console-based Simple Banking System using dictionaries, loops, functions, and
conditional statements as described in Chapters 1 to 4 of the report.
"""
import random
from datetime import datetime

accounts = {}

def create_account():
    print("\n--- Create Account ---")
    name = input("Enter customer name: ").strip()
    try:
        initial_deposit = float(input("Enter initial deposit (₹): "))
        if initial_deposit < 0:
            print("Initial deposit cannot be negative.")
            return
    except ValueError:
        print("Invalid deposit amount.")
        return

    acc_num = str(random.randint(100000000000, 999999999999))
    accounts[acc_num] = {
        "name": name,
        "balance": initial_deposit,
        "transactions": [
            {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "type": "Initial Deposit",
                "amount": initial_deposit,
                "balance": initial_deposit,
                "details": "Account opened"
            }
        ]
    }
    print(f"Account created successfully!")
    print(f"Customer: {name} | Account Number: {acc_num} | Balance: ₹{initial_deposit:.2f}")

def deposit():
    print("\n--- Deposit Funds ---")
    acc_num = input("Enter account number: ").strip()
    if acc_num not in accounts:
        print("Account not found.")
        return

    try:
        amount = float(input("Enter deposit amount (₹): "))
        if amount <= 0:
            print("Deposit amount must be greater than zero.")
            return
    except ValueError:
        print("Invalid amount.")
        return

    accounts[acc_num]["balance"] += amount
    curr_balance = accounts[acc_num]["balance"]
    accounts[acc_num]["transactions"].append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": "Deposit",
        "amount": amount,
        "balance": curr_balance,
        "details": "Deposit to account"
    })
    print(f"₹{amount:.2f} deposited successfully! Current balance: ₹{curr_balance:.2f}")

def withdraw():
    print("\n--- Withdraw Funds ---")
    acc_num = input("Enter account number: ").strip()
    if acc_num not in accounts:
        print("Account not found.")
        return

    try:
        amount = float(input("Enter withdrawal amount (₹): "))
        if amount <= 0:
            print("Withdrawal amount must be greater than zero.")
            return
    except ValueError:
        print("Invalid amount.")
        return

    if amount > accounts[acc_num]["balance"]:
        print("Error: Insufficient balance.")
        return

    accounts[acc_num]["balance"] -= amount
    curr_balance = accounts[acc_num]["balance"]
    accounts[acc_num]["transactions"].append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": "Withdrawal",
        "amount": amount,
        "balance": curr_balance,
        "details": "Withdrawal from account"
    })
    print(f"₹{amount:.2f} withdrawn successfully! Current balance: ₹{curr_balance:.2f}")

def check_balance():
    print("\n--- Balance Inquiry ---")
    acc_num = input("Enter account number: ").strip()
    if acc_num not in accounts:
        print("Account not found.")
        return

    acc = accounts[acc_num]
    print(f"Account Holder: {acc['name']}")
    print(f"Account Number: {acc_num}")
    print(f"Current Balance: ₹{acc['balance']:.2f}")

def print_statement():
    print("\n--- Transaction Statement ---")
    acc_num = input("Enter account number: ").strip()
    if acc_num not in accounts:
        print("Account not found.")
        return

    acc = accounts[acc_num]
    print(f"\nStatement for {acc['name']} ({acc_num})")
    print("-" * 75)
    print(f"{'Date':<20} {'Type':<15} {'Amount':<12} {'Balance':<12} Details")
    print("-" * 75)
    for tx in acc["transactions"]:
        print(f"{tx['date']:<20} {tx['type']:<15} ₹{tx['amount']:<11.2f} ₹{tx['balance']:<11.2f} {tx['details']}")
    print("-" * 75)

def main():
    while True:
        print("\n==========================================")
        print("     SIMPLE BANKING MANAGEMENT SYSTEM     ")
        print("==========================================")
        print("1. Create New Account")
        print("2. Deposit Money")
        print("3. Withdraw Money")
        print("4. Check Balance")
        print("5. View Transaction Statement")
        print("6. Exit")
        choice = input("Enter your choice (1-6): ").strip()

        if choice == '1':
            create_account()
        elif choice == '2':
            deposit()
        elif choice == '3':
            withdraw()
        elif choice == '4':
            check_balance()
        elif choice == '5':
            print_statement()
        elif choice == '6':
            print("Thank you for using Simple Banking System. Goodbye!")
            break
        else:
            print("Invalid option! Please enter a number from 1 to 6.")

if __name__ == '__main__':
    main()
