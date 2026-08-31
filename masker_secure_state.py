"""AES-256-GCM protected local state for Masker."""

import json
import os
import subprocess
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


STATE_DIR = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Masker"
KEY_FILE = STATE_DIR / "masker.key"
STATE_FILE = STATE_DIR / "state.aes256"
AAD = b"Masker-State-v1"
_KEY_CACHE = None


def _ensure_key():
    global _KEY_CACHE
    if _KEY_CACHE is not None:
        return _KEY_CACHE
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not KEY_FILE.exists():
        key = AESGCM.generate_key(bit_length=256)
        KEY_FILE.write_bytes(key)
        subprocess.run(
            [
                "icacls.exe",
                str(KEY_FILE),
                "/inheritance:r",
                "/grant:r",
                "*S-1-5-18:F",
                "*S-1-5-32-544:F",
            ],
            capture_output=True,
            check=False,
        )
    else:
        key = KEY_FILE.read_bytes()
    if len(key) != 32:
        raise RuntimeError("A chave local do Masker nao possui 256 bits.")
    _KEY_CACHE = key
    return _KEY_CACHE


def save_state(data):
    key = _ensure_key()
    nonce = os.urandom(12)
    plaintext = json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")
    encrypted = AESGCM(key).encrypt(nonce, plaintext, AAD)
    temporary = STATE_FILE.with_suffix(".tmp")
    temporary.write_bytes(b"MSK1" + nonce + encrypted)
    os.replace(temporary, STATE_FILE)


def load_state():
    if not STATE_FILE.exists():
        return {}
    payload = STATE_FILE.read_bytes()
    if len(payload) < 33 or payload[:4] != b"MSK1":
        raise RuntimeError("Estado criptografado do Masker invalido.")
    plaintext = AESGCM(_ensure_key()).decrypt(payload[4:16], payload[16:], AAD)
    return json.loads(plaintext.decode("utf-8"))
