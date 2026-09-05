from functools import wraps
import inspect
import logging
import time

logger = logging.getLogger(__name__)


def log_execution_time(func):
    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            result = await func(*args, **kwargs)
            end_time = time.perf_counter()
            logger.debug(
                f"Function {func.__name__}{args} {kwargs} "
                f"Took {end_time - start_time:.4f} sec"
            )
            return result

        return async_wrapper
    else:

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            logger.debug(
                f"Function {func.__name__}{args} {kwargs} "
                f"Took {end_time - start_time:.4f} sec"
            )
            return result

        return sync_wrapper
