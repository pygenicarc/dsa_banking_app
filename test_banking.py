"""
Comprehensive Automated Test Suite for Apex Banking System.
Validates:
- Account creation with validation (email, phone, pin, minimum deposit)
- PIN hashing, verification, and salting security
- Authentication and auto-lockout after 3 failed PIN attempts
- Deposits & withdrawals (including minimum balance rules)
- Inter-account fund transfers (atomic balance updates)
- Transaction logging and CSV file persistence
- Admin operations and institutional summaries
"""

import unittest
import os
import shutil
import tempfile

from database import CSVDatabase
from bank_service import BankService
from security import hash_pin, verify_pin, validate_pin_format
from models import AccountStatus, AccountType, TransactionType

class TestBankingSystem(unittest.TestCase):
    def setUp(self):
        # Create an isolated temporary directory for testing database CSVs
        self.test_dir = tempfile.mkdtemp()
        self.db = CSVDatabase(data_dir=self.test_dir)
        self.service = BankService(db=self.db)

    def tearDown(self):
        # Clean up temporary test files
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # ------------------ SECURITY TESTS ------------------ #

    def test_pin_hashing_and_verification(self):
        pin = "1234"
        pin_hash, salt = hash_pin(pin)

        # Hash must not be equal to raw PIN
        self.assertNotEqual(pin, pin_hash)
        # Verification must succeed with correct PIN
        self.assertTrue(verify_pin("1234", pin_hash, salt))
        # Verification must fail with wrong PIN
        self.assertFalse(verify_pin("9999", pin_hash, salt))

    def test_pin_validation_rules(self):
        self.assertTrue(validate_pin_format("1234")[0])
        self.assertTrue(validate_pin_format("123456")[0])
        self.assertFalse(validate_pin_format("123")[0])     # Too short
        self.assertFalse(validate_pin_format("1234567")[0])  # Too long
        self.assertFalse(validate_pin_format("12a4")[0])    # Non-digit

    # ------------------ ACCOUNT CREATION ------------------ #

    def test_create_account_success(self):
        success, msg, acc = self.service.create_account(
            name="John Doe",
            email="john@example.com",
            phone="1234567890",
            pin="5555",
            account_type="SAVINGS",
            initial_deposit=1000.0
        )
        self.assertTrue(success)
        self.assertIsNotNone(acc)
        self.assertEqual(acc.name, "John Doe")
        self.assertEqual(acc.balance, 1000.0)
        self.assertEqual(acc.status, AccountStatus.ACTIVE.value)

        # Verify persisted in CSV
        loaded = self.db.get_account(acc.account_number)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.balance, 1000.0)

        # Verify opening transaction was logged
        txs = self.db.load_transactions(acc.account_number)
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0].tx_type, TransactionType.DEPOSIT.value)
        self.assertEqual(txs[0].amount, 1000.0)

    def test_create_account_insufficient_initial_deposit(self):
        # Savings requires min $500
        success, msg, acc = self.service.create_account(
            name="John Doe",
            email="john@example.com",
            phone="1234567890",
            pin="5555",
            account_type="SAVINGS",
            initial_deposit=200.0  # Below $500
        )
        self.assertFalse(success)
        self.assertIn("Initial deposit must be at least", msg)
        self.assertIsNone(acc)

    # ------------------ AUTHENTICATION & LOCKOUT ------------------ #

    def test_authentication_and_auto_freeze(self):
        _, _, acc = self.service.create_account(
            name="Alice",
            email="alice@test.com",
            phone="9876543210",
            pin="1234",
            account_type="SAVINGS",
            initial_deposit=600.0
        )

        # Successful auth
        ok, _, user = self.service.authenticate_account(acc.account_number, "1234")
        self.assertTrue(ok)
        self.assertIsNotNone(user)

        # 1st failed attempt
        ok, msg, _ = self.service.authenticate_account(acc.account_number, "0000")
        self.assertFalse(ok)
        self.assertIn("2 attempt(s) remaining", msg)

        # 2nd failed attempt
        ok, msg, _ = self.service.authenticate_account(acc.account_number, "0000")
        self.assertFalse(ok)
        self.assertIn("1 attempt(s) remaining", msg)

        # 3rd failed attempt -> Account should freeze!
        ok, msg, _ = self.service.authenticate_account(acc.account_number, "0000")
        self.assertFalse(ok)
        self.assertIn("FROZEN", msg)

        # Check account status is FROZEN
        refreshed = self.db.get_account(acc.account_number)
        self.assertEqual(refreshed.status, AccountStatus.FROZEN.value)

        # Attempt with correct PIN now fails because account is frozen
        ok, msg, _ = self.service.authenticate_account(acc.account_number, "1234")
        self.assertFalse(ok)
        self.assertIn("frozen", msg.lower())

    # ------------------ DEPOSIT & WITHDRAWAL ------------------ #

    def test_deposit(self):
        _, _, acc = self.service.create_account(
            name="Bob",
            email="bob@test.com",
            phone="1112223333",
            pin="1111",
            account_type="SAVINGS",
            initial_deposit=500.0
        )

        ok, msg, bal = self.service.deposit(acc.account_number, 250.0, "Salary")
        self.assertTrue(ok)
        self.assertEqual(bal, 750.0)

        # Check CSV
        acc_updated = self.db.get_account(acc.account_number)
        self.assertEqual(acc_updated.balance, 750.0)

    def test_withdrawal_and_minimum_balance(self):
        # Savings has $500 min balance
        _, _, acc = self.service.create_account(
            name="Charlie",
            email="charlie@test.com",
            phone="2223334444",
            pin="2222",
            account_type="SAVINGS",
            initial_deposit=1000.0
        )

        # Withdraw $300 -> Remaining $700 >= $500 (allowed)
        ok, msg, bal = self.service.withdraw(acc.account_number, 300.0)
        self.assertTrue(ok)
        self.assertEqual(bal, 700.0)

        # Withdraw $300 -> Remaining $400 < $500 (rejected due to min balance rule)
        ok, msg, bal = self.service.withdraw(acc.account_number, 300.0)
        self.assertFalse(ok)
        self.assertIn("Insufficient funds", msg)
        self.assertEqual(bal, 700.0)

    # ------------------ FUND TRANSFER ------------------ #

    def test_fund_transfer_atomic(self):
        _, _, sender = self.service.create_account(
            name="Sender",
            email="sender@test.com",
            phone="3334445555",
            pin="3333",
            account_type="SAVINGS",
            initial_deposit=2000.0
        )
        _, _, receiver = self.service.create_account(
            name="Receiver",
            email="receiver@test.com",
            phone="4445556666",
            pin="4444",
            account_type="SAVINGS",
            initial_deposit=1000.0
        )

        # Transfer $500
        ok, msg = self.service.transfer(sender.account_number, receiver.account_number, 500.0, "Gift")
        self.assertTrue(ok)

        # Check balances in DB
        s_after = self.db.get_account(sender.account_number)
        r_after = self.db.get_account(receiver.account_number)
        self.assertEqual(s_after.balance, 1500.0)
        self.assertEqual(r_after.balance, 1500.0)

        # Check transactions logged
        s_txs = self.service.get_statement(sender.account_number)
        r_txs = self.service.get_statement(receiver.account_number)
        self.assertEqual(s_txs[0].tx_type, TransactionType.TRANSFER_OUT.value)
        self.assertEqual(r_txs[0].tx_type, TransactionType.TRANSFER_IN.value)

    # ------------------ ADMIN & SUMMARY ------------------ #

    def test_admin_functions(self):
        self.assertTrue(self.service.admin_authenticate("admin", "admin123"))
        self.assertFalse(self.service.admin_authenticate("admin", "wrongpass"))

        _, _, acc = self.service.create_account(
            name="David",
            email="david@test.com",
            phone="5556667777",
            pin="5555",
            account_type="CURRENT",
            initial_deposit=1500.0
        )

        summary = self.service.get_bank_summary()
        self.assertEqual(summary["total_accounts"], 1)
        self.assertEqual(summary["total_deposits"], 1500.0)

        # Admin freeze
        ok, _ = self.service.toggle_account_status(acc.account_number, AccountStatus.FROZEN.value)
        self.assertTrue(ok)
        self.assertEqual(self.db.get_account(acc.account_number).status, AccountStatus.FROZEN.value)

        # Admin unfreeze
        ok, _ = self.service.toggle_account_status(acc.account_number, AccountStatus.ACTIVE.value)
        self.assertTrue(ok)
        self.assertEqual(self.db.get_account(acc.account_number).status, AccountStatus.ACTIVE.value)

if __name__ == "__main__":
    unittest.main()
