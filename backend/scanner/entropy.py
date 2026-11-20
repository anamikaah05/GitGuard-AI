"""
scanner/entropy.py — Shannon entropy analysis for secret detection

High-entropy strings are a strong indicator of encoded secrets (e.g., base64
API keys, random tokens). This module tokenises input text, computes per-token
entropy, and returns tokens that exceed a configurable threshold.

Shannon entropy formula:
    H(X) = -Σ p(x) * log2(p(x))

A perfectly random string of printable ASCII has entropy ≈ 6.5 bits/char.
Typical English prose has entropy ≈ 3.5–4.0 bits/char.
We flag tokens with entropy > 4.5 bits/char (tuned for low false-positive rate).
"""

from __future__ import annotations

import math
import re
from collections import Counter

# Characters common in secrets (base64, hex, alphanumeric)
_ALPHABET = re.compile(r"[A-Za-z0-9+/=_\-]{16,}")

# Minimum entropy threshold (bits per character) to flag a token
ENTROPY_THRESHOLD: float = 4.5

# Minimum token length to consider (short tokens produce unreliable entropy)
MIN_TOKEN_LENGTH: int = 16


def shannon_entropy(token: str) -> float:
    """
    Calculate the Shannon entropy of *token* in bits per character.

    Returns 0.0 for empty strings.
    """
    if not token:
        return 0.0

    freq = Counter(token)
    length = len(token)
    entropy = -sum(
        (count / length) * math.log2(count / length)
        for count in freq.values()
    )
    return round(entropy, 4)


def find_high_entropy_tokens(text: str, threshold: float = ENTROPY_THRESHOLD) -> list[str]:
    """
    Scan *text* and return a list of high-entropy substrings that may be secrets.

    Parameters
    ----------
    text:      The raw code or text to analyse.
    threshold: Entropy bits/char above which a token is flagged (default 4.5).

    Returns
    -------
    A deduplicated list of flagged token strings, ordered by descending entropy.
    """
    candidates = _ALPHABET.findall(text)

    flagged: dict[str, float] = {}
    for token in candidates:
        if len(token) < MIN_TOKEN_LENGTH:
            continue
        h = shannon_entropy(token)
        if h >= threshold:
            flagged[token] = h

    # Sort by entropy descending, return unique tokens
    return [tok for tok, _ in sorted(flagged.items(), key=lambda x: x[1], reverse=True)]
