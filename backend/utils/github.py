
"""
utils/github.py — GitHub REST API helpers

Provides async functions to:
  - Fetch the raw diff text for a Pull Request
  - Fetch changed files in a Pull Request
  - Fetch raw file content from a repository
  - Post security comments on Pull Requests
  - Fetch files changed by a push event

All GitHub API requests use GitHub App installation authentication.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

import httpx

from utils.github_app import get_installation_access_token
from core.exceptions import GitHubAPIError, InvalidInputError

logger = logging.getLogger(__name__)

_GITHUB_API = "https://api.github.com"

_PR_URL_RE = re.compile(
    r"https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)",
    re.IGNORECASE,
)


# ---------------------------------------------------------
# GitHub App Authentication
# ---------------------------------------------------------

async def _auth_headers() -> dict[str, str]:
    """Generate authentication headers using GitHub App installation token."""

    token = await get_installation_access_token()

    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def _diff_headers() -> dict[str, str]:
    """Generate headers for fetching Pull Request diffs."""

    headers = await _auth_headers()
    headers["Accept"] = "application/vnd.github.diff"

    return headers


# ---------------------------------------------------------
# Parse Pull Request URL
# ---------------------------------------------------------

def parse_pr_url(pr_url: str) -> tuple[str, str, int]:
    """
    Extract owner, repository and PR number from a GitHub PR URL.
    """

    match = _PR_URL_RE.match(pr_url.strip())

    if not match:
        raise InvalidInputError(
            f"Invalid GitHub PR URL: '{pr_url}'. "
            "Expected format: https://github.com/owner/repo/pull/number"
        )

    return (
        match.group("owner"),
        match.group("repo"),
        int(match.group("number")),
    )


# ---------------------------------------------------------
# Fetch Pull Request Diff
# ---------------------------------------------------------

async def fetch_pr_diff(pr_url: str) -> str:
    """
    Fetch the unified diff for a GitHub Pull Request.
    """

    owner, repo, number = parse_pr_url(pr_url)

    api_url = (
        f"{_GITHUB_API}/repos/{owner}/{repo}/pulls/{number}"
    )

    logger.info("Fetching PR diff from %s", api_url)

    headers = await _diff_headers()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            api_url,
            headers=headers,
        )

    if response.status_code == 404:
        raise GitHubAPIError(
            f"PR not found: {pr_url}. "
            "Check that the GitHub App is installed on this repository "
            "and has Pull requests read permission."
        )

    if response.status_code == 401:
        raise GitHubAPIError(
            "GitHub App authentication failed while fetching PR diff."
        )

    if response.status_code == 403:
        raise GitHubAPIError(
            "GitHub denied access to the PR diff. "
            "Check GitHub App permissions and API rate limits."
        )

    if response.status_code != 200:
        raise GitHubAPIError(
            f"GitHub API returned HTTP {response.status_code} "
            f"for {api_url}. Body: {response.text[:300]}"
        )

    return response.text


# ---------------------------------------------------------
# Fetch Raw File Content
# ---------------------------------------------------------

async def fetch_raw_file(raw_url: str) -> str:
    """
    Fetch content from a GitHub raw file URL.
    """

    parsed = urlparse(raw_url)

    if parsed.scheme != "https" or parsed.hostname not in (
        "raw.githubusercontent.com",
        "github.com",
    ):
        raise InvalidInputError(
            f"URL must point to a valid GitHub resource. Got: {raw_url}"
        )

    logger.info("Fetching raw file from %s", raw_url)

    headers = await _auth_headers()

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            raw_url,
            headers=headers,
        )

    if response.status_code == 401:
        raise GitHubAPIError(
            "GitHub App authentication failed while fetching file."
        )

    if response.status_code == 403:
        raise GitHubAPIError(
            "GitHub denied access to the requested file. "
            "Check the App's Contents read permission."
        )

    if response.status_code != 200:
        raise GitHubAPIError(
            f"Failed to fetch file from {raw_url}. "
            f"HTTP {response.status_code}"
        )

    return response.text


# ---------------------------------------------------------
# Fetch Pull Request Changed Files
# ---------------------------------------------------------

async def fetch_pr_files(pr_url: str) -> list[dict]:
    """
    Fetch all files changed in a GitHub Pull Request.

    Returns file information including filename, status and patch.
    """

    owner, repo, number = parse_pr_url(pr_url)

    api_url = (
        f"{_GITHUB_API}/repos/{owner}/{repo}"
        f"/pulls/{number}/files"
    )

    logger.info("Fetching changed PR files from %s", api_url)

    all_files = []
    page = 1

    headers = await _auth_headers()

    async with httpx.AsyncClient(timeout=30.0) as client:

        while True:

            response = await client.get(
                api_url,
                headers=headers,
                params={
                    "per_page": 100,
                    "page": page,
                },
            )

            if response.status_code == 404:
                raise GitHubAPIError(
                    f"Pull Request not found: {pr_url}"
                )

            if response.status_code == 401:
                raise GitHubAPIError(
                    "GitHub App authentication failed while fetching PR files."
                )

            if response.status_code == 403:
                raise GitHubAPIError(
                    "GitHub denied access to PR files. "
                    "Check Pull requests read permission."
                )

            if response.status_code != 200:
                raise GitHubAPIError(
                    f"Failed to fetch PR files. "
                    f"HTTP {response.status_code}: "
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

    logger.info(
        "Retrieved %d changed PR files",
        len(all_files),
    )

    return all_files


# ---------------------------------------------------------
# Post Pull Request Security Comment
# ---------------------------------------------------------

async def post_pr_comment(pr_url: str, comment: str) -> dict:
    """
    Post a GitGuard AI security report comment on a Pull Request.

    Uses GitHub App installation authentication.
    """

    owner, repo, number = parse_pr_url(pr_url)

    api_url = (
        f"{_GITHUB_API}/repos/{owner}/{repo}"
        f"/issues/{number}/comments"
    )

    logger.info(
        "Posting GitGuard AI comment on PR: %s",
        pr_url,
    )

    headers = await _auth_headers()

    async with httpx.AsyncClient(timeout=30.0) as client:

        response = await client.post(
            api_url,
            headers=headers,
            json={"body": comment},
        )

    if response.status_code == 401:
        raise GitHubAPIError(
            "GitHub App authentication failed while posting PR comment."
        )

    if response.status_code == 403:
        raise GitHubAPIError(
            "GitHub denied permission to post the PR comment. "
            "Check that the GitHub App has Issues read and write permission."
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


# ---------------------------------------------------------
# Fetch Files Changed by Push Event
# ---------------------------------------------------------

async def fetch_push_files(
    repository_full_name: str,
    before: str,
    after: str,
) -> list[dict]:
    """
    Fetch files changed between two commits after a GitHub push.
    """

    if not re.fullmatch(r"[^/]+/[^/]+", repository_full_name):
        raise InvalidInputError(
            "Invalid GitHub repository name."
        )

    if not re.fullmatch(r"[0-9a-fA-F]{40}", before):
        raise InvalidInputError(
            "Invalid previous commit SHA."
        )

    if not re.fullmatch(r"[0-9a-fA-F]{40}", after):
        raise InvalidInputError(
            "Invalid latest commit SHA."
        )

    owner, repo = repository_full_name.split("/")

    api_url = (
        f"{_GITHUB_API}/repos/{owner}/{repo}"
        f"/compare/{before}...{after}"
    )

    logger.info(
        "Fetching pushed files from %s",
        api_url,
    )

    headers = await _auth_headers()

    async with httpx.AsyncClient(timeout=30.0) as client:

        response = await client.get(
            api_url,
            headers=headers,
        )

    if response.status_code == 401:
        raise GitHubAPIError(
            "GitHub App authentication failed while fetching push files."
        )

    if response.status_code == 403:
        raise GitHubAPIError(
            "GitHub denied access to commit comparison. "
            "Check the App's Contents read permission."
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

    logger.info(
        "Retrieved %d changed push files",
        len(files),
    )

    return files
