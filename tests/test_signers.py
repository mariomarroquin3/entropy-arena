import hashlib
import pytest

from entropy_arena.methods.computational.os_urandom import OsUrandomMethod
from entropy_arena.wallet.signer import create_signer
from entropy_arena.wallet.descriptor import (
    multisig_descriptor, parse_multisig_descriptor, derive_address)
from entropy_arena.wallet.key_derivation import master_key_from_seed, derive_path
from entropy_arena.wallet.multisig_builder import witness_script
from entropy_arena.wallet.seed_generator import mnemonic_to_seed
from entropy_arena.wallet.bech32 import segwit_v0_address


def _three():
    return [create_signer(OsUrandomMethod(), f"s{i}") for i in range(3)]


def _signers(ss):
    return [{"fingerprint": p["master_fingerprint"], "path": p["path"], "xpub": p["xpub"]}
            for _, p in ss]


def test_signers_independent_and_public_only():
    ss = _three()
    assert len({p["master_fingerprint"] for _, p in ss}) == 3
    for secret, pub in ss:
        assert secret not in str(pub) and pub["xpub"].startswith("tpub")
        assert pub["path"] == "m/48'/1'/0'/2'" and len(pub["master_fingerprint"]) == 8


def test_watch_only_reconstruction_matches_private_side():
    """Dirección derivada solo con tpub+descriptor == la derivada con claves privadas."""
    ss = _three()
    info = parse_multisig_descriptor(multisig_descriptor(2, _signers(ss), "0"))
    assert info["threshold"] == 2 and len(info["keys"]) == 3 and info["checksum_ok"]
    for idx in (0, 3):
        pubs = [derive_path(master_key_from_seed(mnemonic_to_seed(m)),
                            f"m/48'/1'/0'/2'/0/{idx}").pub for m, _ in ss]
        expected = segwit_v0_address("tb", hashlib.sha256(witness_script(pubs, 2)).digest())
        assert derive_address(info, 0, idx)["address"] == expected


def test_descriptor_bad_checksum_rejected():
    d = multisig_descriptor(2, _signers(_three()))
    with pytest.raises(ValueError):
        parse_multisig_descriptor(d[:-1] + ("q" if d[-1] != "q" else "p"))


def test_ripemd160_fallback_multiblock_matches_openssl():
    import hashlib
    from entropy_arena.wallet.hashes import _ripemd160_py
    try:
        ref = lambda d: hashlib.new("ripemd160", d).digest()
        ref(b"")
    except ValueError:
        pytest.skip("OpenSSL sin ripemd160")
    for n in (55, 56, 64, 65, 200, 1000):
        d = bytes(range(256)) * 4
        assert _ripemd160_py(d[:n]) == ref(d[:n])


def test_import_mnemonic_export_is_valid_json():
    import json
    from entropy_arena.wallet.signer import signer_from_mnemonic
    pub = signer_from_mnemonic("abandon " * 11 + "about", "x")
    json.loads(json.dumps(pub, allow_nan=False))       # sin NaN
    assert pub["entropy_bits"] is None


def test_derive_address_rejects_wrong_branch():
    d = multisig_descriptor(2, _signers(_three()), "0")
    info = parse_multisig_descriptor(d)
    with pytest.raises(ValueError):
        derive_address(info, 1, 0)


def test_descriptor_hardened_marker_and_order_change_text_not_wallet():
    from entropy_arena.wallet.descriptor import parse_multisig_descriptor, derive_address
    sg = _signers(_three())
    d_apos = multisig_descriptor(2, sg, "0")
    d_h = multisig_descriptor(2, sg, "0", hardened="h")
    assert "48h/1h/0h/2h" in d_h and "48'/1'/0'/2'" in d_apos
    assert d_apos.split("#")[1] != d_h.split("#")[1]           # el checksum cambia con el texto
    a1 = derive_address(parse_multisig_descriptor(d_apos), 0, 0)["address"]
    a2 = derive_address(parse_multisig_descriptor(d_h), 0, 0)["address"]
    a3 = derive_address(parse_multisig_descriptor(multisig_descriptor(2, sg[::-1], "0", "h")), 0, 0)["address"]
    assert a1 == a2 == a3                                       # misma wallet (sortedmulti)
