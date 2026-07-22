"""Excepciones tipadas del módulo lottery."""

from __future__ import annotations

from fastapi import HTTPException, status


class LotteryQueryError(Exception):
    def __init__(self, code: str, message: str, *, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_http(self) -> HTTPException:
        mapping = {
            "LOTTERY_NOT_FOUND": status.HTTP_404_NOT_FOUND,
            "LOTTERY_AMBIGUOUS": status.HTTP_409_CONFLICT,
            "LOTTERY_PENDING_MAPPING": status.HTTP_409_CONFLICT,
            "DATE_INVALID": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "RANGE_INVALID": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "RANGE_TOO_LARGE": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "COUNT_INVALID": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "NUMBER_INVALID": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "NO_RESULTS": status.HTTP_404_NOT_FOUND,
            "MODULE_DISABLED": status.HTTP_403_FORBIDDEN,
            "FORBIDDEN": status.HTTP_403_FORBIDDEN,
        }
        return HTTPException(
            status_code=mapping.get(self.code, status.HTTP_400_BAD_REQUEST),
            detail={"code": self.code, "message": self.message, "details": self.details},
        )
