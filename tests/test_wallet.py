import pytest
from entropy_arena.wallet.key_derivation import master_key_from_seed, derive_path
from entropy_arena.wallet.seed_generator import (
    mnemonic_from_entropy, mnemonic_to_seed, generate_seed_from)
from entropy_arena.wallet.bech32 import segwit_v0_address
from entropy_arena.wallet.multisig_builder import build_multisig_vault, attack_bits
from entropy_arena.methods.computational.os_urandom import OsUrandomMethod
from entropy_arena.methods.computational.prng_family import RanduMethod


def test_bip32_vector1():
    m = master_key_from_seed(bytes(range(16)))
    assert m.priv.to_bytes(32, "big").hex() == \
        "e8f32e723decf4051aefac8e2c93c9c5b214313817cdb01a1494b917c8436b35"
    assert m.pub.hex() == \
        "0339a36013301597daef41fbe593a02cc513d0b55527ec2df1050e2e8ff49c85c2"
    c = derive_path(m, "m/0'")
    assert c.priv.to_bytes(32, "big").hex() == \
        "edb2e14f9ee77d26dd93b4ecede8d16ed408ce149b6cd80b0715a2d911a0afea"


def test_bip39_vector():
    phrase = mnemonic_from_entropy(bytes(16))
    assert phrase == "abandon " * 11 + "about"
    seed = mnemonic_to_seed(phrase, "TREZOR")
    assert seed.hex().startswith("c55257c360c07c72029aebc1b53c05ed0362ada38ead3e3e9efa3708e5349553")


def test_bech32_bip173_p2wpkh():
    prog = bytes.fromhex("751e76e8199196d454941c45d1b3a323f1433bd6")
    assert segwit_v0_address("bc", prog) == "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"


def test_weak_source_rejected():
    with pytest.raises(ValueError):
        generate_seed_from(RanduMethod(), nbytes=32)


def test_vault_2of3_and_attack_bits():
    v = build_multisig_vault([OsUrandomMethod()] * 3)
    assert v["address"].startswith("tb1q") and len(v["signers"]) == 3
    assert v["witness_script"].startswith("52") and v["witness_script"].endswith("53ae")
    assert attack_bits([64, 256, 256], 2) == 256
    assert attack_bits([64, 64, 256], 2) == 64


def test_descriptor_checksum_bip380_vector():
    from entropy_arena.wallet.descriptor import checksum
    assert checksum("raw(deadbeef)") == "89f8spxm"


def test_descriptor_matches_script():
    from entropy_arena.wallet.descriptor import checksum
    v = build_multisig_vault([OsUrandomMethod()] * 3)
    body, _, cs = v["descriptor"].partition("#")
    assert checksum(body) == cs and body.startswith("wsh(sortedmulti(2,")
    keys = body[len("wsh(sortedmulti(2,"):-2].split(",")
    from entropy_arena.wallet.multisig_builder import witness_script
    assert witness_script([bytes.fromhex(k) for k in keys], 2).hex() == v["witness_script"]


def test_ripemd160_fallback():
    from entropy_arena.wallet.hashes import _ripemd160_py
    assert _ripemd160_py(b"abc").hex() == "8eb208f7e05d987a9b044a8e98c6b087f15a0bfc"
    assert _ripemd160_py(b"").hex() == "9c1185a5c5e9fc54612808977ee8f548b2258d31"


def test_bip32_xpub_and_fingerprint_vector1():
    from entropy_arena.wallet.key_derivation import to_pub
    from entropy_arena.wallet.xkeys import serialize_pub, serialize_priv
    m = master_key_from_seed(bytes(range(16)))
    assert serialize_pub(to_pub(m), "mainnet") == (
        "xpub661MyMwAqRbcFtXgS5sYJABqqG9YLmC4Q1Rdap9gSE8NqtwybGhePY2gZ29ESFjqJoCu1Rupje8YtGqsefD265TMg7usUDFdp6W1EGMcet8")
    assert serialize_priv(m, "mainnet").startswith("xprv9s21ZrQH143K3QTDL4LXw2F7HEK3wJUD2nW2nRk4stbPy6cq3jPPqjiChkVvvNKmPGJxWUtg6LnF5kejMRNNU3TGtRBeJgk33yuGBxrMPHi")
    assert m.fingerprint.hex() == "3442193e"
    c = derive_path(m, "m/0'")
    assert serialize_pub(to_pub(c), "mainnet") == (
        "xpub68Gmy5EdvgibQVfPdqkBBCHxA5htiqg55crXYuXoQRKfDBFA1WEjWgP6LHhwBZeNK1VTsfTFUHCdrfp1bgwQ9xv5ski8PX9rL2dZXvgGDnw")


def test_public_derivation_matches_private_and_roundtrip():
    from entropy_arena.wallet.key_derivation import to_pub, derive_pub_child, derive_child
    from entropy_arena.wallet.xkeys import serialize_pub, parse_pub
    m = master_key_from_seed(bytes(range(16)))
    acct = derive_path(m, "m/48'/1'/0'/2'")
    s = serialize_pub(to_pub(acct))
    assert s.startswith("tpub")
    p = parse_pub(s)
    for i in (0, 1, 7):
        assert derive_pub_child(p, i).pub == derive_child(acct, i).pub


def test_coincurve_backend_matches_pure_python():
    import importlib
    from entropy_arena.wallet import key_derivation as kd
    m = master_key_from_seed(bytes(range(16)))
    child = derive_path(m, "m/48'/1'/0'/2'")
    assert kd.BACKEND.startswith("coincurve"), "coincurve no está instalado: se está probando solo el fallback"
    pub_coincurve = child.pub
    from entropy_arena.wallet.secp256k1 import pubkey_compressed
    assert pub_coincurve == pubkey_compressed(child.priv)

    from entropy_arena.wallet.key_derivation import derive_pub_child, to_pub
    acct_pub = to_pub(derive_path(m, "m/48'/1'/0'/2'"))
    coincurve_child_pub = derive_pub_child(acct_pub, 3).pub
    # forzar el camino Python puro y comparar
    kd.coincurve = None
    try:
        pure_child_pub = derive_pub_child(acct_pub, 3).pub
    finally:
        importlib.reload(kd)
    assert coincurve_child_pub == pure_child_pub
