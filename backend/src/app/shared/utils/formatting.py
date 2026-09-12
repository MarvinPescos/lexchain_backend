# keep plaintext addresses out of the log stream.
def _mask_email(email: str | None) -> str:
    if not email or "@" not in email:
        return "<unknown>"
    local, _, domain = email.partition("@")
    return f"{local[0]}***@{domain}"
