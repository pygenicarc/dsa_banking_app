"""
Console User Interface (CLI) for the Banking Application.
Provides interactive text menus, formatted tables, masked input, and error handling.
"""

import sys
import os
import getpass
from typing import Optional
from models import Account, AccountType, AccountStatus, Transaction
from bank_service import BankService, MINIMUM_BALANCE

# Terminal styling constants
LINE_WIDTH = 76
BORDER_CHAR = "="
SUB_BORDER_CHAR = "-"

def clear_screen():
    """Clear terminal screen if supported."""
    # Only clear if running in standard interactive terminal
    if sys.stdout.isatty():
        os.system("cls" if os.name == "nt" else "clear")

def print_header(title: str):
    """Print an attractive section header."""
    print()
    print(BORDER_CHAR * LINE_WIDTH)
    print(f" {title.upper()} ".center(LINE_WIDTH, " "))
    print(BORDER_CHAR * LINE_WIDTH)

def print_sub_header(title: str):
    print()
    print(f"-- {title} " + SUB_BORDER_CHAR * max(0, (LINE_WIDTH - len(title) - 4)))

def print_success(message: str):
    print(f"\n[OK] {message}")

def print_error(message: str):
    print(f"\n[ERROR] {message}")

def print_warning(message: str):
    print(f"\n[WARNING] {message}")

def pause():
    """Pause until user presses Enter."""
    print()
    input("Press [Enter] to return...")

def secure_input(prompt: str = "Enter PIN: ") -> str:
    """Read a masked password or PIN with fallback to normal input if no tty."""
    try:
        val = getpass.getpass(prompt)
        if not val and not sys.stdin.isatty():
            # In some IDEs or non-interactive environments getpass returns empty
            val = input(prompt)
        return val
    except Exception:
        return input(prompt)

def prompt_float(prompt: str, min_val: float = 0.01) -> Optional[float]:
    """Prompt user for a positive float amount. Allows typing 'c' to cancel."""
    while True:
        raw = input(f"{prompt} (or 'c' to cancel): ").strip()
        if raw.lower() == "c":
            return None
        try:
            val = float(raw)
            if val < min_val:
                print_error(f"Amount must be at least ${min_val:,.2f}.")
                continue
            return val
        except ValueError:
            print_error("Invalid amount. Please enter a valid numerical value.")

def prompt_str(prompt: str, min_len: int = 1) -> Optional[str]:
    """Prompt user for a non-empty string. Allows typing 'c' to cancel."""
    while True:
        raw = input(f"{prompt} (or 'c' to cancel): ").strip()
        if raw.lower() == "c":
            return None
        if len(raw) < min_len:
            print_error(f"Input must be at least {min_len} character(s).")
            continue
        return raw

def format_transactions_table(transactions: list[Transaction]):
    """Print a formatted tabular statement of transactions."""
    if not transactions:
        print("No transactions found.")
        return

    # Header
    col_date = 19
    col_id = 20
    col_type = 13
    col_amount = 12
    col_bal = 12
    col_desc = 25

    header = (
        f"{'Date & Time':<{col_date}} | "
        f"{'Tx ID':<{col_id}} | "
        f"{'Type':<{col_type}} | "
        f"{'Amount ($)':>{col_amount}} | "
        f"{'Balance ($)':>{col_bal}} | "
        f"{'Description'}"
    )
    sep = "-" * len(header)

    print(sep)
    print(header)
    print(sep)

    for tx in transactions:
        sign = "+" if tx.tx_type in ["DEPOSIT", "TRANSFER_IN"] else "-"
        amt_str = f"{sign}{tx.amount:,.2f}"
        print(
            f"{tx.timestamp:<{col_date}} | "
            f"{tx.transaction_id:<{col_id}} | "
            f"{tx.tx_type:<{col_type}} | "
            f"{amt_str:>{col_amount}} | "
            f"{tx.balance_after:>{col_bal},.2f} | "
            f"{tx.description}"
        )
    print(sep)


class BankingCLI:
    def __init__(self, service: Optional[BankService] = None):
        self.service = service if service is not None else BankService()

    def run(self):
        """Main application loop."""
        while True:
            print_header("Apex Community Bank - Console Portal")
            print("1. Login to Existing Account")
            print("2. Open New Bank Account")
            print("3. Administrator Portal")
            print("4. About & System Information")
            print("5. Exit")
            print(BORDER_CHAR * LINE_WIDTH)

            choice = input("Select an option (1-5): ").strip()

            if choice == "1":
                self.login_flow()
            elif choice == "2":
                self.create_account_flow()
            elif choice == "3":
                self.admin_login_flow()
            elif choice == "4":
                self.show_about()
            elif choice == "5":
                print("\nThank you for choosing Apex Community Bank. Goodbye!")
                break
            else:
                print_error("Invalid option. Please choose between 1 and 5.")

    # ------------------ REGISTRATION ------------------ #

    def create_account_flow(self):
        print_header("New Account Registration")
        print("Note: Type 'c' at any prompt to cancel registration.")

        name = prompt_str("Enter Full Name", min_len=2)
        if name is None:
            return

        email = prompt_str("Enter Email Address", min_len=5)
        if email is None:
            return

        phone = prompt_str("Enter Phone Number", min_len=7)
        if phone is None:
            return

        print_sub_header("Select Account Type")
        print(f"1. SAVINGS (Min. Deposit: ${MINIMUM_BALANCE[AccountType.SAVINGS.value]:,.2f})")
        print(f"2. CURRENT (Min. Deposit: ${MINIMUM_BALANCE[AccountType.CURRENT.value]:,.2f})")
        
        acc_type_choice = input("Select Account Type (1 or 2): ").strip()
        if acc_type_choice == "1":
            acc_type = AccountType.SAVINGS.value
        elif acc_type_choice == "2":
            acc_type = AccountType.CURRENT.value
        else:
            print_error("Invalid account type selection. Registration cancelled.")
            pause()
            return

        min_deposit = MINIMUM_BALANCE[acc_type]
        print(f"\nMinimum initial deposit for {acc_type} is ${min_deposit:,.2f}.")
        deposit_amount = prompt_float("Enter Initial Deposit Amount", min_val=min_deposit)
        if deposit_amount is None:
            return

        print("\nSetup your 4-6 digit Security PIN.")
        pin = secure_input("Enter 4-6 digit PIN: ").strip()
        pin_confirm = secure_input("Confirm PIN: ").strip()

        if pin != pin_confirm:
            print_error("PINs do not match. Registration cancelled.")
            pause()
            return

        success, msg, account = self.service.create_account(
            name=name,
            email=email,
            phone=phone,
            pin=pin,
            account_type=acc_type,
            initial_deposit=deposit_amount
        )

        if success and account:
            print_success(msg)
            print_sub_header("Your Account Details")
            print(f"Account Number : {account.account_number}")
            print(f"Account Holder : {account.name}")
            print(f"Account Type   : {account.account_type}")
            print(f"Initial Balance: ${account.balance:,.2f}")
            print(f"Status         : {account.status}")
            print("\n[!] IMPORTANT: Keep your Account Number and PIN safe for future logins.")
        else:
            print_error(msg)

        pause()

    # ------------------ LOGIN & DASHBOARD ------------------ #

    def login_flow(self):
        print_header("Account Login")
        acc_num = input("Enter Account Number (or 'c' to cancel): ").strip()
        if acc_num.lower() == "c" or not acc_num:
            return

        pin = secure_input("Enter PIN: ").strip()

        success, msg, account = self.service.authenticate_account(acc_num, pin)
        if not success or not account:
            print_error(msg)
            pause()
            return

        print_success(f"Welcome back, {account.name}!")
        self.account_dashboard(account.account_number)

    def account_dashboard(self, account_number: str):
        """Active session dashboard for an authenticated account."""
        while True:
            # Refresh account from database to display current state
            account = self.service.db.get_account(account_number)
            if not account or account.status != AccountStatus.ACTIVE.value:
                print_warning("Account is no longer active or has been logged out.")
                pause()
                break

            print_header(f"Dashboard - {account.name} (Acc #{account.account_number})")
            print(f"Account Type : {account.account_type:<10} | Balance: ${account.balance:,.2f} | Status: {account.status}")
            print(SUB_BORDER_CHAR * LINE_WIDTH)
            print("1. View Profile & Balance")
            print("2. Deposit Money")
            print("3. Withdraw Money")
            print("4. Transfer Funds")
            print("5. Mini Statement (Recent 5 Transactions)")
            print("6. Full Transaction Statement")
            print("7. Change Security PIN")
            print("8. Update Contact Information")
            print("9. Close Account")
            print("10. Logout")
            print(BORDER_CHAR * LINE_WIDTH)

            choice = input("Select an option (1-10): ").strip()

            if choice == "1":
                self.show_account_profile(account)
            elif choice == "2":
                self.deposit_flow(account)
            elif choice == "3":
                self.withdraw_flow(account)
            elif choice == "4":
                self.transfer_flow(account)
            elif choice == "5":
                self.statement_flow(account, limit=5)
            elif choice == "6":
                self.statement_flow(account, limit=None)
            elif choice == "7":
                self.change_pin_flow(account)
            elif choice == "8":
                self.update_profile_flow(account)
            elif choice == "9":
                closed = self.close_account_flow(account)
                if closed:
                    break
            elif choice == "10":
                print("\nYou have been safely logged out.")
                break
            else:
                print_error("Invalid option. Please choose between 1 and 10.")

    def show_account_profile(self, account: Account):
        print_header("Account Profile")
        print(f"Account Number  : {account.account_number}")
        print(f"Account Holder  : {account.name}")
        print(f"Account Type    : {account.account_type}")
        print(f"Current Balance : ${account.balance:,.2f}")
        print(f"Email Address   : {account.email}")
        print(f"Phone Number    : {account.phone}")
        print(f"Account Status  : {account.status}")
        print(f"Account Created : {account.created_at}")
        pause()

    def deposit_flow(self, account: Account):
        print_header("Deposit Funds")
        amount = prompt_float("Enter amount to deposit")
        if amount is None:
            return

        desc = input("Enter description/memo (press Enter for 'Cash Deposit'): ").strip()
        if not desc:
            desc = "Cash Deposit"

        success, msg, new_bal = self.service.deposit(account.account_number, amount, desc)
        if success:
            print_success(msg)
        else:
            print_error(msg)
        pause()

    def withdraw_flow(self, account: Account):
        print_header("Withdraw Funds")
        min_bal = MINIMUM_BALANCE.get(account.account_type, 0.0)
        max_withdrawable = max(0.0, account.balance - min_bal)
        print(f"Current Balance: ${account.balance:,.2f}")
        print(f"Required Minimum Balance: ${min_bal:,.2f}")
        print(f"Maximum Withdrawable Amount: ${max_withdrawable:,.2f}")

        amount = prompt_float("Enter amount to withdraw")
        if amount is None:
            return

        desc = input("Enter description/memo (press Enter for 'Cash Withdrawal'): ").strip()
        if not desc:
            desc = "Cash Withdrawal"

        success, msg, new_bal = self.service.withdraw(account.account_number, amount, desc)
        if success:
            print_success(msg)
        else:
            print_error(msg)
        pause()

    def transfer_flow(self, account: Account):
        print_header("Transfer Funds")
        min_bal = MINIMUM_BALANCE.get(account.account_type, 0.0)
        max_transferable = max(0.0, account.balance - min_bal)
        print(f"Available for Transfer: ${max_transferable:,.2f}")

        target_acc = prompt_str("Enter Recipient 10-digit Account Number")
        if target_acc is None:
            return

        if target_acc == account.account_number:
            print_error("You cannot transfer money to your own account.")
            pause()
            return

        # Preview recipient name
        recipient = self.service.db.get_account(target_acc)
        if not recipient:
            print_error(f"Recipient Account #{target_acc} does not exist.")
            pause()
            return

        if recipient.status != AccountStatus.ACTIVE.value:
            print_error(f"Recipient Account #{target_acc} is currently {recipient.status}. Cannot receive transfers.")
            pause()
            return

        print(f"Recipient Found: {recipient.name} (Acc #{recipient.account_number})")

        amount = prompt_float("Enter Transfer Amount")
        if amount is None:
            return

        note = input("Add a transfer note (optional): ").strip()

        # Confirmation
        confirm = input(f"Confirm transfer of ${amount:,.2f} to {recipient.name}? (y/n): ").strip().lower()
        if confirm != "y":
            print_warning("Transfer cancelled by user.")
            pause()
            return

        success, msg = self.service.transfer(account.account_number, target_acc, amount, note)
        if success:
            print_success(msg)
        else:
            print_error(msg)
        pause()

    def statement_flow(self, account: Account, limit: Optional[int] = None):
        title = f"Mini Statement (Last {limit} Transactions)" if limit else "Full Account Statement"
        print_header(title)
        print(f"Account: {account.name} | Acc #{account.account_number} | Current Balance: ${account.balance:,.2f}")
        print()
        txs = self.service.get_statement(account.account_number, limit=limit)
        format_transactions_table(txs)
        pause()

    def change_pin_flow(self, account: Account):
        print_header("Change Security PIN")
        old_pin = secure_input("Enter Current PIN: ").strip()
        new_pin = secure_input("Enter New 4-6 digit PIN: ").strip()
        confirm_pin = secure_input("Confirm New PIN: ").strip()

        if new_pin != confirm_pin:
            print_error("New PINs do not match.")
            pause()
            return

        success, msg = self.service.change_pin(account.account_number, old_pin, new_pin)
        if success:
            print_success(msg)
        else:
            print_error(msg)
        pause()

    def update_profile_flow(self, account: Account):
        print_header("Update Contact Information")
        print(f"Current Email : {account.email}")
        print(f"Current Phone : {account.phone}")
        print("\n(Leave blank to keep existing value)")

        new_email = input("New Email Address: ").strip() or None
        new_phone = input("New Phone Number: ").strip() or None

        if not new_email and not new_phone:
            print_warning("No changes entered.")
            pause()
            return

        success, msg = self.service.update_profile(account.account_number, email=new_email, phone=new_phone)
        if success:
            print_success(msg)
        else:
            print_error(msg)
        pause()

    def close_account_flow(self, account: Account) -> bool:
        print_header("Close Account")
        print_warning("CAUTION: Closing your account is permanent.")
        print(f"Current Balance: ${account.balance:,.2f}")

        if account.balance > 0:
            print_error("Your balance must be exactly $0.00 before closing. Please withdraw or transfer all funds first.")
            pause()
            return False

        confirm = input("Are you absolutely sure you want to close this account? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("Account closure cancelled.")
            pause()
            return False

        pin = secure_input("Enter your PIN to confirm closure: ").strip()
        success, msg = self.service.close_account(account.account_number, pin)
        if success:
            print_success(msg)
            pause()
            return True
        else:
            print_error(msg)
            pause()
            return False

    # ------------------ ADMIN PORTAL ------------------ #

    def admin_login_flow(self):
        print_header("Bank Administration Portal")
        username = input("Enter Admin Username (or 'c' to cancel): ").strip()
        if username.lower() == "c" or not username:
            return

        password = secure_input("Enter Admin Password: ").strip()

        if not self.service.admin_authenticate(username, password):
            print_error("Invalid administrative credentials.")
            pause()
            return

        print_success(f"Administrative access granted. Welcome, {username}!")
        self.admin_dashboard()

    def admin_dashboard(self):
        while True:
            print_header("Administrator Control Center")
            print("1. Bank Overview & Total Deposit Summary")
            print("2. List All Customer Accounts")
            print("3. Search Account by Number or Name")
            print("4. Freeze or Unfreeze Customer Account")
            print("5. View Global Transaction Log")
            print("6. Return to Main Menu")
            print(BORDER_CHAR * LINE_WIDTH)

            choice = input("Select an option (1-6): ").strip()

            if choice == "1":
                self.admin_show_summary()
            elif choice == "2":
                self.admin_list_accounts()
            elif choice == "3":
                self.admin_search_accounts()
            elif choice == "4":
                self.admin_freeze_unfreeze()
            elif choice == "5":
                self.admin_view_global_transactions()
            elif choice == "6":
                break
            else:
                print_error("Invalid option. Please choose between 1 and 6.")

    def admin_show_summary(self):
        print_header("Bank Institutional Summary")
        summary = self.service.get_bank_summary()
        print(f"Total Registered Accounts : {summary['total_accounts']}")
        print(f"  - Active Accounts       : {summary['active_accounts']}")
        print(f"  - Frozen Accounts       : {summary['frozen_accounts']}")
        print(f"  - Closed Accounts       : {summary['closed_accounts']}")
        print(f"Total Customer Deposits   : ${summary['total_deposits']:,.2f}")
        print(f"Total System Transactions : {summary['total_transactions']}")
        pause()

    def admin_list_accounts(self):
        print_header("All Customer Accounts")
        accounts = self.service.get_all_accounts()
        if not accounts:
            print("No accounts found in database.")
            pause()
            return

        print(f"{'Acc Number':<12} | {'Name':<20} | {'Type':<8} | {'Balance ($)':>12} | {'Status':<8} | {'Phone'}")
        print("-" * LINE_WIDTH)
        for acc in accounts:
            print(f"{acc.account_number:<12} | {acc.name:<20} | {acc.account_type:<8} | {acc.balance:>12,.2f} | {acc.status:<8} | {acc.phone}")
        print("-" * LINE_WIDTH)
        pause()

    def admin_search_accounts(self):
        print_header("Search Accounts")
        term = input("Enter Account Number or Customer Name: ").strip().lower()
        if not term:
            return

        accounts = self.service.get_all_accounts()
        matches = [a for a in accounts if term in a.account_number.lower() or term in a.name.lower()]

        if not matches:
            print_warning(f"No accounts found matching '{term}'.")
        else:
            print_success(f"Found {len(matches)} matching account(s):")
            print(f"{'Acc Number':<12} | {'Name':<20} | {'Type':<8} | {'Balance ($)':>12} | {'Status':<8} | {'Email'}")
            print("-" * LINE_WIDTH)
            for acc in matches:
                print(f"{acc.account_number:<12} | {acc.name:<20} | {acc.account_type:<8} | {acc.balance:>12,.2f} | {acc.status:<8} | {acc.email}")
            print("-" * LINE_WIDTH)
        pause()

    def admin_freeze_unfreeze(self):
        print_header("Freeze / Unfreeze Account")
        acc_num = input("Enter Account Number to modify: ").strip()
        account = self.service.db.get_account(acc_num)
        if not account:
            print_error("Account not found.")
            pause()
            return

        print(f"Account: {account.name} (Acc #{account.account_number})")
        print(f"Current Status: {account.status}")
        print("\nChoose new status:")
        print("1. Set to ACTIVE (Unfreeze)")
        print("2. Set to FROZEN (Freeze)")
        print("3. Set to CLOSED")
        print("4. Cancel")

        choice = input("Select option (1-4): ").strip()
        status_map = {
            "1": AccountStatus.ACTIVE.value,
            "2": AccountStatus.FROZEN.value,
            "3": AccountStatus.CLOSED.value,
        }

        if choice in status_map:
            new_status = status_map[choice]
            success, msg = self.service.toggle_account_status(acc_num, new_status)
            if success:
                print_success(msg)
            else:
                print_error(msg)
        else:
            print("Operation cancelled.")
        pause()

    def admin_view_global_transactions(self):
        print_header("Global Transaction Log (All Accounts)")
        limit_str = input("Enter number of recent transactions to view (press Enter for all): ").strip()
        limit = None
        if limit_str.isdigit():
            limit = int(limit_str)

        txs = self.service.db.load_transactions()
        txs.reverse()
        if limit:
            txs = txs[:limit]

        format_transactions_table(txs)
        pause()

    # ------------------ ABOUT ------------------ #

    def show_about(self):
        print_header("About Apex Banking System")
        print("Apex Banking System is a robust, standalone Console-Based Banking Application.")
        print()
        print("Key Features:")
        print("  - Zero external web frameworks (No Flask/Django/FastAPI needed)")
        print("  - Standard Library CSV persistence (Compatible with Microsoft Excel / Google Sheets)")
        print("  - Cryptographically salted PIN hashing (PBKDF2-HMAC-SHA256)")
        print("  - Savings & Current account support with minimum balance rules")
        print("  - Inter-account fund transfers with double-entry transaction auditing")
        print("  - Account security features (auto-freeze on 3 failed login attempts)")
        print("  - Comprehensive Admin Portal with institutional summaries and account moderation")
        print()
        print("Default Admin Credentials:")
        print("  Username : admin")
        print("  Password : admin123")
        print()
        print("Database CSV Location: ./data/accounts.csv and ./data/transactions.csv")
        pause()
