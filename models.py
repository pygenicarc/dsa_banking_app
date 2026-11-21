"""
Data models for the Banking Application.
"""

from dataclasses import dataclass
from enum import Enum

class AccountType(str, Enum):
    SAVINGS = "SAVINGS"
    CURRENT = "CURRENT"

class AccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    CLOSED = "CLOSED"

class TransactionType(str, Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"

@dataclass
class Account:
    account_number: str
    name: str
    email: str
    phone: str
    pin_hash: str
    pin_salt: str
    account_type: str  # SAVINGS or CURRENT
    balance: float
    status: str        # ACTIVE, FROZEN, CLOSED
    created_at: str

    def to_dict(self) -> dict:
        return {
            "account_number": self.account_number,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "pin_hash": self.pin_hash,
            "pin_salt": self.pin_salt,
            "account_type": self.account_type,
            "balance": f"{self.balance:.2f}",
            "status": self.status,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Account":
        return cls(
            account_number=str(data["account_number"]),
            name=data["name"],
            email=data["email"],
            phone=data["phone"],
            pin_hash=data["pin_hash"],
            pin_salt=data["pin_salt"],
            account_type=data["account_type"],
            balance=float(data["balance"]),
            status=data["status"],
            created_at=data["created_at"]
        )

@dataclass
class Transaction:
    transaction_id: str
    timestamp: str
    account_number: str
    tx_type: str       # DEPOSIT, WITHDRAWAL, TRANSFER_IN, TRANSFER_OUT
    amount: float
    balance_after: float
    description: str

    def to_dict(self) -> dict:
        return {
            "transaction_id": self.transaction_id,
            "timestamp": self.timestamp,
            "account_number": self.account_number,
            "tx_type": self.tx_type,
            "amount": f"{self.amount:.2f}",
            "balance_after": f"{self.balance_after:.2f}",
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        return cls(
            transaction_id=str(data["transaction_id"]),
            timestamp=data["timestamp"],
            account_number=str(data["account_number"]),
            tx_type=data["tx_type"],
            amount=float(data["amount"]),
            balance_after=float(data["balance_after"]),
            description=data["description"]
        )
