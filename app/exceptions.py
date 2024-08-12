class HTTPResponseError(Exception):
    def __init__(self, url: str, status_code: int) -> None:
        super().__init__(
            f"Error getting page: {url}, status code: {status_code}"
        )
