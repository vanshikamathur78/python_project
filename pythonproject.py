"""
storage.py
----------
Handles permanent file storage for the Personal Expense Tracker.
Uses Python's built-in json, csv, os, shutil, and datetime modules.
"""

import csv
import json
import os
import shutil
from datetime import datetime

DATA_DIR = "data"
DEFAULT_DATA_FILE = os.path.join(DATA_DIR, "expense_data.json")
DEFAULT_CSV_FILE = os.path.join(DATA_DIR, "transactions_export.csv")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")


def get_default_data():
    """Return a fresh, empty dictionary structure for storing all records."""
    return {
        "transactions": [],
        "budgets": {
            "overall_monthly": 0.0,
            "categories": {},
        },
        "savings_goals": [],
    }


def ensure_directory_exists(directory_path):
    """Create the target directory if it does not already exist."""
    if directory_path and not os.path.exists(directory_path):
        os.makedirs(directory_path, exist_ok=True)


def normalize_data_structure(raw_data):
    """
    Validate and fill in any missing top-level keys so loaded JSON data
    always matches the expected dictionary and list schema.
    """
    default_data = get_default_data()

    if not isinstance(raw_data, dict):
        return default_data

    transactions = raw_data.get("transactions", [])
    if not isinstance(transactions, list):
        transactions = []

    raw_budgets = raw_data.get("budgets", {})
    if not isinstance(raw_budgets, dict):
        raw_budgets = {}

    overall_budget = raw_budgets.get("overall_monthly", 0.0)
    try:
        overall_budget = float(overall_budget)
    except (TypeError, ValueError):
        overall_budget = 0.0

    category_budgets = raw_budgets.get("categories", {})
    if not isinstance(category_budgets, dict):
        category_budgets = {}

    savings_goals = raw_data.get("savings_goals", [])
    if not isinstance(savings_goals, list):
        savings_goals = []

    return {
        "transactions": transactions,
        "budgets": {
            "overall_monthly": overall_budget,
            "categories": category_budgets,
        },
        "savings_goals": savings_goals,
    }


def load_data(filepath=DEFAULT_DATA_FILE):
    """
    Load saved records from a JSON file.
    If the file does not exist yet, initialize it with default data.
    """
    directory = os.path.dirname(filepath)
    ensure_directory_exists(directory)

    if not os.path.exists(filepath):
        data = get_default_data()
        save_data(data, filepath)
        return data

    try:
        with open(filepath, "r", encoding="utf-8") as file:
            raw_data = json.load(file)
        return normalize_data_structure(raw_data)
    except (json.JSONDecodeError, OSError):
        corrupted_backup = f"{filepath}.corrupted.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            shutil.copy2(filepath, corrupted_backup)
        except OSError:
            pass
        data = get_default_data()
        save_data(data, filepath)
        return data


def save_data(data, filepath=DEFAULT_DATA_FILE):
    """
    Permanently save all transactions, budgets, and savings goals to a JSON file.
    Returns True on success, False on failure.
    """
    directory = os.path.dirname(filepath)
    ensure_directory_exists(directory)

    try:
        with open(filepath, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
        return True
    except OSError:
        return False


def export_transactions_to_csv(transactions, csv_filepath=DEFAULT_CSV_FILE):
    """
    Export the list of transaction dictionaries into a CSV spreadsheet file.
    Returns (True, csv_filepath) on success or (False, error_message) on failure.
    """
    directory = os.path.dirname(csv_filepath)
    ensure_directory_exists(directory)

    fieldnames = [
        "id",
        "date",
        "type",
        "category",
        "amount",
        "description",
        "goal_name",
    ]

    try:
        with open(csv_filepath, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for tx in transactions:
                writer.writerow(
                    {
                        "id": tx.get("id", ""),
                        "date": tx.get("date", ""),
                        "type": tx.get("type", ""),
                        "category": tx.get("category", ""),
                        "amount": f"{float(tx.get('amount', 0.0)):.2f}",
                        "description": tx.get("description", ""),
                        "goal_name": tx.get("goal_name", ""),
                    }
                )
        return True, csv_filepath
    except OSError as exc:
        return False, str(exc)


def create_backup(filepath=DEFAULT_DATA_FILE, backup_dir=BACKUP_DIR):
    """
    Create a timestamped backup copy of the JSON data file.
    Returns (True, backup_path) on success or (False, error_message) on failure.
    """
    if not os.path.exists(filepath):
        return False, "No saved data file found to back up."

    ensure_directory_exists(backup_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"expense_backup_{timestamp}.json"
    backup_path = os.path.join(backup_dir, backup_filename)

    try:
        shutil.copy2(filepath, backup_path)
        return True, backup_path
    except OSError as exc:
        return False, str(exc)
"""
tracker.py
------------
Core transaction management and financial calculation functions.
Uses Python lists, dictionaries, loops, functions, and conditional statements.
"""
import os
import tempfile
import unittest

from datetime import datetime

INCOME_CATEGORIES = [
    "Allowance",
    "Salary",
    "Freelance",
    "Scholarship",
    "Gift",
    "Other Income",
]

EXPENSE_CATEGORIES = [
    "Food",
    "Transport",
    "Rent & Hostel",
    "Books & Stationery",
    "Bills & Recharge",
    "Entertainment",
    "Health",
    "Shopping",
    "Other Expense",
]

SAVING_CATEGORIES = [
    "Emergency Fund",
    "Education Savings",
    "Gadgets & Tech",
    "Travel & Trip",
    "General Savings",
]


def get_today_date_str():
    """Return today's date formatted as YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")


def get_current_month_str():
    """Return current year and month formatted as YYYY-MM."""
    return datetime.now().strftime("%Y-%m")


def generate_next_id(transactions):
    """Generate the next unique integer transaction ID using a loop."""
    if not transactions:
        return 1

    highest_id = 0
    for tx in transactions:
        tx_id = tx.get("id", 0)
        if tx_id > highest_id:
            highest_id = tx_id
    return highest_id + 1


def record_transaction(
    data,
    tx_type,
    category,
    amount,
    description,
    date_str=None,
    goal_name="",
):
    """
    Create a transaction dictionary and append it to data["transactions"].
    tx_type must be 'income', 'expense', or 'saving'.
    Returns the newly created transaction dictionary.
    """
    valid_types = ("income", "expense", "saving")
    if tx_type not in valid_types:
        raise ValueError(f"Invalid transaction type '{tx_type}'. Must be one of {valid_types}.")

    amount = round(float(amount), 2)
    if amount <= 0:
        raise ValueError("Transaction amount must be greater than zero.")

    if not date_str:
        date_str = get_today_date_str()

    transaction = {
        "id": generate_next_id(data["transactions"]),
        "date": date_str,
        "type": tx_type,
        "category": category.strip() if category else "General",
        "amount": amount,
        "description": description.strip() if description else "-",
        "goal_name": goal_name.strip() if goal_name else "",
    }

    data["transactions"].append(transaction)
    return transaction


def find_transaction_by_id(transactions, tx_id):
    """Search for a transaction dictionary by its ID."""
    for tx in transactions:
        if tx.get("id") == tx_id:
            return tx
    return None


def edit_transaction(
    data,
    tx_id,
    new_amount=None,
    new_category=None,
    new_description=None,
    new_date=None,
):
    """
    Update fields of an existing transaction by ID.
    Returns (True, updated_tx) if found, or (False, None) if not found.
    """
    tx = find_transaction_by_id(data["transactions"], tx_id)
    if tx is None:
        return False, None

    if new_amount is not None:
        parsed_amount = round(float(new_amount), 2)
        if parsed_amount <= 0:
            raise ValueError("Amount must be greater than zero.")
        tx["amount"] = parsed_amount

    if new_category is not None and new_category.strip():
        tx["category"] = new_category.strip()

    if new_description is not None and new_description.strip():
        tx["description"] = new_description.strip()

    if new_date is not None and new_date.strip():
        tx["date"] = new_date.strip()

    return True, tx


def delete_transaction(data, tx_id):
    """
    Remove a transaction by ID from data["transactions"].
    If the deleted transaction was a saving linked to a goal, adjust that goal's saved_amount.
    Returns (True, removed_tx) or (False, None).
    """
    transactions = data["transactions"]
    for index, tx in enumerate(transactions):
        if tx.get("id") == tx_id:
            removed = transactions.pop(index)

            if removed.get("type") == "saving" and removed.get("goal_name"):
                for goal in data.get("savings_goals", []):
                    if goal["name"].lower() == removed["goal_name"].lower():
                        goal["saved_amount"] = round(
                            max(0.0, float(goal["saved_amount"]) - float(removed["amount"])),
                            2,
                        )
                        break
            elif removed.get("type") == "income" and removed.get("category") == "Savings Withdrawal":
                if removed.get("goal_name"):
                    for goal in data.get("savings_goals", []):
                        if goal["name"].lower() == removed["goal_name"].lower():
                            goal["saved_amount"] = round(
                                float(goal["saved_amount"]) + float(removed["amount"]),
                                2,
                            )
                            break

            return True, removed

    return False, None


def filter_transactions(
    transactions,
    tx_type=None,
    category=None,
    month=None,
    keyword=None,
):
    """
    Filter transactions using loops and conditionals.
    Returns a new list sorted by date (newest first), then ID (highest first).
    """
    results = []
    for tx in transactions:
        if tx_type and tx.get("type") != tx_type:
            continue
        if category and tx.get("category", "").lower() != category.lower():
            continue
        if month and not tx.get("date", "").startswith(month):
            continue
        if keyword:
            search_text = f"{tx.get('description', '')} {tx.get('category', '')} {tx.get('goal_name', '')}".lower()
            if keyword.lower() not in search_text:
                continue
        results.append(tx)

    results.sort(key=lambda item: (item.get("date", ""), item.get("id", 0)), reverse=True)
    return results


def calculate_summary(data, month=None):
    """
    Calculate total income, total expenses, total savings, remaining balance,
    and category-wise breakdowns using loops and dictionaries.
    """
    transactions = data.get("transactions", [])
    if month:
        transactions = filter_transactions(transactions, month=month)

    total_income = 0.0
    total_expenses = 0.0
    total_savings = 0.0
    expense_by_category = {}
    income_by_category = {}
    savings_by_category = {}

    for tx in transactions:
        amount = float(tx.get("amount", 0.0))
        tx_type = tx.get("type")
        category = tx.get("category", "Other")

        if tx_type == "income":
            if category == "Savings Withdrawal":
                total_savings = round(total_savings - amount, 2)
            else:
                total_income = round(total_income + amount, 2)
                income_by_category[category] = round(
                    income_by_category.get(category, 0.0) + amount, 2
                )
        elif tx_type == "expense":
            total_expenses = round(total_expenses + amount, 2)
            expense_by_category[category] = round(
                expense_by_category.get(category, 0.0) + amount, 2
            )
        elif tx_type == "saving":
            total_savings = round(total_savings + amount, 2)
            savings_by_category[category] = round(
                savings_by_category.get(category, 0.0) + amount, 2
            )

    net_after_expenses = round(total_income - total_expenses, 2)
    remaining_balance = round(total_income - total_expenses - total_savings, 2)

    if total_income > 0:
        savings_rate_percent = round((total_savings / total_income) * 100, 1)
    else:
        savings_rate_percent = 0.0

    return {
        "month": month if month else "All Time",
        "total_income": total_income,
        "total_expenses": total_expenses,
        "total_savings": max(0.0, total_savings),
        "net_after_expenses": net_after_expenses,
        "remaining_balance": remaining_balance,
        "savings_rate_percent": savings_rate_percent,
        "expense_by_category": expense_by_category,
        "income_by_category": income_by_category,
        "savings_by_category": savings_by_category,
        "transaction_count": len(transactions),
    }


def load_demo_data(data):
    """
    Populate sample college-student records for demonstration during a project viva.
    """
    today = get_today_date_str()
    month_prefix = get_current_month_str()

    data["transactions"] = [
        {
            "id": 1,
            "date": f"{month_prefix}-01",
            "type": "income",
            "category": "Allowance",
            "amount": 12000.0,
            "description": "Monthly home allowance",
            "goal_name": "",
        },
        {
            "id": 2,
            "date": f"{month_prefix}-03",
            "type": "income",
            "category": "Freelance",
            "amount": 4500.0,
            "description": "Python tutoring & mini website help",
            "goal_name": "",
        },
        {
            "id": 3,
            "date": f"{month_prefix}-04",
            "type": "expense",
            "category": "Rent & Hostel",
            "amount": 4500.0,
            "description": "Hostel room monthly fee",
            "goal_name": "",
        },
        {
            "id": 4,
            "date": f"{month_prefix}-06",
            "type": "expense",
            "category": "Books & Stationery",
            "amount": 850.0,
            "description": "BCA 3rd Sem Data Structures & DBMS books",
            "goal_name": "",
        },
        {
            "id": 5,
            "date": f"{month_prefix}-08",
            "type": "expense",
            "category": "Food",
            "amount": 1650.0,
            "description": "Mess & college canteen meals",
            "goal_name": "",
        },
        {
            "id": 6,
            "date": f"{month_prefix}-10",
            "type": "expense",
            "category": "Transport",
            "amount": 600.0,
            "description": "Bus pass & metro recharge",
            "goal_name": "",
        },
        {
            "id": 7,
            "date": f"{month_prefix}-12",
            "type": "saving",
            "category": "Emergency Fund",
            "amount": 2500.0,
            "description": "Monthly emergency savings transfer",
            "goal_name": "Emergency Fund",
        },
        {
            "id": 8,
            "date": today,
            "type": "saving",
            "category": "Gadgets & Tech",
            "amount": 1500.0,
            "description": "Saving for new coding laptop",
            "goal_name": "New Laptop",
        },
        {
            "id": 9,
            "date": today,
            "type": "expense",
            "category": "Bills & Recharge",
            "amount": 499.0,
            "description": "Mobile internet recharge",
            "goal_name": "",
        },
    ]

    data["budgets"] = {
        "overall_monthly": 10000.0,
        "categories": {
            "Food": 2000.0,
            "Transport": 1000.0,
            "Entertainment": 800.0,
        },
    }

    data["savings_goals"] = [
        {
            "name": "Emergency Fund",
            "target_amount": 10000.0,
            "saved_amount": 2500.0,
            "created_date": f"{month_prefix}-01",
        },
        {
            "name": "New Laptop",
            "target_amount": 45000.0,
            "saved_amount": 1500.0,
            "created_date": f"{month_prefix}-05",
        },
    ]

    return data
"""
budget.py
---------
Monthly budget configuration and automated limit-warning checks.
Alerts users when spending approaches (>= 80%) or exceeds (> 100%) monthly limits.
"""

import get_current_month_str


WARNING_THRESHOLD_PERCENT = 80.0


def set_overall_budget(data, amount):
    """Set or clear (0) the overall monthly expense limit."""
    parsed_amount = round(float(amount), 2)
    if parsed_amount < 0:
        raise ValueError("Budget limit cannot be negative.")
    data["budgets"]["overall_monthly"] = parsed_amount
    return parsed_amount


def set_category_budget(data, category, amount):
    """Set or remove (0) a monthly budget limit for a specific expense category."""
    parsed_amount = round(float(amount), 2)
    if parsed_amount < 0:
        raise ValueError("Budget limit cannot be negative.")

    categories = data["budgets"]["categories"]
    if parsed_amount == 0:
        categories.pop(category, None)
    else:
        categories[category] = parsed_amount
    return parsed_amount


def get_monthly_spending(transactions, month=None):
    """
    Calculate total spending and category-wise spending for a given YYYY-MM month.
    Returns (total_spent, category_totals_dict).
    """
    if not month:
        month = get_current_month_str()

    total_spent = 0.0
    category_totals = {}

    for tx in transactions:
        if tx.get("type") != "expense":
            continue
        if not tx.get("date", "").startswith(month):
            continue

        amount = float(tx.get("amount", 0.0))
        category = tx.get("category", "Other Expense")
        total_spent = round(total_spent + amount, 2)
        category_totals[category] = round(category_totals.get(category, 0.0) + amount, 2)

    return total_spent, category_totals


def _evaluate_limit(scope_name, spent, limit):
    """Evaluate spending against a limit and build a status dictionary."""
    if limit <= 0:
        return None

    percent = round((spent / limit) * 100, 1)
    remaining = round(limit - spent, 2)

    if spent > limit:
        over_by = round(spent - limit, 2)
        level = "EXCEEDED"
        message = (
            f"ALERT! {scope_name} monthly budget EXCEEDED by Rs. {over_by:,.2f} "
            f"(Spent Rs. {spent:,.2f} / Limit Rs. {limit:,.2f} - {percent}%)."
        )
    elif percent >= WARNING_THRESHOLD_PERCENT:
        level = "WARNING"
        message = (
            f"CAUTION: {scope_name} spending has reached {percent}% of monthly budget "
            f"(Rs. {remaining:,.2f} remaining out of Rs. {limit:,.2f})."
        )
    else:
        level = "OK"
        message = (
            f"OK: {scope_name} is within budget ({percent}% used, "
            f"Rs. {remaining:,.2f} remaining)."
        )

    return {
        "scope": scope_name,
        "level": level,
        "spent": spent,
        "limit": limit,
        "remaining": remaining,
        "percent": percent,
        "message": message,
    }


def check_budget_warnings(data, month=None, category=None):
    """
    Check overall monthly budget and category budget(s) for a month.
    If 'category' is passed, checks that specific category and overall budget.
    If 'category' is None, checks overall budget and all budgeted categories.
    Returns a list of status dictionaries.
    """
    if not month:
        month = get_current_month_str()

    total_spent, category_totals = get_monthly_spending(data["transactions"], month)
    budgets = data.get("budgets", {})
    results = []

    overall_limit = float(budgets.get("overall_monthly", 0.0))
    if overall_limit > 0:
        overall_status = _evaluate_limit("Overall Monthly", total_spent, overall_limit)
        if overall_status:
            results.append(overall_status)

    cat_budgets = budgets.get("categories", {})
    if category:
        if category in cat_budgets:
            cat_limit = float(cat_budgets[category])
            cat_spent = float(category_totals.get(category, 0.0))
            cat_status = _evaluate_limit(f"Category '{category}'", cat_spent, cat_limit)
            if cat_status:
                results.append(cat_status)
    else:
        for cat_name, cat_limit in cat_budgets.items():
            cat_spent = float(category_totals.get(cat_name, 0.0))
            cat_status = _evaluate_limit(f"Category '{cat_name}'", cat_spent, float(cat_limit))
            if cat_status:
                results.append(cat_status)

    return results
"""
savings.py
----------
Manages personal savings deposits, savings goals, progress tracking,
and savings withdrawals.
"""

from tracker import get_today_date_str, record_transaction


def find_savings_goal(data, goal_name):
    """Find a savings goal dictionary by name (case-insensitive)."""
    for goal in data.get("savings_goals", []):
        if goal.get("name", "").lower() == goal_name.strip().lower():
            return goal
    return None


def create_savings_goal(data, goal_name, target_amount, created_date=None):
    """
    Create a new savings goal dictionary and store it in data["savings_goals"].
    Raises ValueError if the goal name is empty, duplicate, or target <= 0.
    """
    cleaned_name = goal_name.strip()
    if not cleaned_name:
        raise ValueError("Savings goal name cannot be empty.")

    if find_savings_goal(data, cleaned_name) is not None:
        raise ValueError(f"A savings goal named '{cleaned_name}' already exists.")

    target = round(float(target_amount), 2)
    if target <= 0:
        raise ValueError("Target savings amount must be greater than zero.")

    goal = {
        "name": cleaned_name,
        "target_amount": target,
        "saved_amount": 0.0,
        "created_date": created_date if created_date else get_today_date_str(),
    }
    data["savings_goals"].append(goal)
    return goal


def add_to_savings(
    data,
    amount,
    goal_name="General Savings",
    description="Savings deposit",
    date_str=None,
):
    """
    Record a savings transaction and update the corresponding savings goal (if matched).
    If goal_name does not match any goal, it still records under General Savings.
    Returns (transaction, matched_goal_or_none).
    """
    parsed_amount = round(float(amount), 2)
    if parsed_amount <= 0:
        raise ValueError("Savings amount must be greater than zero.")

    cleaned_goal = goal_name.strip() if goal_name else "General Savings"
    goal = find_savings_goal(data, cleaned_goal)

    category_label = goal["name"] if goal else cleaned_goal
    tx = record_transaction(
        data=data,
        tx_type="saving",
        category=category_label,
        amount=parsed_amount,
        description=description,
        date_str=date_str,
        goal_name=goal["name"] if goal else "",
    )

    if goal is not None:
        goal["saved_amount"] = round(float(goal["saved_amount"]) + parsed_amount, 2)

    return tx, goal


def withdraw_from_savings(
    data,
    amount,
    goal_name,
    reason="Emergency withdrawal from savings",
    date_str=None,
):
    """
    Withdraw money from an existing savings goal and return it to spendable balance.
    Records an income entry with category 'Savings Withdrawal' for transparent tracking.
    """
    parsed_amount = round(float(amount), 2)
    if parsed_amount <= 0:
        raise ValueError("Withdrawal amount must be greater than zero.")

    goal = find_savings_goal(data, goal_name)
    if goal is None:
        raise ValueError(f"Savings goal '{goal_name}' was not found.")

    current_saved = float(goal.get("saved_amount", 0.0))
    if parsed_amount > current_saved:
        raise ValueError(
            f"Cannot withdraw Rs. {parsed_amount:,.2f}; only Rs. {current_saved:,.2f} saved in '{goal['name']}'."
        )

    goal["saved_amount"] = round(current_saved - parsed_amount, 2)
    tx = record_transaction(
        data=data,
        tx_type="income",
        category="Savings Withdrawal",
        amount=parsed_amount,
        description=reason,
        date_str=date_str,
        goal_name=goal["name"],
    )
    return tx, goal


def get_savings_overview(data):
    """
    Compute total savings across transactions and build goal progress summaries.
    """
    total_saved_in_tx = 0.0
    for tx in data.get("transactions", []):
        if tx.get("type") == "saving":
            total_saved_in_tx = round(total_saved_in_tx + float(tx.get("amount", 0.0)), 2)
        elif tx.get("type") == "income" and tx.get("category") == "Savings Withdrawal":
            total_saved_in_tx = round(total_saved_in_tx - float(tx.get("amount", 0.0)), 2)

    goal_summaries = []
    for goal in data.get("savings_goals", []):
        target = float(goal.get("target_amount", 0.0))
        saved = float(goal.get("saved_amount", 0.0))
        percent = round((saved / target) * 100, 1) if target > 0 else 0.0
        remaining = round(max(0.0, target - saved), 2)
        status = "Completed" if saved >= target else "In Progress"

        goal_summaries.append(
            {
                "name": goal["name"],
                "target_amount": target,
                "saved_amount": saved,
                "remaining_amount": remaining,
                "percent": percent,
                "status": status,
                "created_date": goal.get("created_date", "-"),
            }
        )

    return {
        "total_saved": max(0.0, total_saved_in_tx),
        "goals": goal_summaries,
    }
"""
display.py
----------
Terminal formatting helpers for displaying menus, transaction tables,
financial summaries, budget warnings, and savings progress bars.
"""


def print_line(char="-", width=78):
    """Print a horizontal divider line."""
    print(char * width)


def print_header(title):
    """Print a cleanly centered section header."""
    print()
    print_line("=")
    print(f"  {title}")
    print_line("=")


def format_currency(amount):
    """Format a number as currency (Rs. X,XXX.XX)."""
    return f"Rs. {float(amount):,.2f}"


def make_progress_bar(percent, width=22):
    """Build an ASCII progress bar like [########------------] 40.0%."""
    clamped = max(0.0, min(100.0, float(percent)))
    filled = int((clamped / 100.0) * width)
    empty = width - filled
    return f"[{'#' * filled}{'-' * empty}] {percent:.1f}%"


def display_transactions(transactions, title="TRANSACTION HISTORY"):
    """Display a formatted table of transactions."""
    print_header(title)
    if not transactions:
        print("  No transactions found matching your criteria.")
        print_line("-")
        return

    header = (
        f"{'ID':<4} | {'Date':<10} | {'Type':<8} | "
        f"{'Category':<18} | {'Amount':>12} | {'Description'}"
    )
    print(header)
    print_line("-")

    for tx in transactions:
        tx_id = tx.get("id", "-")
        date_str = tx.get("date", "-")
        tx_type = tx.get("type", "-").upper()
        category = tx.get("category", "-")[:18]
        amount_str = format_currency(tx.get("amount", 0.0))
        desc = tx.get("description", "-")
        if tx.get("goal_name"):
            desc = f"{desc} [Goal: {tx['goal_name']}]"
        if len(desc) > 32:
            desc = desc[:29] + "..."

        print(
            f"{tx_id:<4} | {date_str:<10} | {tx_type:<8} | "
            f"{category:<18} | {amount_str:>12} | {desc}"
        )

    print_line("-")
    print(f"  Total records shown: {len(transactions)}")


def display_summary(summary):
    """Display total income, total expenses, total savings, and remaining balance."""
    print_header(f"FINANCIAL SUMMARY ({summary['month']})")
    print(f"  Total Income            : {format_currency(summary['total_income'])}")
    print(f"  Total Expenses          : {format_currency(summary['total_expenses'])}")
    print(f"  Total Savings           : {format_currency(summary['total_savings'])}")
    print_line("-")
    print(f"  Net (Income - Expenses) : {format_currency(summary['net_after_expenses'])}")
    print(f"  Remaining Balance       : {format_currency(summary['remaining_balance'])}")
    print(f"  Savings Rate            : {summary['savings_rate_percent']:.1f}% of income")
    print(f"  Total Transactions      : {summary['transaction_count']}")

    if summary["expense_by_category"]:
        print("\n  Expense Breakdown by Category:")
        print_line("-", 54)
        total_exp = summary["total_expenses"]
        for category, amount in sorted(
            summary["expense_by_category"].items(), key=lambda x: x[1], reverse=True
        ):
            share = (amount / total_exp * 100) if total_exp > 0 else 0.0
            print(f"    {category:<20} : {format_currency(amount):>14} ({share:>5.1f}%)")

    if summary["income_by_category"]:
        print("\n  Income Breakdown by Category:")
        print_line("-", 54)
        for category, amount in sorted(
            summary["income_by_category"].items(), key=lambda x: x[1], reverse=True
        ):
            print(f"    {category:<20} : {format_currency(amount):>14}")

    print_line("=")


def display_budget_warnings(warnings, month):
    """Display monthly budget statuses and highlight any warning/exceeded alerts."""
    print_header(f"MONTHLY BUDGET STATUS ({month})")
    if not warnings:
        print("  No monthly budgets set yet. Use 'Set & Check Monthly Budgets' to add limits.")
        print_line("-")
        return

    for item in warnings:
        bar = make_progress_bar(item["percent"])
        print(f"  {item['scope']}")
        print(
            f"    Spent: {format_currency(item['spent'])}  /  "
            f"Limit: {format_currency(item['limit'])}   {bar}"
        )
        print(f"    Status -> {item['message']}")
        print_line("-")


def display_savings_overview(overview):
    """Display total savings and progress bars for every savings goal."""
    print_header("SAVINGS & GOALS OVERVIEW")
    print(f"  Total Net Savings Held  : {format_currency(overview['total_saved'])}")
    print_line("-")

    goals = overview.get("goals", [])
    if not goals:
        print("  No savings goals created yet.")
        print_line("-")
        return

    for idx, goal in enumerate(goals, start=1):
        bar = make_progress_bar(goal["percent"])
        print(f"  {idx}. {goal['name']} [{goal['status']}] (Created: {goal['created_date']})")
        print(
            f"     Saved: {format_currency(goal['saved_amount'])} / "
            f"Target: {format_currency(goal['target_amount'])}   {bar}"
        )
        if goal["remaining_amount"] > 0:
            print(f"     Remaining to reach goal: {format_currency(goal['remaining_amount'])}")
        else:
            print("     Congratulations! Goal target reached.")
        print_line("-")
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
"""
test_tracker.py
---------------
Automated unit tests for the Personal Expense, Budget & Savings Tracker.
Uses Python's built-in unittest, tempfile, and os modules.
"""

import os
import tempfile
import unittest

from budget import (
    check_budget_warnings,
    get_monthly_spending,
    set_category_budget,
    set_overall_budget,
)
from savings import (
    add_to_savings,
    create_savings_goal,
    get_savings_overview,
    withdraw_from_savings,
)
from storage import (
    create_backup,
    export_transactions_to_csv,
    get_default_data,
    load_data,
    save_data,
)
from tracker import (
    calculate_summary,
    delete_transaction,
    edit_transaction,
    filter_transactions,
    record_transaction,
)


class TestPersonalExpenseTracker(unittest.TestCase):
    def setUp(self):
        self.data = get_default_data()

    def test_record_income_expense_and_summary_balance(self):
        record_transaction(self.data, "income", "Allowance", 10000.0, "Home allowance", "2026-11-01")
        record_transaction(self.data, "expense", "Food", 1500.0, "Canteen meals", "2026-11-05")
        record_transaction(self.data, "expense", "Transport", 500.0, "Bus pass", "2026-11-06")

        create_savings_goal(self.data, "Emergency Fund", 5000.0, "2026-11-01")
        add_to_savings(self.data, 2000.0, "Emergency Fund", "Monthly saving", "2026-11-07")

        summary = calculate_summary(self.data)
        self.assertEqual(summary["total_income"], 10000.0)
        self.assertEqual(summary["total_expenses"], 2000.0)
        self.assertEqual(summary["total_savings"], 2000.0)
        self.assertEqual(summary["net_after_expenses"], 8000.0)
        self.assertEqual(summary["remaining_balance"], 6000.0)
        self.assertEqual(summary["savings_rate_percent"], 20.0)
        self.assertEqual(summary["expense_by_category"]["Food"], 1500.0)
        self.assertEqual(summary["expense_by_category"]["Transport"], 500.0)

    def test_filtering_transactions(self):
        record_transaction(self.data, "income", "Salary", 5000.0, "Part-time job", "2026-10-28")
        record_transaction(self.data, "expense", "Food", 300.0, "Pizza with friends", "2026-11-10")
        record_transaction(self.data, "expense", "Books & Stationery", 700.0, "Python textbook", "2026-11-12")

        nov_tx = filter_transactions(self.data["transactions"], month="2026-11")
        self.assertEqual(len(nov_tx), 2)

        food_tx = filter_transactions(self.data["transactions"], category="Food")
        self.assertEqual(len(food_tx), 1)
        self.assertEqual(food_tx[0]["amount"], 300.0)

        keyword_tx = filter_transactions(self.data["transactions"], keyword="python")
        self.assertEqual(len(keyword_tx), 1)
        self.assertEqual(keyword_tx[0]["category"], "Books & Stationery")

    def test_monthly_budget_warnings_and_exceeded_alerts(self):
        set_overall_budget(self.data, 5000.0)
        set_category_budget(self.data, "Food", 1000.0)

        record_transaction(self.data, "expense", "Food", 850.0, "Groceries", "2026-11-11")
        warnings = check_budget_warnings(self.data, month="2026-11", category="Food")
        levels = {w["scope"]: w["level"] for w in warnings}
        self.assertEqual(levels["Category 'Food'"], "WARNING")
        self.assertEqual(levels["Overall Monthly"], "OK")

        record_transaction(self.data, "expense", "Food", 300.0, "Dinner", "2026-11-12")
        record_transaction(self.data, "expense", "Rent & Hostel", 4200.0, "Hostel", "2026-11-13")

        total_spent, cat_totals = get_monthly_spending(self.data["transactions"], "2026-11")
        self.assertEqual(total_spent, 5350.0)
        self.assertEqual(cat_totals["Food"], 1150.0)

        all_warnings = check_budget_warnings(self.data, month="2026-11")
        all_levels = {w["scope"]: w["level"] for w in all_warnings}
        self.assertEqual(all_levels["Category 'Food'"], "EXCEEDED")
        self.assertEqual(all_levels["Overall Monthly"], "EXCEEDED")

    def test_savings_goals_and_withdrawal(self):
        record_transaction(self.data, "income", "Allowance", 8000.0, "Allowance", "2026-11-01")
        create_savings_goal(self.data, "New Laptop", 10000.0, "2026-11-01")
        add_to_savings(self.data, 4000.0, "New Laptop", "Deposit 1", "2026-11-05")

        overview = get_savings_overview(self.data)
        self.assertEqual(overview["total_saved"], 4000.0)
        self.assertEqual(overview["goals"][0]["percent"], 40.0)

        withdraw_from_savings(self.data, 1000.0, "New Laptop", "Book fee", "2026-11-10")
        overview_after = get_savings_overview(self.data)
        self.assertEqual(overview_after["total_saved"], 3000.0)
        self.assertEqual(overview_after["goals"][0]["saved_amount"], 3000.0)

        summary = calculate_summary(self.data)
        self.assertEqual(summary["total_savings"], 3000.0)
        self.assertEqual(summary["remaining_balance"], 5000.0)

    def test_edit_and_delete_transaction(self):
        tx = record_transaction(self.data, "expense", "Food", 200.0, "Snacks", "2026-11-15")
        edited, updated = edit_transaction(self.data, tx["id"], new_amount=250.0, new_description="Lunch")
        self.assertTrue(edited)
        self.assertEqual(updated["amount"], 250.0)
        self.assertEqual(updated["description"], "Lunch")

        deleted, removed = delete_transaction(self.data, tx["id"])
        self.assertTrue(deleted)
        self.assertEqual(removed["id"], tx["id"])
        self.assertEqual(len(self.data["transactions"]), 0)

    def test_permanent_file_save_load_csv_and_backup(self):
        record_transaction(self.data, "income", "Scholarship", 6000.0, "Merit scholarship", "2026-11-01")
        record_transaction(self.data, "expense", "Food", 450.0, "Lunch", "2026-11-02")
        set_overall_budget(self.data, 4000.0)

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = os.path.join(tmpdir, "expense_data.json")
            csv_path = os.path.join(tmpdir, "export.csv")
            backup_dir = os.path.join(tmpdir, "backups")

            self.assertTrue(save_data(self.data, json_path))
            reloaded = load_data(json_path)
            self.assertEqual(len(reloaded["transactions"]), 2)
            self.assertEqual(reloaded["budgets"]["overall_monthly"], 4000.0)

            csv_ok, out_csv = export_transactions_to_csv(reloaded["transactions"], csv_path)
            self.assertTrue(csv_ok)
            self.assertTrue(os.path.exists(out_csv))

            backup_ok, backup_file = create_backup(json_path, backup_dir)
            self.assertTrue(backup_ok)
            self.assertTrue(os.path.exists(backup_file))


if __name__ == "__main__":
    unittest.main()
