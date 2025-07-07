# utils.py

from fastmcp.server.auth.providers.bearer import RSAKeyPair
from pydantic import SecretStr


def create_access_token(
    public_key: str,
    private_key: str,
    audience: str = "resume-mcp-server",
    expires_in_seconds: int = 60 * 60 * 24 * 31,
) -> str:
    # Create a key pair instance from the loaded keys to generate our token
    key_pair = RSAKeyPair(public_key=public_key, private_key=SecretStr(private_key))
    access_token = key_pair.create_token(
        audience=audience, expires_in_seconds=expires_in_seconds
    )
    return access_token
