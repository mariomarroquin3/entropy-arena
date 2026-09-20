import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "check_submission", Path(__file__).resolve().parents[1] / "experiments" / "check_submission.py")
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)

MNEMONIC = "abandon " * 11 + "about"          # vector BIP39 válido (12 palabras)


def test_detects_valid_mnemonic_inside_text():
    assert cs.scan_text(f"Mis palabras son: {MNEMONIC}. No las compartas.")


def test_ignores_ordinary_prose_and_invalid_sequences():
    assert not cs.scan_text("la wallet usa un descriptor con tpub y fingerprints publicos")
    assert not cs.scan_text("abandon " * 12)      # palabras válidas pero checksum inválido


def test_detects_extended_private_key():
    from entropy_arena.wallet.key_derivation import master_key_from_seed
    from entropy_arena.wallet.xkeys import serialize_priv
    tprv = serialize_priv(master_key_from_seed(bytes(range(16))), "testnet")
    assert cs.scan_text(f"clave: {tprv}")


def test_public_data_is_clean():
    from entropy_arena.wallet.key_derivation import master_key_from_seed, to_pub
    from entropy_arena.wallet.xkeys import serialize_pub
    tpub = serialize_pub(to_pub(master_key_from_seed(bytes(range(16)))), "testnet")
    assert not cs.scan_text(f"tpub publico: {tpub}")
