"""
scanner/scanner.py — Rule-based secret scanner

Orchestrates the two rule-based detection layers:
  1. Regex pattern matching  (scanner/patterns.py)
  2. Shannon entropy analysis (scanner/entropy.py)

The ML model sits in services/secret_service.py and runs *after* this layer.
Both results are merged in the route handler to form the final API response.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from scanner.patterns import PATTERNS
from scanner.entropy import find_high_entropy_tokens
from models.schemas import RuleMatch


@dataclass
class RuleScanResult:
    """Aggregated output from the rule-based scanning pass."""
    rule_matches: list[RuleMatch] = field(default_factory=list)
    entropy_flags: list[str] = field(default_factory=list)

    @property
    def has_findings(self) -> bool:
        return bool(self.rule_matches or self.entropy_flags)


def run_rule_scan(text: str) -> RuleScanResult:
    """
    Run all rule-based scans against *text* and return a RuleScanResult.

    Parameters
    ----------
    text: The raw code or text to scan.

    Returns
    -------
    RuleScanResult containing any regex matches and high-entropy tokens found.
    """
    result = RuleScanResult()
    lines = text.splitlines()

    # ── 1. Regex pattern scan (line by line) ──────────────────────────────────
    seen_matches: set[str] = set()
    for line_no, line in enumerate(lines, start=1):
        for rule in PATTERNS:
            matches = rule.pattern.findall(line)
            for match in matches:
                # findall can return str or tuple (for groups) — normalise
                matched_str = match if isinstance(match, str) else (match[-1] if match else "")
                if not matched_str or matched_str in seen_matches:
                    continue
                seen_matches.add(matched_str)

                # Redact the middle of long secrets in the response
                display = _redact(matched_str)
                result.rule_matches.append(
                    RuleMatch(
                        secret_type=rule.name,
                        matched_value=display,
                        line_number=line_no,
                    )
                )

    # ── 2. Shannon entropy scan (whole text) ─────────────────────────────────
    result.entropy_flags = find_high_entropy_tokens(text)

    return result


def _redact(value: str, keep: int = 4) -> str:
    """
    Partially redact a secret value for safe API display.

    Example: "ghp_abcdefghijklmnopqrstuvwxyz123456" → "ghp_****...****3456"
    """
    if len(value) <= keep * 2:
        return "****"
    return f"{value[:keep]}{'*' * min(len(value) - keep * 2, 8)}{value[-keep:]}"
