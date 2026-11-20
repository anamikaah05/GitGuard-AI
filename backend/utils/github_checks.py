
"""
GitHub Checks API integration for GitGuard AI.
Creates security check results on GitHub commits.
"""

import re
import httpx

from utils.github_app import get_installation_access_token


async def create_security_check(
    repository_name: str,
    commit_sha: str,
    has_secret: bool,
    summary: str,
) -> dict:
    """Create a completed GitGuard AI security check on a commit."""

    if not re.fullmatch(r"[^/]+/[^/]+", repository_name):
        raise ValueError("Invalid GitHub repository name.")

    if not re.fullmatch(r"[0-9a-fA-F]{40}", commit_sha):
        raise ValueError("Invalid commit SHA.")

    token = await get_installation_access_token()

    owner, repo = repository_name.split("/")

    url = (
        f"https://api.github.com/repos/{owner}/{repo}/check-runs"
    )

    conclusion = "failure" if has_secret else "success"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    payload = {
        "name": "GitGuard AI Security Scan",
        "head_sha": commit_sha,
        "status": "completed",
        "conclusion": conclusion,
        "output": {
            "title": (
                "Potential secret detected"
                if has_secret
                else "No potential secrets detected"
            ),
            "summary": summary,
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            headers=headers,
            json=payload,
        )

    if response.status_code != 201:
        raise RuntimeError(
            "Failed to create GitHub security check: "
            f"HTTP {response.status_code}: {response.text[:300]}"
        )

    result = response.json()

    return {
        "success": True,
        "check_run_id": result.get("id"),
        "check_url": result.get("html_url"),
        "conclusion": result.get("conclusion"),
    }
