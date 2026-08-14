from overlord.modules.validation import FieldValidationError


def require_definition_of_done(value: str | None, *, context: str) -> str:
    clean = (value or "").strip()
    if not clean:
        raise FieldValidationError(
            "definition_of_done",
            "required",
            f"Definition of Done is required before {context}.",
        )
    return clean
