"""BIP32 (derivación jerárquica determinista) sobre secp256k1."""
import hashlib
import hmac
from dataclasses import dataclass
from .hashes import hash160
from .secp256k1 import N, P, G, point_mul, _add, pubkey_compressed

HARDENED = 0x80000000


@dataclass(frozen=True)
class ExtKey:
    priv: int
    chain: bytes
    depth: int = 0
    parent_fp: bytes = b"\x00\x00\x00\x00"
    index: int = 0

    @property
    def pub(self) -> bytes:
        return pubkey_compressed(self.priv)

    @property
    def fingerprint(self) -> bytes:
        """Fingerprint BIP32: primeros 4 bytes de HASH160(pubkey)."""
        return hash160(self.pub)[:4]

    @property
    def key_id(self) -> str:
        return self.fingerprint.hex()


@dataclass(frozen=True)
class ExtPub:
    pub: bytes
    chain: bytes
    depth: int = 0
    parent_fp: bytes = b"\x00\x00\x00\x00"
    index: int = 0

    @property
    def fingerprint(self) -> bytes:
        return hash160(self.pub)[:4]


def master_key_from_seed(seed: bytes) -> ExtKey:
    I = hmac.new(b"Bitcoin seed", seed, hashlib.sha512).digest()
    k = int.from_bytes(I[:32], "big")
    if not 0 < k < N:
        raise ValueError("master key inválida; usar otra seed")
    return ExtKey(k, I[32:])


def derive_child(parent: ExtKey, index: int) -> ExtKey:
    if index >= HARDENED:
        data = b"\x00" + parent.priv.to_bytes(32, "big") + index.to_bytes(4, "big")
    else:
        data = parent.pub + index.to_bytes(4, "big")
    I = hmac.new(parent.chain, data, hashlib.sha512).digest()
    il = int.from_bytes(I[:32], "big")
    child = (il + parent.priv) % N
    if il >= N or child == 0:
        raise ValueError(f"índice {index} inválido (prob. ~2^-127); usar el siguiente")
    return ExtKey(child, I[32:], parent.depth + 1, parent.fingerprint, index)


def to_pub(k: ExtKey) -> ExtPub:
    return ExtPub(k.pub, k.chain, k.depth, k.parent_fp, k.index)


def _decompress(pub: bytes):
    x = int.from_bytes(pub[1:], "big")
    y = pow((x ** 3 + 7) % P, (P + 1) // 4, P)
    if (y & 1) != (pub[0] & 1):
        y = P - y
    return x, y


def derive_pub_child(parent: ExtPub, index: int) -> ExtPub:
    """CKDpub: derivación pública (solo índices no endurecidos), sin claves privadas."""
    if index >= HARDENED:
        raise ValueError("no se puede derivar un hijo endurecido desde una clave pública")
    I = hmac.new(parent.chain, parent.pub + index.to_bytes(4, "big"), hashlib.sha512).digest()
    il = int.from_bytes(I[:32], "big")
    if il >= N:
        raise ValueError("índice inválido")
    pt = _add(point_mul(il, G), _decompress(parent.pub))
    if pt is None:
        raise ValueError("punto en el infinito")
    pub = bytes([2 + (pt[1] & 1)]) + pt[0].to_bytes(32, "big")
    return ExtPub(pub, I[32:], parent.depth + 1, parent.fingerprint, index)


def parse_path(path: str) -> list:
    parts = [p for p in path.strip().split("/") if p != ""]
    if not parts or parts[0] != "m":
        raise ValueError("el path debe empezar por 'm'")
    out = []
    for p in parts[1:]:
        hardened = p[-1] in "'hH"
        i = int(p.rstrip("'hH"))
        out.append(i + HARDENED if hardened else i)
    return out


def derive_path(master: ExtKey, path: str) -> ExtKey:
    k = master
    for i in parse_path(path):
        k = derive_child(k, i)
    return k
