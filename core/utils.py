"""Utility functions for URL domain extraction and directory management."""

import re
from pathlib import Path
from urllib.parse import urlparse


def extract_domain_name(url: str) -> str:
    """Extract a clean, sanitized snake_case domain name from a URL.

    Examples:
        - https://www.saucedemo.com -> saucedemo
        - https://saucedemo.com/inventory -> saucedemo
        - http://localhost:3000 -> localhost
        - https://sub.saucedemo.com -> saucedemo
        - https://ecommerce.co.uk/checkout -> ecommerce

    Args:
        url: Full web application URL.

    Returns:
        Sanitized domain string suitable for directory and package names.
    """
    if not url:
        return "default"

    parsed = urlparse(url)
    netloc = parsed.netloc or parsed.path.split("/")[0]
    host = netloc.split(":")[0].lower()

    if host.startswith("www."):
        host = host[4:]

    parts = [p for p in host.split(".") if p]

    if len(parts) >= 2:
        if parts[-2] in ("co", "com", "org", "net", "gov", "edu") and len(parts) >= 3:
            domain = parts[-3]
        else:
            domain = parts[0] if len(parts) == 2 else parts[-2]
    elif parts:
        domain = parts[0]
    else:
        domain = "default"

    sanitized = re.sub(r"[^\w]", "_", domain).strip("_").lower()
    return sanitized or "default"


def ensure_package_dir(path: Path) -> Path:
    """Ensure directory exists and contains an __init__.py file.

    Args:
        path: Path object to directory.

    Returns:
        The ensured Path object.
    """
    path.mkdir(parents=True, exist_ok=True)
    init_file = path / "__init__.py"
    if not init_file.exists():
        init_file.write_text(f'"""Package for {path.name} components."""\n', encoding="utf-8")
    return path
