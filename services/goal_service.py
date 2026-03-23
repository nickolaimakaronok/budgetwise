"""
services/goal_service.py
Business logic for savings goals.
Extracted from ui/pages/goals.py to follow the services architecture pattern.
UI never touches the database directly — it only calls functions from here.
"""

import logging
from db.database import db
from models.models import Goal

logger = logging.getLogger(__name__)


def get_goals(user) -> list[Goal]:
    goals = list(Goal.select().where(
        Goal.user == user,
        Goal.status.in_(["active", "completed"]),
    ).order_by(Goal.created_at.desc()))
    return goals


def add_goal(user, name: str, target_cents: int, icon: str = "🎯") -> Goal:
    """
    Creates and saves a new savings goal.

    Usage:
        goal = add_goal(user, "Japan Trip", 200000, icon="✈️")
    """
    if not name.strip():
        raise ValueError("Goal name cannot be empty")
    if target_cents <= 0:
        raise ValueError("Target amount must be greater than zero")

    with db:
        goal = Goal.create(
            user=user,
            name=name.strip(),
            target_cents=target_cents,
            icon=icon,
        )
    logger.info(f"Created goal '{name}' with target {target_cents} cents")
    return goal


def contribute_to_goal(goal: Goal, amount_cents: int) -> Goal:
    """
    Adds an amount to a goal's current savings.
    Automatically marks the goal as completed if target is reached.

    Usage:
        contribute_to_goal(goal, 50000)  # add 500.00
    """
    if amount_cents <= 0:
        raise ValueError("Contribution amount must be greater than zero")

    with db:
        goal.current_cents += amount_cents
        if goal.current_cents >= goal.target_cents:
            goal.status = "completed"
            logger.info(f"Goal '{goal.name}' completed!")
        goal.save()

    logger.debug(f"Contributed {amount_cents} cents to goal '{goal.name}'")
    return goal


def archive_goal(goal: Goal) -> Goal:
    """
    Soft-deletes a goal by setting its status to 'archived'.
    The goal remains in the database but won't appear in the active list.

    Usage:
        archive_goal(goal)
    """
    with db:
        goal.status = "archived"
        goal.save()
    logger.info(f"Archived goal '{goal.name}'")
    return goal


def get_completed_goals(user) -> list[Goal]:
    """Returns all completed goals for a user."""
    return list(Goal.select().where(
        Goal.user == user,
        Goal.status == "completed",
    ).order_by(Goal.created_at.desc()))


def get_goal_progress(goal: Goal) -> dict:
    """
    Returns progress information for a goal.

    Returns:
        {
            "percent":         42.0,
            "remaining_cents": 116000,
            "is_completed":    False,
        }
    """
    pct = min(goal.current_cents / goal.target_cents * 100, 100.0) if goal.target_cents > 0 else 0.0
    return {
        "percent":         round(pct, 1),
        "remaining_cents": max(0, goal.target_cents - goal.current_cents),
        "is_completed":    goal.current_cents >= goal.target_cents,
    }