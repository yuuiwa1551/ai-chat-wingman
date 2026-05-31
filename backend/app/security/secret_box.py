"""Local static encryption for sensitive settings (e.g. provider API keys).

This module provides reversible, at-rest encryption without adding any
third-party dependency. It derives a per-install random key stored in a
restricted-permission file under the app data directory and uses an
HMAC-SHA256 keystream (with a random nonce) plus an authentication tag.

The format of an encrypted value is:

    enc:v1:<base64(nonce[16] + tag[32] + ciphertext)>

Plain (legacy) values that are not prefixed with ``enc:v1:`` are returned
unchanged by :func:`decrypt`, so existing clear-text configs keep working
and get upgraded to ciphertext the next time they are written.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os

from app.paths import SECRET_KEY_PATH, ensure_app_dirs

ENC_PREFIX = "enc:v1:"
_NONCE_SIZE = 16
_TAG_SIZE = 32
_KEY_SIZE = 32


def _load_or_create_key() -> bytes:
    if SECRET_KEY_PATH.exists():
        return SECRET_KEY_PATH.read_bytes()
    ensure_app_dirs()
    key = os.urandom(_KEY_SIZE)
    SECRET_KEY_PATH.write_bytes(key)
    try:
        os.chmod(SECRET_KEY_PATH, 0o600)
    except OSError:
        # Best-effort on platforms/filesystems without POSIX permissions.
        pass
    return key


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    stream = bytearray()
    counter = 0
    while len(stream) < length:
        block = hmac.new(key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest()
        stream.extend(block)
        counter += 1
    return bytes(stream[:length])


def _mac(key: bytes, nonce: bytes, ciphertext: bytes) -> bytes:
    return hmac.new(key, b"mac" + nonce + ciphertext, hashlib.sha256).digest()


def encrypt(plaintext: str) -> str:
    if not plaintext:
        return plaintext
    if is_encrypted(plaintext):
        return plaintext
    key = _load_or_create_key()
    nonce = os.urandom(_NONCE_SIZE)
    data = plaintext.encode("utf-8")
    ciphertext = bytes(b ^ k for b, k in zip(data, _keystream(key, nonce, len(data))))
    tag = _mac(key, nonce, ciphertext)
    blob = base64.b64encode(nonce + tag + ciphertext).decode("ascii")
    return f"{ENC_PREFIX}{blob}"


def decrypt(value: str) -> str:
    if not value or not is_encrypted(value):
        return value
    key = _load_or_create_key()
    raw = base64.b64decode(value[len(ENC_PREFIX):].encode("ascii"))
    nonce = raw[:_NONCE_SIZE]
    tag = raw[_NONCE_SIZE:_NONCE_SIZE + _TAG_SIZE]
    ciphertext = raw[_NONCE_SIZE + _TAG_SIZE:]
    if not hmac.compare_digest(tag, _mac(key, nonce, ciphertext)):
        raise ValueError("Secret authentication failed; key file may be corrupted or replaced")
    plaintext = bytes(b ^ k for b, k in zip(ciphertext, _keystream(key, nonce, len(ciphertext))))
    return plaintext.decode("utf-8")


def is_encrypted(value: str) -> bool:
    return isinstance(value, str) and value.startswith(ENC_PREFIX)
