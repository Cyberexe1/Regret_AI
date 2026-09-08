"""Placeholder identity resolution.

There is no authentication system yet. Every request is currently
attributed to a single fixed user id (from configuration) so that the data
model and access patterns are already user-scoped - swapping this for a
real "who is calling" resolver (JWT, session, etc.) later should only mean
changing this one function, not every place that currently calls it.
"""

from app.core.config import get_settings


def get_current_user_id() -> str:
    """Return the id of the "current user" for this request.

    Always returns the configured placeholder user id until real
    authentication exists.
    """
    return get_settings().default_user_id
