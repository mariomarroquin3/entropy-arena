import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from entropy_arena.methods.computational.secrets_csprng import SecretsMethod
from entropy_arena.methods.physical_manual.dice_rolls import ManualDiceRolls
from entropy_arena.methods.physical_manual.coin_flips import ManualCoinFlips
from entropy_arena.wallet.multisig_builder import build_multisig_vault


def pick(name: str):
    data_dir = ROOT / "data" / "manual_rolls"
    if name == "secrets":
        return SecretsMethod()
    if name == "urandom":
        from entropy_arena.methods.computational.os_urandom import OsUrandomMethod
        return OsUrandomMethod()
    if name == "pcg":
        from entropy_arena.methods.computational.prng_family import Pcg64Method
        return Pcg64Method()
    if name == "dice":
        return ManualDiceRolls(csv_path=str(data_dir / "dice.csv"))
    if name == "coins":
        return ManualCoinFlips(csv_path=str(data_dir / "coins.csv"))
    raise ValueError(f"Método desconocido: {name}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    show = "--show-secrets" in sys.argv
    weak = "--allow-weak" in sys.argv
    net = "mainnet" if "--mainnet" in sys.argv else "testnet"
    names = args or ["secrets", "dice", "coins"]
    if len(names) != 3:
        print("Uso: run_multisig.py <m1> <m2> <m3> [--show-secrets] [--allow-weak] [--mainnet]")
        sys.exit(1)
    methods = [pick(n) for n in names]
    try:
        vault = build_multisig_vault(methods, nbytes=32, threshold=2, total=3,
                                     network=net, allow_weak=weak)
    except ValueError as e:
        print(f"[abortado] {e}")
        sys.exit(2)
    print()
    print(f"=== BÓVEDA MULTISIG 2-de-3 ({vault['network']}, P2WSH BIP48) ===")
    print()
    for s in vault["signers"]:
        print(f"Firmante {s['signer']} - {s['method']}")
        print(f"  bits de entropía: {s['bits_claimed']:.1f} ({s['words']} palabras)")
        print(f"  master id: {s['master_id']}   pubkey: {s['pubkey']}")
        if show:
            print(f"  MNEMÓNICO: {s['mnemonic']}")
        print()
    print(f"witnessScript: {vault['witness_script']}")
    print(f"Dirección:     {vault['address']}")
    print(f"Descriptor:    {vault['descriptor']}")
    print(f"Esfuerzo de ataque (2 firmantes más débiles): ~2^{vault['attack_bits']:.0f}")
    if not show:
        print("(mnemónicos ocultos; usa --show-secrets solo en un equipo air-gapped)")


if __name__ == "__main__":
    main()
