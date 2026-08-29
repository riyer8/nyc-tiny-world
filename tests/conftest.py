"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import warnings

# urllib3 warns on import with macOS system Python (LibreSSL vs OpenSSL).
warnings.filterwarnings(
    "ignore",
    message=r"urllib3 v2 only supports OpenSSL.*",
)
