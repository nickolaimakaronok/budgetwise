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


def get_goal_deadline_info(goal) -> dict:
    """
    Calculates deadline information for a goal.

    Returns:
        {
            "has_deadline":       True/False,
            "days_left":          68,
            "months_left":        2.3,
            "needed_per_month":   580,   # cents — how much to save each month
            "is_overdue":         False,
        }
    """
    from datetime import date as date_type
    import math

    if not goal.deadline:
        return {
            "has_deadline":      False,
            "days_left":         None,
            "months_left":       None,
            "needed_per_month":  None,
            "is_overdue":        False,
        }

    today          = date_type.today()
    days_left      = (goal.deadline - today).days
    is_overdue     = days_left < 0
    months_left    = max(days_left / 30.44, 0)  # 30.44 = average days in month
    remaining      = max(goal.target_cents - goal.current_cents, 0)

    # How much to save per month to reach goal in time
    if months_left > 0 and remaining > 0:
        needed_per_month = math.ceil(remaining / months_left)
    else:
        needed_per_month = remaining  # pay it all now

    logger.debug(
        f"Goal '{goal.name}' deadline: {days_left} days left, "
        f"need {needed_per_month} cents/month"
    )

    return {
        "has_deadline":      True,
        "days_left":         days_left,
        "months_left":       round(months_left, 1),
        "needed_per_month":  needed_per_month,
        "is_overdue":        is_overdue,
    }


def add_goal(user, name: str, target_cents: int,
             icon: str = "🎯", deadline=None) -> Goal:
    """Creates and saves a new savings goal."""
    if not name.strip():
        raise ValueError("Goal name cannot be empty")
    if target_cents <= 0:
        raise ValueError("Target amount must be greater than zero")

    with db:
        goal = Goal.create(
            user         = user,
            name         = name.strip(),
            target_cents = target_cents,
            icon         = icon,
            deadline     = deadline,
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