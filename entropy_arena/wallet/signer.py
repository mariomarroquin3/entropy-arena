"""Un firmante independiente: genera su mnemónico y exporta SOLO datos públicos."""
from .key_derivation import master_key_from_seed, derive_path, to_pub
from .seed_generator import generate_seed_from, mnemonic_to_seed
from .xkeys import serialize_pub
from mnemonic import Mnemonic

COIN = {"mainnet": 0, "testnet": 1, "regtest": 1}


def account_path(network: str) -> str:
    return f"m/48'/{COIN[network]}'/0'/2'"  # BIP48, P2WSH (script type 2)


def export_public(mnemonic: str, label: str, method: str, bits,
                  network: str = "testnet", passphrase: str = "") -> dict:
    master = master_key_from_seed(mnemonic_to_seed(mnemonic, passphrase))
    path = account_path(network)
    acct = derive_path(master, path)
    xpub = serialize_pub(to_pub(acct), "mainnet" if network == "mainnet" else "testnet")
    return {"label": label, "network": network, "method": method,
            "entropy_bits": None if bits is None else round(bits, 1), "master_fingerprint": master.fingerprint.hex(),
            "path": path, "xpub": xpub,
            "key_origin": f"[{master.fingerprint.hex()}/{path.removeprefix('m/')}]{xpub}"}


def create_signer(method, label: str, network: str = "testnet", allow_weak: bool = False) -> tuple:
    """Devuelve (mnemónico SECRETO, export público)."""
    info = generate_seed_from(method, nbytes=32, allow_weak=allow_weak)
    pub = export_public(info["mnemonic"], label, info["method"], info["bits_claimed"], network)
    return info["mnemonic"], pub


def signer_from_mnemonic(mnemonic: str, label: str, network: str = "testnet") -> dict:
    if not Mnemonic("english").check(mnemonic):
        raise ValueError("mnemónico BIP39 inválido (palabras o checksum)")
    return export_public(mnemonic, label, "mnemonic_importado", None, network)
