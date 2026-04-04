"""
services/tag_service.py
Business logic for transaction tags.
Tags are user-scoped strings like "vacation", "work", "gift".
Stored without '#' — the UI adds it for display.
"""

import logging
from db.database import db
from models.models import Tag, TransactionTag, Transaction

logger = logging.getLogger(__name__)


def get_or_create_tag(user, name: str) -> Tag:
    """
    Returns an existing tag or creates a new one.
    Tag names are case-insensitive and stripped of '#'.
    """
    clean = name.strip().lstrip("#").strip().lower()
    if not clean:
        raise ValueError("Tag name cannot be empty")

    with db:
        tag, created = Tag.get_or_create(
            user=user,
            name=clean,
        )
    if created:
        logger.info(f"Created tag '{clean}'")
    return tag


def get_all_tags(user) -> list[Tag]:
    """Returns all tags for a user, sorted alphabetically."""
    return list(
        Tag.select()
        .where(Tag.user == user)
        .order_by(Tag.name)
    )


def delete_tag(tag: Tag) -> None:
    """Deletes a tag and all its associations."""
    with db:
        TransactionTag.delete().where(TransactionTag.tag == tag).execute()
        tag.delete_instance()
    logger.info(f"Deleted tag '{tag.name}'")


def set_transaction_tags(transaction: Transaction, user, tag_names: list[str]) -> list[Tag]:
    """
    Replaces all tags on a transaction with the given list.
    Creates new tags as needed.

    Usage:
        set_transaction_tags(tx, user, ["vacation", "fun"])
    """
    with db:
        # Remove existing tags
        TransactionTag.delete().where(
            TransactionTag.transaction == transaction
        ).execute()

        # Add new tags
        tags = []
        for name in tag_names:
            clean = name.strip().lstrip("#").strip().lower()
            if not clean:
                continue
            tag = get_or_create_tag(user, clean)
            TransactionTag.create(transaction=transaction, tag=tag)
            tags.append(tag)

    return tags


def get_transaction_tags(transaction: Transaction) -> list[Tag]:
    """Returns all tags for a transaction."""
    return list(
        Tag.select()
        .join(TransactionTag)
        .where(TransactionTag.transaction == transaction)
        .order_by(Tag.name)
    )


def get_transactions_by_tag(user, tag_name: str) -> list[int]:
    """
    Returns transaction IDs that have a given tag.
    Used for filtering.
    """
    clean = tag_name.strip().lstrip("#").strip().lower()
    tag = Tag.select().where(Tag.user == user, Tag.name == clean).first()
    if not tag:
        return []

    return [
        tt.transaction_id
        for tt in TransactionTag.select().where(TransactionTag.tag == tag)
    ]


def parse_tags_string(text: str) -> list[str]:
    """
    Parses a tag input string into a list of clean tag names.
    Supports: "#vacation #work" or "vacation, work" or "vacation work"

    Returns: ["vacation", "work"]
    """
    # Replace commas with spaces, then split
    text = text.replace(",", " ")
    parts = text.split()

    tags = []
    for part in parts:
        clean = part.strip().lstrip("#").strip().lower()
        if clean and clean not in tags:
            tags.append(clean)

    return tags


def format_tags_display(tags: list[Tag]) -> str:
    """Formats tags for display: ['vacation', 'work'] → '#vacation #work'"""
    return " ".join(f"#{t.name}" for t in tags)


def format_tags_edit(tags: list[Tag]) -> str:
    """Formats tags for editing (same as display but used in entry fields)."""
    return " ".join(f"#{t.name}" for t in tags)
