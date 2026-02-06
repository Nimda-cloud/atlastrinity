import re


def mask_sensitive_data(text: str) -> str:
    """Masks sensitive data (passwords, API keys, SSH credentials, tokens) in text.

    Combining patterns from Agent logic and Logging filters for project-wide consistency.
    """
    if not isinstance(text, str):
        return text

    sensitive_patterns = [
        # Keywords based masking
        (
            r"(password|passwd|pwd|apikey|token|secret|sshpass)[:\s=]+([^\s\n\"']+)",
            r"\1=****MASKED****",
        ),
        (r"-p\s+([^\s\n\"']+)", r"-p ****MASKED****"),
        (r"--password[:\s=]+([^\s\n\"']+)", r"--password=****MASKED****"),
        # Hardcoded patterns
        (r"gh[up]_[a-zA-Z0-9]{30,60}", "****MASKED_GH_TOKEN****"),
        (r"AIzaSy[a-zA-Z0-9_-]{33}", "****MASKED_GOOGLE_KEY****"),
        (r"Bearer\s+[a-zA-Z0-9._-]+", "Bearer ****MASKED_TOKEN****"),
        # Generic long character sequences often used as passwords/keys
        (r"(?<!\w)(?:[A-Za-z0-9@#$%^&+=]{16,})(?!\w)", "****MASKED_SECRET****"),
        # Identity
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "****MASKED_EMAIL****"),
        (r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "****MASKED_CC****"),
    ]

    masked_text = text
    for pattern, replacement in sensitive_patterns:
        # Use simple replacement or regex substitution
        if replacement.startswith("****"):
            masked_text = re.sub(pattern, replacement, masked_text, flags=re.IGNORECASE)
        else:
            # For keyword-based, we want to keep the label
            masked_text = re.sub(pattern, replacement, masked_text, flags=re.IGNORECASE)

    return masked_text
