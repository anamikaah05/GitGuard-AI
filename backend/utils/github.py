"""
utils/github.py — GitHub REST API helpers

Provides async functions to:
  - Fetch the raw diff text for a Pull Request
  - Fetch raw file content from a repository

All requests are made with httpx (async) and use the GITHUB_TOKEN from
settings for authentication. Rate-limit and error handling is included.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

import httpx

from core.config import settings
from core.exceptions import GitHubAPIError, InvalidInputError

logger = logging.getLogger(__name__)

_GITHUB_API = "https://api.github.com"
_PR_URL_RE = re.compile(
    r"https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)",
    re.IGNORECASE,
)


def _auth_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


def _diff_headers() -> dict[str, str]:
    headers = _auth_headers()
    headers["Accept"] = "application/vnd.github.diff"
    return headers


def parse_pr_url(pr_url: str) -> tuple[str, str, int]:
    """
    Extract (owner, repo, pr_number) from a GitHub PR URL.

    Raises InvalidInputError if the URL format is not recognised.
    """
    match = _PR_URL_RE.match(pr_url.strip())
    if not match:
        raise InvalidInputError(
            f"Invalid GitHub PR URL: '{pr_url}'. "
            "Expected format: https://github.com/<owner>/<repo>/pull/<number>"
        )
    return match.group("owner"), match.group("repo"), int(match.group("number"))


async def fetch_pr_diff(pr_url: str) -> str:
    """
    Fetch the unified diff for a GitHub Pull Request.

    Parameters
    ----------
    pr_url: Full GitHub PR URL (e.g., https://github.com/owner/repo/pull/42).

    Returns
    -------
    Raw unified diff text as a string.

    Raises
    ------
    InvalidInputError: If the PR URL is malformed.
    GitHubAPIError:    If the GitHub API returns a non-200 response.
    """
    owner, repo, number = parse_pr_url(pr_url)
    api_url = f"{_GITHUB_API}/repos/{owner}/{repo}/pulls/{number}"

    logger.info("Fetching PR diff from %s", api_url)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(api_url, headers=_diff_headers())

    if response.status_code == 404:
        raise GitHubAPIError(
            f"PR not found: {pr_url}. "
            "Check that the repository is public or your GITHUB_TOKEN has access."
        )
    if response.status_code == 403:
        raise GitHubAPIError(
            "GitHub API rate limit exceeded or insufficient token permissions. "
            "Set a valid GITHUB_TOKEN in .env to increase rate limits."
        )
    if response.status_code != 200:
        raise GitHubAPIError(
            f"GitHub API returned HTTP {response.status_code} for {api_url}. "
            f"Body: {response.text[:300]}"
        )

    return response.text


async def fetch_raw_file(raw_url: str) -> str:
    """
    Fetch the content of a raw file from GitHub (raw.githubusercontent.com).

    Parameters
    ----------
    raw_url: URL to a raw file, e.g.
             https://raw.githubusercontent.com/owner/repo/main/.env

    Returns
    -------
    File content as a string.

    Raises
    ------
    GitHubAPIError: If the request fails.
    """
    parsed = urlparse(raw_url)
    if "github" not in parsed.netloc:
        raise InvalidInputError(
            f"URL must point to a GitHub resource (raw.githubusercontent.com or github.com). Got: {raw_url}"
        )

    logger.info("Fetching raw file from %s", raw_url)

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(raw_url, headers=_auth_headers())

    if response.status_code != 200:
        raise GitHubAPIError(
            f"Failed to fetch file from {raw_url}. HTTP {response.status_code}"
        )

    return response.text
async def fetch_pr_files(pr_url: str) -> list[dict]:
    """
    Fetch the list of files changed in a GitHub Pull Request.

    Returns file information including filename, status and patch.
    """
    owner, repo, number = parse_pr_url(pr_url)

    api_url = f"{_GITHUB_API}/repos/{owner}/{repo}/pulls/{number}/files"

    logger.info("Fetching changed PR files from %s", api_url)

    all_files = []
    page = 1

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            response = await client.get(
                api_url,
                headers=_auth_headers(),
                params={"per_page": 100, "page": page},
            )

            if response.status_code == 404:
                raise GitHubAPIError(
                    f"Pull Request not found: {pr_url}"
                )

            if response.status_code == 403:
                raise GitHubAPIError(
                    "GitHub API rate limit exceeded or insufficient permissions."
                )

            if response.status_code != 200:
                raise GitHubAPIError(
                    f"Failed to fetch PR files. HTTP {response.status_code}: "
                    f"{response.text[:300]}"
                )

            files = response.json()

            if not isinstance(files, list):
                raise GitHubAPIError(
                    "GitHub returned an unexpected PR files response."
                )

            all_files.extend(files)

            if len(files) < 100:
                break

            page += 1

    logger.info("Retrieved %d changed PR files", len(all_files))

    return all_files
async def post_pr_comment(pr_url: str, comment: str) -> dict:
    """
    Post a security report comment on a GitHub Pull Request.
    """

    owner, repo, number = parse_pr_url(pr_url)

    if not settings.github_token:
        raise GitHubAPIError(
            "GITHUB_TOKEN is not configured."
        )

    api_url = (
        f"{_GITHUB_API}/repos/{owner}/{repo}"
        f"/issues/{number}/comments"
    )

    logger.info("Posting GitGuard AI comment on PR: %s", pr_url)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            api_url,
            headers=_auth_headers(),
            json={"body": comment},
        )

    if response.status_code == 401:
        raise GitHubAPIError(
            "GitHub authentication failed. Check your GITHUB_TOKEN."
        )

    if response.status_code == 403:
        raise GitHubAPIError(
            "GitHub denied permission to post the PR comment. "
            "Check the token's Issues: Read and write permission."
        )

    if response.status_code not in (200, 201):
        raise GitHubAPIError(
            f"Failed to post PR comment. "
            f"HTTP {response.status_code}: {response.text[:300]}"
        )

    result = response.json()

    logger.info(
        "GitGuard AI comment posted successfully. Comment ID: %s",
        result.get("id"),
    )

    return {
        "success": True,
        "comment_id": result.get("id"),
        "comment_url": result.get("html_url"),
    }
async def fetch_push_files(
    repository_full_name: str,
    before: str,
    after: str,
) -> list[dict]:
    """
    Fetch files changed between two commits after a GitHub push.
    """

    if not re.fullmatch(r"[^/]+/[^/]+", repository_full_name):
        raise InvalidInputError("Invalid GitHub repository name.")

    if not re.fullmatch(r"[0-9a-fA-F]{40}", before):
        raise InvalidInputError("Invalid previous commit SHA.")

    if not re.fullmatch(r"[0-9a-fA-F]{40}", after):
        raise InvalidInputError("Invalid latest commit SHA.")

    owner, repo = repository_full_name.split("/")

    api_url = (
        f"{_GITHUB_API}/repos/{owner}/{repo}"
        f"/compare/{before}...{after}"
    )

    logger.info("Fetching pushed files from %s", api_url)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            api_url,
            headers=_auth_headers(),
        )

    if response.status_code != 200:
        raise GitHubAPIError(
            f"Failed to fetch pushed files. "
            f"HTTP {response.status_code}: {response.text[:300]}"
        )

    result = response.json()
    files = result.get("files", [])

    if not isinstance(files, list):
        raise GitHubAPIError(
            "GitHub returned an unexpected push files response."
        )

    logger.info("Retrieved %d changed push files", len(files))

    return files