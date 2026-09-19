import hashlib
import unicodedata
from mnemonic import Mnemonic
from ..methods.base import EntropyMethod

_WORDS = Mnemonic("english")
VALID_ENTROPY_BYTES = (16, 20, 24, 28, 32)
MIN_ENTROPY_BITS = 128.0


def mnemonic_from_entropy(entropy: bytes) -> str:
    if len(entropy) not in VALID_ENTROPY_BYTES:
        raise ValueError(f"BIP39 requiere {VALID_ENTROPY_BYTES} bytes de entropía")
    return _WORDS.to_mnemonic(entropy)


def mnemonic_to_seed(mnemonic: str, passphrase: str = "") -> bytes:
    """BIP39: PBKDF2-HMAC-SHA512 sobre la *frase* (no sobre la entropía cruda)."""
    m = unicodedata.normalize("NFKD", mnemonic)
    salt = unicodedata.normalize("NFKD", "mnemonic" + passphrase)
    return hashlib.pbkdf2_hmac("sha512", m.encode(), salt.encode(), 2048, dklen=64)


def generate_seed_from(method: EntropyMethod, nbytes: int = 32,
                       passphrase: str = "", allow_weak: bool = False) -> dict:
    sample = method.generate(nbytes)
    bits = min(sample.bits_claimed, 8.0 * len(sample.data))  # el hash no crea entropía
    if bits < MIN_ENTROPY_BITS and not allow_weak:
        raise ValueError(
            f"'{method.name}' aporta ~{bits:.0f} bits reales "
            f"(< {MIN_ENTROPY_BITS:.0f}); no es apta para custodiar fondos")
    phrase = mnemonic_from_entropy(sample.data)
    return {
        "method": method.name,
        "entropy_bytes": sample.data.hex(),
        "bits_claimed": bits,
        "mnemonic": phrase,
        "seed_hex": mnemonic_to_seed(phrase, passphrase).hex(),
        "metadata": sample.metadata,
    }
