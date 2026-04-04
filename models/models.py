"""
models/models.py
All data models (SQLite tables) via Peewee ORM.

IMPORTANT: all amounts are stored in CENTS (integer).
Display: amount_cents / 100
Save:    round(float_amount * 100)
"""

from datetime import date, datetime
from peewee import (
    Model, AutoField, IntegerField, TextField,
    BooleanField, ForeignKeyField, DateField, DateTimeField
)
from db.database import db


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    """Local user profile."""
    id            = AutoField()
    name          = TextField()
    password_hash = TextField(default="")       # bcrypt hash or empty string
    currency      = TextField(default="USD")    # "USD" | "EUR" | "RUB" | "ILS"
    month_start   = IntegerField(default=1)     # Budget month start day (1–28)
    language = TextField(default="en")
    created_at    = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "users"


class Category(BaseModel):
    """Transaction category. user=NULL means it's a built-in system category."""
    id          = AutoField()
    user        = ForeignKeyField(User, backref="categories", null=True, on_delete="CASCADE")
    name        = TextField()
    icon        = TextField(default="💳")       # Emoji or icon filename
    color       = TextField(default="#64748B")  # HEX color for charts
    type        = TextField(default="expense")  # "income" | "expense"
    is_archived = BooleanField(default=False)

    class Meta:
        table_name = "categories"


class Transaction(BaseModel):
    """A single income or expense record."""
    id           = AutoField()
    user         = ForeignKeyField(User, backref="transactions", on_delete="CASCADE")
    type         = TextField()                  # "income" | "expense"
    amount_cents = IntegerField()               # !! CENTS, not float
    category     = ForeignKeyField(Category, backref="transactions", null=True, on_delete="SET NULL")
    date         = DateField(default=date.today)
    note         = TextField(default="")
    created_at   = DateTimeField(default=datetime.now)
    is_recurring = BooleanField(default=False)

    class Meta:
        table_name = "transactions"


class Budget(BaseModel):
    """Spending limit for a category in a specific month."""
    id           = AutoField()
    user         = ForeignKeyField(User, backref="budgets", on_delete="CASCADE")
    category     = ForeignKeyField(Category, backref="budgets", on_delete="CASCADE")
    period_year  = IntegerField()
    period_month = IntegerField()               # 1–12
    limit_cents  = IntegerField()               # !! CENTS

    class Meta:
        table_name = "budgets"
        indexes    = ((("user", "category", "period_year", "period_month"), True),)  # Unique constraint


class Goal(BaseModel):
    """A savings goal."""
    id            = AutoField()
    user          = ForeignKeyField(User, backref="goals", on_delete="CASCADE")
    name          = TextField()
    icon          = TextField(default="🎯")
    target_cents  = IntegerField()              # Target amount in cents
    current_cents = IntegerField(default=0)     # Amount saved so far in cents
    deadline      = DateField(null=True)        # Optional target date
    status        = TextField(default="active") # "active" | "completed" | "archived"
    created_at    = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "goals"


# ── v1.8.0 — Tags ────────────────────────────────────────────────────────────

class Tag(BaseModel):
    """A user-defined tag for transactions (e.g. #vacation, #work)."""
    id   = AutoField()
    user = ForeignKeyField(User, backref="tags", on_delete="CASCADE")
    name = TextField()  # stored without '#', e.g. "vacation"

    class Meta:
        table_name = "tags"
        indexes = ((("user", "name"), True),)  # unique per user


class TransactionTag(BaseModel):
    """Many-to-many junction: transaction ↔ tag."""
    id          = AutoField()
    transaction = ForeignKeyField(Transaction, backref="transaction_tags", on_delete="CASCADE")
    tag         = ForeignKeyField(Tag, backref="transaction_tags", on_delete="CASCADE")

    class Meta:
        table_name = "transaction_tags"
        indexes = ((("transaction", "tag"), True),)


ALL_MODELS = [User, Category, Transaction, Budget, Goal, Tag, TransactionTag]
