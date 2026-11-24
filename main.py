"""
main.py
-------
Personal Expense, Budget & Savings Tracker (Pure Python CLI Application)
Designed for BCA 3rd-Semester College Project & Viva.

Run with:
    python main.py
or:
    python3 main.py
"""

from datetime import datetime

from budget import (
    check_budget_warnings,
    set_category_budget,
    set_overall_budget,
)
from display import (
    display_budget_warnings,
    display_savings_overview,
    display_summary,
    display_transactions,
    format_currency,
    print_header,
    print_line,
)
from savings import (
    add_to_savings,
    create_savings_goal,
    get_savings_overview,
    withdraw_from_savings,
)
from storage import (
    DEFAULT_DATA_FILE,
    create_backup,
    export_transactions_to_csv,
    get_default_data,
    load_data,
    save_data,
)
from tracker import (
    EXPENSE_CATEGORIES,
    INCOME_CATEGORIES,
    calculate_summary,
    delete_transaction,
    edit_transaction,
    filter_transactions,
    find_transaction_by_id,
    get_current_month_str,
    get_today_date_str,
    load_demo_data,
    record_transaction,
)


def get_valid_float(prompt, allow_zero=False):
    """Repeatedly prompt the user until a valid positive number is entered."""
    while True:
        raw = input(prompt).strip()
        try:
            value = float(raw)
            if allow_zero and value >= 0:
                return round(value, 2)
            if not allow_zero and value > 0:
                return round(value, 2)
            print("  [Error] Please enter an amount greater than 0." if not allow_zero else "  [Error] Amount cannot be negative.")
        except ValueError:
            print("  [Error] Invalid number. Please enter digits only (e.g., 250 or 1250.50).")


def get_valid_int(prompt):
    """Repeatedly prompt the user until a valid integer is entered."""
    while True:
        raw = input(prompt).strip()
        try:
            return int(raw)
        except ValueError:
            print("  [Error] Please enter a valid whole number.")


def get_valid_date(prompt, default_today=True):
    """Prompt for a date in YYYY-MM-DD format; blank uses today's date."""
    today = get_today_date_str()
    while True:
        suffix = f" [Press Enter for {today}]" if default_today else ""
        raw = input(f"{prompt}{suffix}: ").strip()
        if not raw and default_today:
            return today
        try:
            datetime.strptime(raw, "%Y-%m-%d")
            return raw
        except ValueError:
            print("  [Error] Invalid date format. Please use YYYY-MM-DD (e.g., 2026-11-17).")


def get_valid_month(prompt, allow_blank_for_all=False):
    """Prompt for YYYY-MM month string."""
    current_month = get_current_month_str()
    while True:
        if allow_blank_for_all:
            raw = input(f"{prompt} [YYYY-MM, Enter for All Time]: ").strip()
            if not raw:
                return None
        else:
            raw = input(f"{prompt} [YYYY-MM, Enter for {current_month}]: ").strip()
            if not raw:
                return current_month
        try:
            datetime.strptime(raw, "%Y-%m")
            return raw
        except ValueError:
            print("  [Error] Invalid month format. Please use YYYY-MM (e.g., 2026-11).")


def choose_from_list(title, items, allow_custom=True):
    """Display a numbered list of choices and return the selected string."""
    print(f"\n  {title}:")
    for idx, item in enumerate(items, start=1):
        print(f"    {idx}. {item}")
    if allow_custom:
        print(f"    {len(items) + 1}. Custom Category")

    while True:
        choice = get_valid_int("  Enter choice number: ")
        if 1 <= choice <= len(items):
            return items[choice - 1]
        if allow_custom and choice == len(items) + 1:
            while True:
                custom = input("  Enter custom category name: ").strip()
                if custom:
                    return custom
                print("  [Error] Category name cannot be empty.")
        print("  [Error] Choice out of range. Please try again.")


def persist_changes(data):
    """Save data permanently to disk and report if saving fails."""
    if save_data(data, DEFAULT_DATA_FILE):
        print("  [Saved] Changes saved permanently to disk.")
    else:
        print("  [Error] Failed to save data to disk!")


def handle_record_income(data):
    """Workflow to record an income entry."""
    print_header("RECORD INCOME")
    category = choose_from_list("Select Income Category", INCOME_CATEGORIES)
    amount = get_valid_float("  Enter income amount (Rs.): ")
    date_str = get_valid_date("  Enter date (YYYY-MM-DD)")
    description = input("  Enter description (optional): ").strip() or f"{category} received"

    tx = record_transaction(
        data=data,
        tx_type="income",
        category=category,
        amount=amount,
        description=description,
        date_str=date_str,
    )
    persist_changes(data)
    print(
        f"  Recorded Income #{tx['id']}: {format_currency(tx['amount'])} "
        f"under '{tx['category']}' on {tx['date']}."
    )


def handle_record_expense(data):
    """Workflow to record a daily expense and immediately check monthly budgets."""
    print_header("RECORD DAILY EXPENSE")
    category = choose_from_list("Select Expense Category", EXPENSE_CATEGORIES)
    amount = get_valid_float("  Enter expense amount (Rs.): ")
    date_str = get_valid_date("  Enter date (YYYY-MM-DD)")
    description = input("  Enter description (e.g., Lunch, Bus ticket): ").strip() or f"{category} expense"

    summary_before = calculate_summary(data)
    if amount > summary_before["remaining_balance"]:
        print(
            f"  [Note] This expense ({format_currency(amount)}) exceeds your current "
            f"remaining balance ({format_currency(summary_before['remaining_balance'])})."
        )
        confirm = input("  Do you still want to record this expense? (y/n): ").strip().lower()
        if confirm != "y":
            print("  Expense cancelled.")
            return

    tx = record_transaction(
        data=data,
        tx_type="expense",
        category=category,
        amount=amount,
        description=description,
        date_str=date_str,
    )
    persist_changes(data)
    print(
        f"  Recorded Expense #{tx['id']}: {format_currency(tx['amount'])} "
        f"under '{tx['category']}' on {tx['date']}."
    )

    tx_month = tx["date"][:7]
    warnings = check_budget_warnings(data, month=tx_month, category=category)
    for item in warnings:
        if item["level"] in ("WARNING", "EXCEEDED"):
            print(f"\n  *** {item['message']} ***")


def handle_savings_menu(data):
    """Sub-menu for recording savings, creating goals, viewing progress, and withdrawing."""
    while True:
        print_header("SAVINGS & GOALS MENU")
        print("  1. Record a New Saving Deposit")
        print("  2. Create a New Savings Goal")
        print("  3. View Savings & Goals Progress")
        print("  4. Withdraw from a Savings Goal")
        print("  0. Back to Main Menu")
        print_line("-")

        choice = input("  Choose an option: ").strip()

        if choice == "1":
            summary = calculate_summary(data)
            print(f"\n  Current Remaining Spendable Balance: {format_currency(summary['remaining_balance'])}")
            goals = data.get("savings_goals", [])

            goal_name = "General Savings"
            if goals:
                print("\n  Select where to save:")
                for idx, goal in enumerate(goals, start=1):
                    print(
                        f"    {idx}. {goal['name']} "
                        f"(Saved: {format_currency(goal['saved_amount'])} / {format_currency(goal['target_amount'])})"
                    )
                print(f"    {len(goals) + 1}. General Savings (No specific goal)")

                while True:
                    pick = get_valid_int("  Enter choice number: ")
                    if 1 <= pick <= len(goals):
                        goal_name = goals[pick - 1]["name"]
                        break
                    if pick == len(goals) + 1:
                        goal_name = "General Savings"
                        break
                    print("  [Error] Invalid selection.")
            else:
                print("  No specific goals yet. Recording under 'General Savings'.")

            amount = get_valid_float("  Enter amount to save (Rs.): ")
            if amount > summary["remaining_balance"]:
                print(
                    f"  [Warning] Amount exceeds your remaining balance "
                    f"({format_currency(summary['remaining_balance'])})."
                )
                proceed = input("  Still record this saving? (y/n): ").strip().lower()
                if proceed != "y":
                    print("  Saving cancelled.")
                    continue

            date_str = get_valid_date("  Enter date (YYYY-MM-DD)")
            desc = input("  Enter note/description (optional): ").strip() or f"Saved toward {goal_name}"

            tx, matched_goal = add_to_savings(
                data=data,
                amount=amount,
                goal_name=goal_name,
                description=desc,
                date_str=date_str,
            )
            persist_changes(data)
            print(f"  Recorded Saving #{tx['id']}: {format_currency(tx['amount'])} ({tx['category']}).")
            if matched_goal and matched_goal["saved_amount"] >= matched_goal["target_amount"]:
                print(f"  *** CONGRATULATIONS! You reached your '{matched_goal['name']}' savings goal! ***")

        elif choice == "2":
            name = input("  Enter new savings goal name (e.g., New Laptop): ").strip()
            target = get_valid_float("  Enter target amount (Rs.): ")
            try:
                goal = create_savings_goal(data, name, target)
                persist_changes(data)
                print(
                    f"  Created goal '{goal['name']}' with target "
                    f"{format_currency(goal['target_amount'])}."
                )
            except ValueError as exc:
                print(f"  [Error] {exc}")

        elif choice == "3":
            overview = get_savings_overview(data)
            display_savings_overview(overview)

        elif choice == "4":
            goals = [g for g in data.get("savings_goals", []) if float(g.get("saved_amount", 0)) > 0]
            if not goals:
                print("  [Info] No savings goals have available balance to withdraw.")
                continue

            print("\n  Select goal to withdraw from:")
            for idx, goal in enumerate(goals, start=1):
                print(f"    {idx}. {goal['name']} (Available: {format_currency(goal['saved_amount'])})")

            while True:
                pick = get_valid_int("  Enter choice number: ")
                if 1 <= pick <= len(goals):
                    chosen_goal = goals[pick - 1]
                    break
                print("  [Error] Invalid selection.")

            amount = get_valid_float("  Enter amount to withdraw (Rs.): ")
            reason = input("  Enter reason for withdrawal: ").strip() or "Transfer to spendable balance"
            date_str = get_valid_date("  Enter date (YYYY-MM-DD)")

            try:
                tx, updated_goal = withdraw_from_savings(
                    data=data,
                    amount=amount,
                    goal_name=chosen_goal["name"],
                    reason=reason,
                    date_str=date_str,
                )
                persist_changes(data)
                print(
                    f"  Withdrew {format_currency(tx['amount'])} from '{updated_goal['name']}'. "
                    f"Remaining in goal: {format_currency(updated_goal['saved_amount'])}."
                )
            except ValueError as exc:
                print(f"  [Error] {exc}")

        elif choice == "0":
            break
        else:
            print("  [Error] Invalid choice. Please select 0-4.")


def handle_view_history(data):
    """Sub-menu to view all transactions or filter by type, category, month, or keyword."""
    while True:
        print_header("VIEW TRANSACTION HISTORY")
        print("  1. View All Transactions")
        print("  2. Filter by Type (Income / Expense / Saving)")
        print("  3. Filter by Category")
        print("  4. Filter by Month (YYYY-MM)")
        print("  5. Search by Keyword")
        print("  0. Back to Main Menu")
        print_line("-")

        choice = input("  Choose an option: ").strip()
        transactions = data.get("transactions", [])

        if choice == "1":
            results = filter_transactions(transactions)
            display_transactions(results, "ALL TRANSACTIONS")
        elif choice == "2":
            tx_type = choose_from_list(
                "Select Type", ["income", "expense", "saving"], allow_custom=False
            )
            results = filter_transactions(transactions, tx_type=tx_type)
            display_transactions(results, f"{tx_type.upper()} TRANSACTIONS")
        elif choice == "3":
            cat = input("  Enter category name (e.g., Food, Allowance): ").strip()
            results = filter_transactions(transactions, category=cat)
            display_transactions(results, f"CATEGORY: {cat.upper()}")
        elif choice == "4":
            month = get_valid_month("  Enter month to view")
            results = filter_transactions(transactions, month=month)
            display_transactions(results, f"TRANSACTIONS FOR {month}")
        elif choice == "5":
            keyword = input("  Enter keyword to search in description/category: ").strip()
            results = filter_transactions(transactions, keyword=keyword)
            display_transactions(results, f"SEARCH RESULTS: '{keyword}'")
        elif choice == "0":
            break
        else:
            print("  [Error] Invalid option. Please select 0-5.")


def handle_view_summary(data):
    """Display overall or month-specific financial summary."""
    print_header("FINANCIAL SUMMARY OPTIONS")
    month = get_valid_month("  Filter by month or leave blank for All Time", allow_blank_for_all=True)
    summary = calculate_summary(data, month=month)
    display_summary(summary)

    check_month = month if month else get_current_month_str()
    warnings = check_budget_warnings(data, month=check_month)
    triggered = [w for w in warnings if w["level"] in ("WARNING", "EXCEEDED")]
    if triggered:
        print(f"\n  Active Budget Alerts for {check_month}:")
        for item in triggered:
            print(f"    -> {item['message']}")
        print_line("-")


def handle_budget_menu(data):
    """Sub-menu to set overall/category monthly budgets and view utilization warnings."""
    while True:
        print_header("MONTHLY BUDGETS & WARNINGS")
        print("  1. View Monthly Budget Status & Warnings")
        print("  2. Set Overall Monthly Expense Budget")
        print("  3. Set Category-Wise Monthly Budget")
        print("  0. Back to Main Menu")
        print_line("-")

        choice = input("  Choose an option: ").strip()

        if choice == "1":
            month = get_valid_month("  Enter month to check")
            warnings = check_budget_warnings(data, month=month)
            display_budget_warnings(warnings, month)
        elif choice == "2":
            print("  (Enter 0 to remove the overall monthly budget limit)")
            limit = get_valid_float("  Enter overall monthly budget limit (Rs.): ", allow_zero=True)
            set_overall_budget(data, limit)
            persist_changes(data)
            if limit == 0:
                print("  Overall monthly budget removed.")
            else:
                print(f"  Overall monthly budget set to {format_currency(limit)}.")
        elif choice == "3":
            category = choose_from_list("Select Expense Category to Budget", EXPENSE_CATEGORIES)
            print("  (Enter 0 to remove budget limit for this category)")
            limit = get_valid_float(f"  Enter monthly limit for '{category}' (Rs.): ", allow_zero=True)
            set_category_budget(data, category, limit)
            persist_changes(data)
            if limit == 0:
                print(f"  Budget removed for '{category}'.")
            else:
                print(f"  Monthly budget for '{category}' set to {format_currency(limit)}.")
        elif choice == "0":
            break
        else:
            print("  [Error] Invalid choice. Please select 0-3.")


def handle_edit_or_delete(data):
    """Allow the user to edit or delete an existing transaction by ID."""
    transactions = filter_transactions(data.get("transactions", []))
    display_transactions(transactions, "SELECT TRANSACTION TO EDIT OR DELETE")
    if not transactions:
        return

    tx_id = get_valid_int("  Enter Transaction ID (or 0 to cancel): ")
    if tx_id == 0:
        return

    tx = find_transaction_by_id(data["transactions"], tx_id)
    if tx is None:
        print(f"  [Error] Transaction ID #{tx_id} not found.")
        return

    print(
        f"\n  Selected #{tx['id']}: {tx['date']} | {tx['type'].upper()} | "
        f"{tx['category']} | {format_currency(tx['amount'])} | {tx['description']}"
    )
    print("  1. Edit Transaction")
    print("  2. Delete Transaction")
    print("  0. Cancel")
    action = input("  Choose action: ").strip()

    if action == "1":
        print("  Leave a field blank to keep its current value.")
        raw_amount = input(f"  New amount [{tx['amount']}]: ").strip()
        new_amount = None
        if raw_amount:
            try:
                parsed = float(raw_amount)
                if parsed <= 0:
                    print("  [Error] Amount must be greater than 0. Edit cancelled.")
                    return
                new_amount = parsed
            except ValueError:
                print("  [Error] Invalid number. Edit cancelled.")
                return

        new_category = input(f"  New category [{tx['category']}]: ").strip() or None
        new_description = input(f"  New description [{tx['description']}]: ").strip() or None
        raw_date = input(f"  New date YYYY-MM-DD [{tx['date']}]: ").strip()
        new_date = None
        if raw_date:
            try:
                datetime.strptime(raw_date, "%Y-%m-%d")
                new_date = raw_date
            except ValueError:
                print("  [Error] Invalid date format. Edit cancelled.")
                return

        edit_transaction(
            data,
            tx_id,
            new_amount=new_amount,
            new_category=new_category,
            new_description=new_description,
            new_date=new_date,
        )
        persist_changes(data)
        print(f"  Transaction #{tx_id} updated.")

    elif action == "2":
        confirm = input(f"  Are you sure you want to delete Transaction #{tx_id}? (y/n): ").strip().lower()
        if confirm == "y":
            deleted, removed = delete_transaction(data, tx_id)
            if deleted:
                persist_changes(data)
                print(f"  Deleted Transaction #{removed['id']} ({removed['category']}).")
        else:
            print("  Delete cancelled.")


def handle_export_and_backup(data):
    """Export transactions to CSV and create a timestamped JSON backup."""
    print_header("EXPORT & BACKUP")
    persist_changes(data)

    csv_ok, csv_info = export_transactions_to_csv(data.get("transactions", []))
    if csv_ok:
        print(f"  [CSV Exported] Saved spreadsheet to: {csv_info}")
    else:
        print(f"  [Error] CSV export failed: {csv_info}")

    backup_ok, backup_info = create_backup(DEFAULT_DATA_FILE)
    if backup_ok:
        print(f"  [Backup Created] JSON backup saved to: {backup_info}")
    else:
        print(f"  [Warning] Backup skipped: {backup_info}")


def handle_demo_or_reset(data):
    """Load sample demo records (useful for college project viva) or reset all data."""
    print_header("DEMO DATA / RESET")
    print("  1. Load Sample Demo Data (replaces current records)")
    print("  2. Clear All Saved Data (reset to empty)")
    print("  0. Back to Main Menu")
    print_line("-")

    choice = input("  Choose an option: ").strip()
    if choice == "1":
        confirm = input("  Replace current data with sample demo records? (y/n): ").strip().lower()
        if confirm == "y":
            load_demo_data(data)
            persist_changes(data)
            print("  Demo data loaded successfully! Try viewing Summary, Budgets, or Savings.")
    elif choice == "2":
        confirm = input("  WARNING: Delete ALL transactions, budgets, and goals? (y/n): ").strip().lower()
        if confirm == "y":
            fresh = get_default_data()
            data.clear()
            data.update(fresh)
            persist_changes(data)
            print("  All records cleared.")


def print_main_menu(data):
    """Show live quick-glance stats and main navigation menu."""
    summary = calculate_summary(data)
    current_month = get_current_month_str()
    warnings = check_budget_warnings(data, month=current_month)
    active_alerts = [w for w in warnings if w["level"] in ("WARNING", "EXCEEDED")]

    print()
    print_line("=")
    print("       PERSONAL EXPENSE, BUDGET & SAVINGS TRACKER (PYTHON)")
    print_line("=")
    print(
        f"  Income: {format_currency(summary['total_income'])} | "
        f"Expenses: {format_currency(summary['total_expenses'])} | "
        f"Savings: {format_currency(summary['total_savings'])} | "
        f"Balance: {format_currency(summary['remaining_balance'])}"
    )
    if active_alerts:
        print_line("-")
        for alert in active_alerts:
            print(f"  [!] {alert['message']}")
    print_line("=")
    print("  1. Record Income")
    print("  2. Record Daily Expense")
    print("  3. Savings & Savings Goals")
    print("  4. View Transaction History & Filter")
    print("  5. View Financial Summary")
    print("  6. Set & Check Monthly Budgets")
    print("  7. Edit or Delete a Transaction")
    print("  8. Export to CSV & Create Backup")
    print("  9. Load Demo Data / Reset Records")
    print("  0. Save & Exit")
    print_line("-")


def main():
    """Application entry point: loads saved file and runs the main menu loop."""
    data = load_data(DEFAULT_DATA_FILE)
    print("\n  Welcome! Loaded saved records from:", DEFAULT_DATA_FILE)

    while True:
        print_main_menu(data)
        choice = input("  Enter your choice (0-9): ").strip()

        if choice == "1":
            handle_record_income(data)
        elif choice == "2":
            handle_record_expense(data)
        elif choice == "3":
            handle_savings_menu(data)
        elif choice == "4":
            handle_view_history(data)
        elif choice == "5":
            handle_view_summary(data)
        elif choice == "6":
            handle_budget_menu(data)
        elif choice == "7":
            handle_edit_or_delete(data)
        elif choice == "8":
            handle_export_and_backup(data)
        elif choice == "9":
            handle_demo_or_reset(data)
        elif choice == "0":
            persist_changes(data)
            print("\n  Thank you for using Personal Expense Tracker. Goodbye!\n")
            break
        else:
            print("  [Error] Invalid menu choice. Please enter a number from 0 to 9.")


if __name__ == "__main__":
    main()
