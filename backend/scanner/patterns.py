"""
scanner/patterns.py — Regex-based secret pattern definitions

Each entry in PATTERNS is a dict with:
  - name:    Human-readable category label (shown in API response)
  - pattern: Compiled regex that matches the secret value

Sources / inspiration:
  - GitHub Secret Scanning patterns
  - TruffleHog rules
  - gitleaks default ruleset
"""

import re
from typing import NamedTuple


class PatternRule(NamedTuple):
    name: str
    pattern: re.Pattern


PATTERNS: list[PatternRule] = [
    # ── GitHub ───────────────────────────────────────────────────────────────
    PatternRule("GitHub Personal Access Token (Classic)", re.compile(r"ghp_[0-9a-zA-Z]{36}")),
    PatternRule("GitHub Fine-Grained Token", re.compile(r"github_pat_[0-9a-zA-Z_]{82}")),
    PatternRule("GitHub OAuth Token", re.compile(r"gho_[0-9a-zA-Z]{36}")),
    PatternRule("GitHub App Token", re.compile(r"ghs_[0-9a-zA-Z]{36}")),

    # ── AWS ──────────────────────────────────────────────────────────────────
    PatternRule("AWS Access Key ID", re.compile(r"(?<![A-Z0-9])(AKIA|ASIA|ABIA|ACCA)[0-9A-Z]{16}(?![A-Z0-9])")),
    PatternRule("AWS Secret Access Key", re.compile(r"(?i)aws.{0,20}secret.{0,20}['\"]?([0-9a-zA-Z/+]{40})['\"]?")),

    # ── OpenAI ───────────────────────────────────────────────────────────────
    PatternRule("OpenAI API Key", re.compile(r"sk-[a-zA-Z0-9]{48}")),
    PatternRule("OpenAI Project Key", re.compile(r"sk-proj-[a-zA-Z0-9_-]{100,}")),

    # ── Slack ─────────────────────────────────────────────────────────────────
    PatternRule("Slack Bot Token", re.compile(r"xoxb-[0-9]{11}-[0-9]{11}-[0-9a-zA-Z]{24}")),
    PatternRule("Slack User Token", re.compile(r"xoxp-[0-9]{11}-[0-9]{11}-[0-9]{11}-[0-9a-f]{32}")),
    PatternRule("Slack Webhook URL", re.compile(r"https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[a-zA-Z0-9]+")),

    # ── Google ────────────────────────────────────────────────────────────────
    PatternRule("Google API Key", re.compile(r"AIza[0-9A-Za-z_-]{35}")),
    PatternRule("Google OAuth Client Secret", re.compile(r"GOCSPX-[0-9A-Za-z_-]{28}")),

    # ── Generic / common patterns ─────────────────────────────────────────────
    PatternRule("Generic API Key assignment", re.compile(
        r"(?i)(api[_\-]?key|api[_\-]?secret|access[_\-]?token)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{20,})['\"]?"
    )),
    PatternRule("Generic Password assignment", re.compile(
        r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]?([^\s'\"]{8,})['\"]?"
    )),
    PatternRule("Generic Secret assignment", re.compile(
        r"(?i)(secret|private[_\-]?key)\s*[:=]\s*['\"]?([A-Za-z0-9+/=_\-]{16,})['\"]?"
    )),

    # ── Database connection strings ────────────────────────────────────────────
    PatternRule("Database Connection String (with password)", re.compile(
        r"(?i)(mysql|postgres|mongodb|redis|mssql)://[^:]+:[^@]+@"
    )),

    # ── Private keys ──────────────────────────────────────────────────────────
    PatternRule("RSA/EC Private Key", re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    PatternRule("PGP Private Key", re.compile(r"-----BEGIN PGP PRIVATE KEY BLOCK-----")),

    # ── JWT ──────────────────────────────────────────────────────────────────
    PatternRule("JWT Token", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),

    # ── HuggingFace ───────────────────────────────────────────────────────────
    PatternRule("HuggingFace API Token", re.compile(r"hf_[a-zA-Z0-9]{34}")),

    # ── SendGrid ──────────────────────────────────────────────────────────────
    PatternRule("SendGrid API Key", re.compile(r"SG\.[a-zA-Z0-9_-]{22}\.[a-zA-Z0-9_-]{43}")),

    # ── Stripe ────────────────────────────────────────────────────────────────
    PatternRule("Stripe Secret Key", re.compile(r"sk_(live|test)_[0-9a-zA-Z]{24}")),
    PatternRule("Stripe Publishable Key", re.compile(r"pk_(live|test)_[0-9a-zA-Z]{24}")),
]
