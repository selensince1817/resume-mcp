# utils.py

from fastmcp.server.auth.providers.bearer import RSAKeyPair
from pydantic import SecretStr
from fastmcp.server.auth.providers.bearer import RSAKeyPair
from .config import Config


def load_public_key():
    try:
        with open(Config.PUBLIC_KEY_PATH, "r") as f:
            public_key = f.read()
        return public_key
    except FileNotFoundError:
        return None


def load_private_key_bytes():
    try:
        with open(Config.PRIVATE_KEY_PATH, "r") as f:
            private_key = f.read()
        return private_key
    except FileNotFoundError:
        return None


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


def gen_keys() -> None:

    print("Generating new RSA key pair...")

    try:
        # This generates an object where the keys are already PEM-encoded strings.
        # The private key is wrapped in a SecretStr for security.
        key_pair = RSAKeyPair.generate()

        # --- Private Key Handling ---
        # Get the private key string from the SecretStr wrapper and encode it to bytes.
        private_key_pem_string = key_pair.private_key.get_secret_value()
        private_key_bytes = private_key_pem_string.encode("utf-8")

        # --- Public Key Handling ---
        # The public key is already a simple string. Just encode it to bytes.
        public_key_pem_string = key_pair.public_key
        public_key_bytes = public_key_pem_string.encode("utf-8")

        # --- Save to Files ---
        with open("private_key.pem", "wb") as f:
            f.write(private_key_bytes)

        with open("../../../public_key.pem", "wb") as f:
            f.write(public_key_bytes)

        print(
            "Successfully generated and saved 'private_key.pem' and 'public_key.pem'."
        )

    except Exception as e:
        print(f"Failed to generate keys: {e}")
