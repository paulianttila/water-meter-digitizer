from functools import wraps
import logging
import time

logger = logging.getLogger(__name__)


def log_execution_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        logger.debug(
            f"Function {func.__name__}{args} {kwargs} "
            f"Took {end_time - start_time:.4f} sec"
        )
        return result

    return wrapper
