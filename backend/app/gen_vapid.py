"""Generate a VAPID key pair for web push. Run:  python -m app.gen_vapid"""

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def main() -> None:
    key = ec.generate_private_key(ec.SECP256R1())
    private_value = key.private_numbers().private_value.to_bytes(32, "big")
    public_bytes = key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    print("Add these to backend/.env:\n")
    print(f"VAPID_PUBLIC_KEY={b64url(public_bytes)}")
    print(f"VAPID_PRIVATE_KEY={b64url(private_value)}")


if __name__ == "__main__":
    main()
