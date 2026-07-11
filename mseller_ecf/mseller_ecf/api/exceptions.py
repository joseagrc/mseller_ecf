class MSellerECFError(Exception):
    """Base exception for MSeller ECF integration errors."""


class MSellerECFConfigurationError(MSellerECFError):
    """Raised when integration settings are incomplete or invalid."""


class MSellerECFAuthenticationError(MSellerECFError):
    """Raised when MSeller authentication fails."""


class MSellerECFRequestError(MSellerECFError):
    """Raised when MSeller API returns an unexpected response."""

    def __init__(self, message, status_code=None, response_text=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text
