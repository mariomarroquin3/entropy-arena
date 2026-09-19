import hashlib
from .bech32 import segwit_v0_address
from .descriptor import wsh_sortedmulti
from .key_derivation import master_key_from_seed, derive_path
from .seed_generator import generate_seed_from

NETWORKS = {"testnet": ("tb", 1), "mainnet": ("bc", 0), "regtest": ("bcrt", 1)}


def witness_script(pubkeys: list, threshold: int) -> bytes:
    """OP_m <pk...> OP_n OP_CHECKMULTISIG con claves ordenadas (BIP67)."""
    keys = sorted(pubkeys)
    n = len(keys)
    if not (1 <= threshold <= n <= 16):
        raise ValueError("threshold/total inválidos")
    return (bytes([0x50 + threshold]) + b"".join(bytes([33]) + k for k in keys)
            + bytes([0x50 + n, 0xAE]))


def build_multisig_vault(methods: list, nbytes: int = 32, threshold: int = 2,
                         total: int = 3, network: str = "testnet",
                         allow_weak: bool = False, address_index: int = 0) -> dict:
    if len(methods) != total:
        raise ValueError(f"Se requieren {total} métodos (uno por firmante)")
    hrp, coin = NETWORKS[network]
    account = f"m/48'/{coin}'/0'/2'"  # BIP48, script type P2WSH
    path = f"{account}/0/{address_index}"
    signers, pubkeys = [], []
    for i, m in enumerate(methods):
        info = generate_seed_from(m, nbytes=nbytes, allow_weak=allow_weak)
        master = master_key_from_seed(bytes.fromhex(info["seed_hex"]))
        leaf = derive_path(master, path)
        pubkeys.append(leaf.pub)
        signers.append({
            "signer": i + 1, "method": info["method"],
            "bits_claimed": info["bits_claimed"],
            "words": len(info["mnemonic"].split()),
            "mnemonic": info["mnemonic"], "master_id": master.key_id,
            "pubkey": leaf.pub.hex(), "path": path,
        })
    if len(set(pubkeys)) != len(pubkeys):
        raise ValueError("dos firmantes generaron la misma clave (misma fuente fija reutilizada)")
    script = witness_script(pubkeys, threshold)
    bits = sorted(s["bits_claimed"] for s in signers)
    return {
        "threshold": threshold, "total": total, "network": network,
        "signers": signers, "witness_script": script.hex(),
        "address": segwit_v0_address(hrp, hashlib.sha256(script).digest()),
        "attack_bits": attack_bits(bits, threshold),
        "descriptor": wsh_sortedmulti(threshold, pubkeys),
    }


def attack_bits(bits: list, threshold: int) -> float:
    """Bits de esfuerzo para romper `threshold` firmantes: se atacan los más débiles
    y el coste lo domina el más fuerte de ese subconjunto."""
    return max(sorted(bits)[:threshold])
