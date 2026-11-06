class ModelServerRateLimitError(Exception):
    """
    Exception raised for rate limiting errors from the model server.
    """


class ModelServerConcurrencyLimitError(Exception):
    """
    Exception raised when the model server rejects the request with a 503,
    e.g. Uvicorn's "Exceeded concurrency limit".
    """


class CohereBillingLimitError(Exception):
    """
    Raised when Cohere rejects requests because the billing cap is reached.
    """
