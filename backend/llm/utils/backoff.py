# llm/utils/backoff.py
import random
import time
from functools import wraps


def retry_with_exponential_backoff(
    errors,
    initial_delay: float = 1,
    exponential_base: float = 2,
    jitter: bool = True,
    max_retries: int = 5,
):
    """
    Parameterized decorator:
      @retry_with_exponential_backoff((SomeError, OtherError), max_retries=5)
      def fn(...): ...
    """
    # Accept single exception class too
    if not isinstance(errors, tuple):
        errors = (errors,)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            attempts = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except errors as e:
                    print(f"Error: {e} - Attempt {attempts + 1} of {max_retries}")
                    attempts += 1
                    if attempts > max_retries:
                        print(f"Max retries reached. Raising exception.")
                        raise e
                    sleep_for = delay * (1 + random.random() if jitter else 1)
                    time.sleep(sleep_for)
                    delay *= exponential_base

        return wrapper

    return decorator
