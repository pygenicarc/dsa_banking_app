"""
Main entry point for the Apex Banking Console Application.
Run directly with: python main.py
"""

import sys
from cli import BankingCLI
from bank_service import BankService
from database import CSVDatabase

def seed_demo_data(service: BankService):
    """Seed sample customer accounts if database is empty to allow immediate testing."""
    accounts = service.db.load_accounts()
    if not accounts:
        print("[*] Initializing demo accounts for quick testing...")
        # Create Alice (Savings)
        service.create_account(
            name="Alice Johnson",
            email="alice@example.com",
            phone="5551234567",
            pin="1234",
            account_type="SAVINGS",
            initial_deposit=2500.00
        )
        # Create Bob (Current)
        service.create_account(
            name="Bob Smith",
            email="bob@example.com",
            phone="5559876543",
            pin="4321",
            account_type="CURRENT",
            initial_deposit=5000.00
        )
        print("[*] Created demo accounts:")
        for acc in service.db.load_accounts().values():
            print(f"    - {acc.name}: Acc #{acc.account_number} | Type: {acc.account_type} | Balance: ${acc.balance:,.2f} | PIN: {'1234' if 'Alice' in acc.name else '4321'}")
        print()

def main():
    service = BankService()
    
    # Check if user passed --seed or if database is brand new and user wants demo data
    if "--seed" in sys.argv:
        seed_demo_data(service)
    elif len(service.db.load_accounts()) == 0:
        # Prompt if first time run
        print("=" * 60)
        print(" Welcome to Apex Banking System (First Time Setup)")
        print("=" * 60)
        seed_choice = input("Would you like to seed 2 demo customer accounts for testing? (y/n): ").strip().lower()
        if seed_choice == "y":
            seed_demo_data(service)

    app = BankingCLI(service)
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n\nSession terminated. Goodbye!")
        sys.exit(0)

if __name__ == "__main__":
    main()
