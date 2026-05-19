"""Daily scheduling boundary."""
from collections.abc import Callable


def run_once(job: Callable[[], None]) -> None:
    """Run a scheduled job once."""
    job()
