import logging
import time
from functools import wraps
from typing import Callable, Any


def configure_logging() -> None:
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler("app.log")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(console_handler)


def log_time(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(url: str, *args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        result = func(url, *args, **kwargs)
        elapsed_time = time.time() - start_time
        logging.info(
            f"Time taken by {func.__name__} "
            f"for {url}: {elapsed_time:.2f} seconds"
        )
        return result

    return wrapper
