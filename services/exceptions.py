class LLMError(Exception):
    """Base exception for LLM service."""
    pass

class LLMConnectionError(LLMError):
    """Raised when connection to LLM provider fails."""
    pass

class LLMTimeoutError(LLMError):
    """Raised when connection to LLM provider times out."""
    pass

class LLMRateLimitError(LLMError):
    """Raised when rate limit is exceeded."""
    pass

class LLMAuthenticationError(LLMError):
    """Raised when authentication with LLM provider fails."""
    pass

class LLMResponseError(LLMError):
    """Raised when LLM provider returns an invalid or error response."""
    pass
