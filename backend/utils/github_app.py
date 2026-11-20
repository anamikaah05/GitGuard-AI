
"""
GitHub App authentication utilities.
Generates installation access tokens for GitGuard AI.
"""

import time
import jwt
import httpx

from pathlib import Path
from cryptography.hazmat.primitives import serialization

from core.config import settings


def generate_app_jwt() -> str:
    """Generate a short-lived JWT for GitHub App authentication."""

    app_id = settings.github_app_id
    private_key_path = settings.github_app_private_key_path

    if not app_id or not private_key_path:
        raise ValueError("GitHub App ID or private key path is missing.")

    key_path = Path(private_key_path)

    if not key_path.is_file():
        raise FileNotFoundError(
            f"GitHub App private key not found: {key_path}"
        )

    with key_path.open("rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
        )

    now = int(time.time())

    payload = {
        "iat": now - 60,
        "exp": now + 540,
        "iss": app_id,
    }

    return jwt.encode(payload, private_key, algorithm="RS256")


async def get_installation_access_token() -> str:
    """Generate an installation access token."""

    installation_id = settings.github_app_installation_id

    if not installation_id:
        raise ValueError("GitHub App installation ID is missing.")

    app_jwt = generate_app_jwt()

    url = (
        "https://api.github.com/app/installations/"
        f"{installation_id}/access_tokens"
    )

    headers = {
        "Authorization": f"Bearer {app_jwt}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers)

    if response.status_code != 201:
        raise RuntimeError(
            "Failed to generate GitHub installation token: "
            f"HTTP {response.status_code}: {response.text[:300]}"
        )

    result = response.json()
    token = result.get("token")

    if not token:
        raise RuntimeError("GitHub did not return an installation token.")

    return token
