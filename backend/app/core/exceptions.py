from fastapi import HTTPException, status


class JAIOSException(Exception):
    """Base application exception."""

    def __init__(self, message: str, code: str = "JAIOS_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class AuthenticationError(JAIOSException):
    pass


class AuthorizationError(JAIOSException):
    pass


class TenantNotFoundError(JAIOSException):
    pass


class LLMProviderError(JAIOSException):
    pass


class IntegrationError(JAIOSException):
    pass


def unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def forbidden(detail: str = "Not authorized") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def not_found(detail: str = "Resource not found") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
