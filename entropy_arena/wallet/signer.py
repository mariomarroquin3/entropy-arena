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


def public_keystore_export(label: str, fingerprint: str, path: str, xpub: str,
                           network: str = "regtest") -> dict:
    """Construye el JSON público de un firmante a partir de datos que da Sparrow
    (fingerprint, ruta y xpub de un keystore), validando que xpub y ruta son coherentes:
    la profundidad de la xpub debe ser igual al número de pasos de la ruta y su último
    paso (índice hijo) debe coincidir con el último paso de la ruta. Un desajuste implica
    que la xpub NO sale de esa ruta y Sparrow no podría firmar."""
    import re
    from .key_derivation import HARDENED, parse_path
    from .xkeys import parse_pub
    if not re.fullmatch(r"[0-9a-fA-F]{8}", fingerprint):
        raise ValueError("el fingerprint debe tener 8 caracteres hexadecimales")
    if fingerprint == "00000000":
        raise ValueError("fingerprint 00000000 es el marcador de 'desconocido'; usa el real")
    steps = parse_path(path)
    if not steps:
        raise ValueError("la ruta debe tener al menos un paso (p. ej. m/84'/1'/0')")
    k = parse_pub(xpub)
    if k.depth != len(steps):
        raise ValueError(
            f"la xpub tiene profundidad {k.depth} pero la ruta {path} tiene {len(steps)} pasos: "
            "la xpub NO se derivó de esa ruta")
    if k.index != steps[-1]:
        last = steps[-1]
        raise ValueError(
            f"el último paso de la xpub ({k.index - HARDENED if k.index >= HARDENED else k.index}"
            f"{chr(39) if k.index >= HARDENED else ''}) no coincide con el de la ruta "
            f"({last - HARDENED if last >= HARDENED else last}{chr(39) if last >= HARDENED else ''})")
    return {"label": label, "network": network, "method": "importado_de_sparrow",
            "entropy_bits": None, "master_fingerprint": fingerprint.lower(),
            "path": path.replace("h", "'").replace("H", "'"), "xpub": xpub,
            "key_origin": f"[{fingerprint.lower()}/{path.removeprefix('m/').replace('h', chr(39))}]{xpub}"}
