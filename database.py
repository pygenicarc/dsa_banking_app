"""
Database layer using CSV files for data persistence.
CSV files are fully compatible with Microsoft Excel, Google Sheets, and standard spreadsheet software.
"""

import os
import csv
import tempfile
from typing import Optional
from models import Account, Transaction

DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ACCOUNTS_FILENAME = "accounts.csv"
TRANSACTIONS_FILENAME = "transactions.csv"

ACCOUNT_HEADERS = [
    "account_number",
    "name",
    "email",
    "phone",
    "pin_hash",
    "pin_salt",
    "account_type",
    "balance",
    "status",
    "created_at"
]

TRANSACTION_HEADERS = [
    "transaction_id",
    "timestamp",
    "account_number",
    "tx_type",
    "amount",
    "balance_after",
    "description"
]

class CSVDatabase:
    def __init__(self, data_dir: str = DEFAULT_DATA_DIR):
        self.data_dir = data_dir
        self.accounts_file = os.path.join(self.data_dir, ACCOUNTS_FILENAME)
        self.transactions_file = os.path.join(self.data_dir, TRANSACTIONS_FILENAME)
        self._ensure_storage_initialized()

    def _ensure_storage_initialized(self) -> None:
        """Create data directory and initialize CSV files with headers if they do not exist."""
        os.makedirs(self.data_dir, exist_ok=True)

        if not os.path.exists(self.accounts_file):
            with open(self.accounts_file, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(ACCOUNT_HEADERS)

        if not os.path.exists(self.transactions_file):
            with open(self.transactions_file, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(TRANSACTION_HEADERS)

    # ------------------ ACCOUNTS ------------------ #

    def load_accounts(self) -> dict[str, Account]:
        """Load all accounts from accounts.csv into a dictionary keyed by account_number."""
        accounts = {}
        if not os.path.exists(self.accounts_file):
            return accounts

        with open(self.accounts_file, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row and row.get("account_number"):
                    acc = Account.from_dict(row)
                    accounts[acc.account_number] = acc
        return accounts

    def get_account(self, account_number: str) -> Optional[Account]:
        """Fetch a single account by its account number."""
        accounts = self.load_accounts()
        return accounts.get(str(account_number))

    def save_account(self, account: Account) -> None:
        """Insert or update a single account."""
        accounts = self.load_accounts()
        accounts[account.account_number] = account
        self.save_all_accounts(accounts)

    def save_all_accounts(self, accounts: dict[str, Account]) -> None:
        """Safely write all accounts to accounts.csv using an atomic temporary file."""
        dir_name = os.path.dirname(self.accounts_file)
        with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, newline="", encoding="utf-8") as tf:
            writer = csv.DictWriter(tf, fieldnames=ACCOUNT_HEADERS)
            writer.writeheader()
            for acc in accounts.values():
                writer.writerow(acc.to_dict())
            temp_name = tf.name

        # Atomically replace existing accounts file
        os.replace(temp_name, self.accounts_file)

    # ------------------ TRANSACTIONS ------------------ #

    def log_transaction(self, tx: Transaction) -> None:
        """Append a transaction record to transactions.csv."""
        with open(self.transactions_file, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=TRANSACTION_HEADERS)
            writer.writerow(tx.to_dict())

    def load_transactions(self, account_number: Optional[str] = None) -> list[Transaction]:
        """
        Load all transactions, optionally filtering for a specific account.
        Returns transactions sorted by timestamp (chronological).
        """
        transactions = []
        if not os.path.exists(self.transactions_file):
            return transactions

        with open(self.transactions_file, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row and row.get("transaction_id"):
                    tx = Transaction.from_dict(row)
                    if account_number is None or tx.account_number == str(account_number):
                        transactions.append(tx)

        return transactions
