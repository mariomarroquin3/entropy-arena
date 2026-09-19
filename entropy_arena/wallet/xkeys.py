"""Serialización BIP32 de claves extendidas (xpub/tpub/tprv)."""
from .base58 import b58check_encode, b58check_decode
from .key_derivation import ExtKey, ExtPub

VERSIONS = {  # (versión pública, versión privada)
    "mainnet": (0x0488B21E, 0x0488ADE4),
    "testnet": (0x043587CF, 0x04358394),
}


def serialize_pub(k: ExtPub, network: str = "testnet") -> str:
    v = VERSIONS[network][0]
    payload = (v.to_bytes(4, "big") + bytes([k.depth]) + k.parent_fp
               + k.index.to_bytes(4, "big") + k.chain + k.pub)
    return b58check_encode(payload)


def serialize_priv(k: ExtKey, network: str = "testnet") -> str:
    v = VERSIONS[network][1]
    payload = (v.to_bytes(4, "big") + bytes([k.depth]) + k.parent_fp
               + k.index.to_bytes(4, "big") + k.chain + b"\x00" + k.priv.to_bytes(32, "big"))
    return b58check_encode(payload)


def parse_pub(s: str) -> ExtPub:
    p = b58check_decode(s)
    if len(p) != 78 or int.from_bytes(p[:4], "big") not in (VERSIONS["mainnet"][0], VERSIONS["testnet"][0]):
        raise ValueError("no es una clave pública extendida xpub/tpub válida")
    return ExtPub(p[45:78], p[13:45], p[4], p[5:9], int.from_bytes(p[9:13], "big"))
