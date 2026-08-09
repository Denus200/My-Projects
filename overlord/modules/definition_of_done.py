def require_definition_of_done(value: str | None, *, context: str) -> str:
    clean = (value or "").strip()
    if not clean:
        raise ValueError(f"Definition of Done is required before {context}.")
    return clean
