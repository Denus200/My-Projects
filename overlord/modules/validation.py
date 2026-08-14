from __future__ import annotations


class FieldValidationError(ValueError):
    """Validation failure with stable metadata for presentation routing."""

    __slots__ = ("field", "code")

    def __init__(self, field: str, code: str, message: str):
        super().__init__(message)
        self.field = field
        self.code = code
