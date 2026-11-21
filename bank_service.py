"""
Business logic and service layer for the Banking System.
Encapsulates account operations, transactions, fund transfers, and validations.
"""

from datetime import datetime
import secrets
from typing import Optional

from models import Account, AccountStatus, AccountType, Transaction, TransactionType
from database import CSVDatabase
from security import hash_pin, verify_pin, validate_pin_format

MINIMUM_BALANCE = {
    AccountType.SAVINGS.value: 500.0,
    AccountType.CURRENT.value: 1000.0,
}

ADMIN_CREDENTIALS = {
    "admin": "admin123"
}

class BankService:
    def __init__(self, db: Optional[CSVDatabase] = None):
        self.db = db if db is not None else CSVDatabase()
        # Keep track of consecutive failed login attempts {account_number: count}
        self.failed_attempts: dict[str, int] = {}

    def _generate_account_number(self) -> str:
        """Generate a unique 10-digit account number."""
        accounts = self.db.load_accounts()
        while True:
            # Generate 10-digit number starting with 100
            random_digits = secrets.randbelow(9000000) + 1000000
            acc_num = f"100{random_digits}"
            if acc_num not in accounts:
                return acc_num

    def _generate_transaction_id(self) -> str:
        """Generate a unique transaction identifier."""
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        suffix = secrets.token_hex(3).upper()
        return f"TXN{ts}{suffix}"

    # ------------------ ACCOUNT MANAGEMENT ------------------ #

    def create_account(
        self,
        name: str,
        email: str,
        phone: str,
        pin: str,
        account_type: str,
        initial_deposit: float
    ) -> tuple[bool, str, Optional[Account]]:
        """
        Create a new bank account with an initial deposit.
        Returns (success: bool, message: str, account: Optional[Account])
        """
        # Validate inputs
        name = name.strip()
        if not name or len(name) < 2:
            return False, "Full Name must be at least 2 characters.", None

        if "@" not in email or "." not in email:
            return False, "Invalid email address format.", None

        clean_phone = "".join(filter(str.isdigit, phone))
        if len(clean_phone) < 7:
            return False, "Invalid phone number. Must contain at least 7 digits.", None

        is_pin_valid, pin_msg = validate_pin_format(pin)
        if not is_pin_valid:
            return False, pin_msg, None

        acc_type_normalized = account_type.strip().upper()
        if acc_type_normalized not in [AccountType.SAVINGS.value, AccountType.CURRENT.value]:
            return False, f"Invalid account type. Choose '{AccountType.SAVINGS.value}' or '{AccountType.CURRENT.value}'.", None

        min_bal = MINIMUM_BALANCE[acc_type_normalized]
        if initial_deposit < min_bal:
            return False, f"Initial deposit must be at least ${min_bal:,.2f} for {acc_type_normalized} accounts.", None

        # Hash PIN
        pin_hash, salt = hash_pin(pin)
        acc_num = self._generate_account_number()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        account = Account(
            account_number=acc_num,
            name=name,
            email=email.strip().lower(),
            phone=phone.strip(),
            pin_hash=pin_hash,
            pin_salt=salt,
            account_type=acc_type_normalized,
            balance=initial_deposit,
            status=AccountStatus.ACTIVE.value,
            created_at=now_str
        )

        self.db.save_account(account)

        # Log initial deposit transaction
        tx = Transaction(
            transaction_id=self._generate_transaction_id(),
            timestamp=now_str,
            account_number=acc_num,
            tx_type=TransactionType.DEPOSIT.value,
            amount=initial_deposit,
            balance_after=initial_deposit,
            description="Initial Account Opening Deposit"
        )
        self.db.log_transaction(tx)

        return True, "Account created successfully!", account

    def authenticate_account(self, account_number: str, pin: str) -> tuple[bool, str, Optional[Account]]:
        """
        Authenticate an account with account number and PIN.
        Auto-freezes account if 3 consecutive failed attempts occur.
        """
        account = self.db.get_account(account_number)
        if not account:
            return False, "Account number not found.", None

        if account.status == AccountStatus.CLOSED.value:
            return False, "This account is closed. Please contact customer support.", None

        if account.status == AccountStatus.FROZEN.value:
            return False, "This account has been frozen for security. Please contact bank admin.", None

        if not verify_pin(pin, account.pin_hash, account.pin_salt):
            attempts = self.failed_attempts.get(account_number, 0) + 1
            self.failed_attempts[account_number] = attempts

            if attempts >= 3:
                account.status = AccountStatus.FROZEN.value
                self.db.save_account(account)
                self.failed_attempts[account_number] = 0
                return False, "3 consecutive incorrect PIN entries. Your account has been FROZEN for security.", None

            remaining = 3 - attempts
            return False, f"Incorrect PIN. {remaining} attempt(s) remaining before account is frozen.", None

        # Reset failed attempts upon successful login
        self.failed_attempts[account_number] = 0
        return True, "Authentication successful.", account

    # ------------------ FINANCIAL TRANSACTIONS ------------------ #

    def deposit(self, account_number: str, amount: float, description: str = "Cash Deposit") -> tuple[bool, str, float]:
        """
        Deposit funds into an account.
        Returns (success: bool, message: str, new_balance: float)
        """
        if amount <= 0:
            return False, "Deposit amount must be greater than 0.", 0.0

        account = self.db.get_account(account_number)
        if not account:
            return False, "Account not found.", 0.0

        if account.status != AccountStatus.ACTIVE.value:
            return False, f"Account is {account.status}. Cannot perform deposit.", account.balance

        account.balance += amount
        self.db.save_account(account)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tx = Transaction(
            transaction_id=self._generate_transaction_id(),
            timestamp=now_str,
            account_number=account_number,
            tx_type=TransactionType.DEPOSIT.value,
            amount=amount,
            balance_after=account.balance,
            description=description
        )
        self.db.log_transaction(tx)

        return True, f"Successfully deposited ${amount:,.2f}. Current balance: ${account.balance:,.2f}", account.balance

    def withdraw(self, account_number: str, amount: float, description: str = "Cash Withdrawal") -> tuple[bool, str, float]:
        """
        Withdraw funds from an account while respecting minimum balance rules.
        Returns (success: bool, message: str, new_balance: float)
        """
        if amount <= 0:
            return False, "Withdrawal amount must be greater than 0.", 0.0

        account = self.db.get_account(account_number)
        if not account:
            return False, "Account not found.", 0.0

        if account.status != AccountStatus.ACTIVE.value:
            return False, f"Account is {account.status}. Cannot perform withdrawal.", account.balance

        min_bal = MINIMUM_BALANCE.get(account.account_type, 0.0)
        if account.balance - amount < min_bal:
            max_allowed = max(0.0, account.balance - min_bal)
            return False, (
                f"Insufficient funds. Maintaining minimum balance of ${min_bal:,.2f} is required for {account.account_type} accounts. "
                f"Maximum you can withdraw right now: ${max_allowed:,.2f}"
            ), account.balance

        account.balance -= amount
        self.db.save_account(account)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tx = Transaction(
            transaction_id=self._generate_transaction_id(),
            timestamp=now_str,
            account_number=account_number,
            tx_type=TransactionType.WITHDRAWAL.value,
            amount=amount,
            balance_after=account.balance,
            description=description
        )
        self.db.log_transaction(tx)

        return True, f"Successfully withdrew ${amount:,.2f}. Current balance: ${account.balance:,.2f}", account.balance

    def transfer(self, sender_acc_num: str, receiver_acc_num: str, amount: float, note: str = "") -> tuple[bool, str]:
        """
        Transfer funds from sender to receiver.
        Ensures atomic balance updates and logs paired transactions.
        """
        if sender_acc_num == receiver_acc_num:
            return False, "Cannot transfer funds to the same account."

        if amount <= 0:
            return False, "Transfer amount must be greater than 0."

        accounts = self.db.load_accounts()
        sender = accounts.get(sender_acc_num)
        receiver = accounts.get(receiver_acc_num)

        if not sender:
            return False, "Sender account not found."
        if not receiver:
            return False, f"Receiver account '{receiver_acc_num}' not found."

        if sender.status != AccountStatus.ACTIVE.value:
            return False, f"Sender account is {sender.status}. Transaction cancelled."
        if receiver.status != AccountStatus.ACTIVE.value:
            return False, f"Receiver account is {receiver.status}. Transaction cancelled."

        min_bal = MINIMUM_BALANCE.get(sender.account_type, 0.0)
        if sender.balance - amount < min_bal:
            max_allowed = max(0.0, sender.balance - min_bal)
            return False, (
                f"Insufficient funds. Maintaining minimum balance of ${min_bal:,.2f} is required. "
                f"Maximum you can transfer: ${max_allowed:,.2f}"
            )

        # Atomic execution on accounts dictionary
        sender.balance -= amount
        receiver.balance += amount
        self.db.save_all_accounts(accounts)

        # Log paired transactions
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        note_str = f" - Note: {note}" if note else ""

        tx_out = Transaction(
            transaction_id=self._generate_transaction_id(),
            timestamp=now_str,
            account_number=sender_acc_num,
            tx_type=TransactionType.TRANSFER_OUT.value,
            amount=amount,
            balance_after=sender.balance,
            description=f"Transfer to Acc #{receiver_acc_num} ({receiver.name}){note_str}"
        )
        tx_in = Transaction(
            transaction_id=self._generate_transaction_id(),
            timestamp=now_str,
            account_number=receiver_acc_num,
            tx_type=TransactionType.TRANSFER_IN.value,
            amount=amount,
            balance_after=receiver.balance,
            description=f"Transfer from Acc #{sender_acc_num} ({sender.name}){note_str}"
        )

        self.db.log_transaction(tx_out)
        self.db.log_transaction(tx_in)

        return True, f"Successfully transferred ${amount:,.2f} to {receiver.name} (Acc #{receiver_acc_num})."

    # ------------------ PROFILE & SECURITY ------------------ #

    def change_pin(self, account_number: str, old_pin: str, new_pin: str) -> tuple[bool, str]:
        """Change account PIN after verifying old PIN."""
        account = self.db.get_account(account_number)
        if not account:
            return False, "Account not found."

        if not verify_pin(old_pin, account.pin_hash, account.pin_salt):
            return False, "Current PIN is incorrect."

        is_valid, msg = validate_pin_format(new_pin)
        if not is_valid:
            return False, msg

        if old_pin == new_pin:
            return False, "New PIN cannot be the same as the current PIN."

        new_hash, new_salt = hash_pin(new_pin)
        account.pin_hash = new_hash
        account.pin_salt = new_salt
        self.db.save_account(account)

        return True, "PIN updated successfully!"

    def update_profile(
        self,
        account_number: str,
        email: Optional[str] = None,
        phone: Optional[str] = None
    ) -> tuple[bool, str]:
        """Update contact information for an account."""
        account = self.db.get_account(account_number)
        if not account:
            return False, "Account not found."

        updated = False
        if email:
            email = email.strip().lower()
            if "@" not in email or "." not in email:
                return False, "Invalid email address format."
            account.email = email
            updated = True

        if phone:
            clean_phone = "".join(filter(str.isdigit, phone))
            if len(clean_phone) < 7:
                return False, "Invalid phone number."
            account.phone = phone.strip()
            updated = True

        if updated:
            self.db.save_account(account)
            return True, "Profile updated successfully."
        return False, "No changes provided."

    def close_account(self, account_number: str, pin: str) -> tuple[bool, str]:
        """Close an account. Account must be active and balance must be fully withdrawn or transferred."""
        account = self.db.get_account(account_number)
        if not account:
            return False, "Account not found."

        if not verify_pin(pin, account.pin_hash, account.pin_salt):
            return False, "Incorrect PIN. Cannot close account."

        if account.balance > 0:
            return False, f"Account balance must be $0.00 before closing. Current balance: ${account.balance:,.2f}. Please withdraw all funds first."

        account.status = AccountStatus.CLOSED.value
        self.db.save_account(account)
        return True, "Account closed successfully."

    # ------------------ STATEMENTS & INQUIRIES ------------------ #

    def get_statement(self, account_number: str, limit: Optional[int] = None) -> list[Transaction]:
        """Retrieve transaction history for an account, sorted newest first."""
        txs = self.db.load_transactions(account_number)
        # Sort in reverse chronological order
        txs.reverse()
        if limit is not None and limit > 0:
            return txs[:limit]
        return txs

    # ------------------ ADMIN OPERATIONS ------------------ #

    def admin_authenticate(self, username: str, pin_or_pass: str) -> bool:
        """Verify administrator credentials."""
        expected = ADMIN_CREDENTIALS.get(username.strip())
        return expected is not None and expected == pin_or_pass

    def get_all_accounts(self) -> list[Account]:
        """Retrieve all registered accounts (admin view)."""
        accounts = self.db.load_accounts()
        return list(accounts.values())

    def toggle_account_status(self, account_number: str, new_status: str) -> tuple[bool, str]:
        """Freeze, Unfreeze, or Close an account (admin operation)."""
        account = self.db.get_account(account_number)
        if not account:
            return False, "Account not found."

        status_norm = new_status.strip().upper()
        if status_norm not in [AccountStatus.ACTIVE.value, AccountStatus.FROZEN.value, AccountStatus.CLOSED.value]:
            return False, "Invalid status choice."

        account.status = status_norm
        self.db.save_account(account)
        return True, f"Account #{account_number} status changed to {status_norm}."

    def get_bank_summary(self) -> dict:
        """Get summary statistics across the whole banking institution."""
        accounts = list(self.db.load_accounts().values())
        transactions = self.db.load_transactions()

        total_balance = sum(acc.balance for acc in accounts)
        active_count = sum(1 for acc in accounts if acc.status == AccountStatus.ACTIVE.value)
        frozen_count = sum(1 for acc in accounts if acc.status == AccountStatus.FROZEN.value)
        closed_count = sum(1 for acc in accounts if acc.status == AccountStatus.CLOSED.value)

        return {
            "total_accounts": len(accounts),
            "active_accounts": active_count,
            "frozen_accounts": frozen_count,
            "closed_accounts": closed_count,
            "total_deposits": total_balance,
            "total_transactions": len(transactions)
        }
