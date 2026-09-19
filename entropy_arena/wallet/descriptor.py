"""Output descriptors (BIP380/BIP383) para importar la bóveda en Bitcoin Core."""

_INPUT = ("0123456789()[],'/*abcdefgh@:$%{}IJKLMNOPQRSTUVWXYZ&+-.;<=>?!^_|~"
          "ijklmnopqrstuvwxyzABCDEFGH`#\"\\ ")
_CHECK = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
_GEN = [0xf5dee51989, 0xa9fdca3312, 0x1bab10e32d, 0x3706b1677a, 0x644d626ffd]


def _polymod(c: int, val: int) -> int:
    c0 = c >> 35
    c = ((c & 0x7ffffffff) << 5) ^ val
    for i, g in enumerate(_GEN):
        if (c0 >> i) & 1:
            c ^= g
    return c


def checksum(desc: str) -> str:
    c, cls, n = 1, 0, 0
    for ch in desc:
        pos = _INPUT.find(ch)
        if pos == -1:
            raise ValueError(f"carácter inválido en descriptor: {ch!r}")
        c = _polymod(c, pos & 31)
        cls, n = cls * 3 + (pos >> 5), n + 1
        if n == 3:
            c, cls, n = _polymod(c, cls), 0, 0
    if n:
        c = _polymod(c, cls)
    for _ in range(8):
        c = _polymod(c, 0)
    c ^= 1
    return "".join(_CHECK[(c >> (5 * (7 - j))) & 31] for j in range(8))


def wsh_sortedmulti(threshold: int, pubkeys: list) -> str:
    """wsh(sortedmulti(m,pk...)) con clave pública fija (una sola dirección)."""
    body = f"wsh(sortedmulti({threshold}," + ",".join(k.hex() for k in pubkeys) + "))"
    return f"{body}#{checksum(body)}"


# ----------------------------------------------------------------- con origen
import re
from .bech32 import segwit_v0_address
from .key_derivation import derive_pub_child
from .xkeys import parse_pub

HRP = {"mainnet": "bc", "testnet": "tb", "regtest": "bcrt"}
_KEY_RE = re.compile(r"\[([0-9a-fA-F]{8})((?:/\d+['h]?)+)\]([xt]pub[1-9A-HJ-NP-Za-km-z]+)/(<0;1>|[01])/\*")


def key_origin(fingerprint_hex: str, path: str, xpub: str, branch: str) -> str:
    """[fingerprint/ruta]xpub/rama/*  (path sin la 'm', p. ej. 48'/1'/0'/2')."""
    return f"[{fingerprint_hex}/{path}]{xpub}/{branch}/*"


def multisig_descriptor(threshold: int, signers: list, branch: str = "<0;1>") -> str:
    """signers: [{'fingerprint','path','xpub'}, ...]. branch: '<0;1>', '0' o '1'."""
    keys = ",".join(key_origin(s["fingerprint"], s["path"].removeprefix("m/"), s["xpub"], branch)
                    for s in signers)
    body = f"wsh(sortedmulti({threshold},{keys}))"
    return f"{body}#{checksum(body)}"


def parse_multisig_descriptor(desc: str) -> dict:
    """Valida el checksum y extrae política y claves públicas (sin material secreto)."""
    body, sep, cs = desc.strip().partition("#")
    if sep and checksum(body) != cs:
        raise ValueError("checksum del descriptor incorrecto")
    m = re.fullmatch(r"wsh\(sortedmulti\((\d+),(.+)\)\)", body)
    if not m:
        raise ValueError("solo se soporta wsh(sortedmulti(m,...))")
    keys = []
    for k in re.findall(r"\[[^\]]+\][xt]pub\w+/(?:<0;1>|[01])/\*", m.group(2)):
        km = _KEY_RE.fullmatch(k)
        if not km:
            raise ValueError(f"clave no reconocida: {k}")
        keys.append({"fingerprint": km.group(1).lower(), "path": km.group(2).lstrip("/"),
                     "xpub": km.group(3), "branch": km.group(4)})
    if not keys or not (1 <= int(m.group(1)) <= len(keys)):
        raise ValueError("política inválida")
    return {"threshold": int(m.group(1)), "keys": keys, "checksum_ok": bool(sep)}


def derive_address(info: dict, chain: int, index: int, network: str = "testnet") -> dict:
    """Dirección y script de la rama `chain` (0 recibir, 1 cambio) usando SOLO claves públicas."""
    import hashlib
    from .multisig_builder import witness_script
    for k in info["keys"]:
        if k["branch"] not in ("<0;1>", str(chain)):
            raise ValueError(f"el descriptor solo cubre la rama {k['branch']}, no la {chain}")
    pubs = [derive_pub_child(derive_pub_child(parse_pub(k["xpub"]), chain), index).pub
            for k in info["keys"]]
    script = witness_script(pubs, info["threshold"])
    return {"chain": chain, "index": index, "witness_script": script.hex(),
            "address": segwit_v0_address(HRP[network], hashlib.sha256(script).digest())}
