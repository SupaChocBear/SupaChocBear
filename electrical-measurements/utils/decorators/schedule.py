"""
utils/decorators/schedule.py
============================
Lightweight @schedule() decorator.

When called directly (python electrical_data_loader.py) the decorated
function runs immediately.

When run as a scheduled job the decorator can be extended to use
APScheduler or a cron trigger — for now it just executes the function
once and returns its result so the data loader stays self-contained.
"""

import functools
from typing import Callable


def schedule(interval_seconds: int = 0):
    """
    Decorator factory.

    Parameters
    ----------
    interval_seconds : int
        How often to re-run the function (0 = run once and return).
        Extend this with APScheduler if you need periodic execution.

    Usage
    -----
    @schedule()
    def get_data():
        ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator
