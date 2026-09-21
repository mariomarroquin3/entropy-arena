"""Un firmante genera SU clave en SU equipo y exporta solo datos públicos.

Uso:
  python experiments/signer_export.py <nombre> [--method secrets|urandom|pcg|dice|coins|xor-dice|xor-coins]
                                      [--network testnet|regtest] [--mnemonic "24 palabras"]
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from entropy_arena.wallet.signer import create_signer, signer_from_mnemonic


def pick(name: str):
    data = ROOT / "data" / "manual_rolls"
    if name == "secrets":
        from entropy_arena.methods.computational.secrets_csprng import SecretsMethod
        return SecretsMethod()
    if name == "urandom":
        from entropy_arena.methods.computational.os_urandom import OsUrandomMethod
        return OsUrandomMethod()
    if name == "pcg":
        from entropy_arena.methods.computational.prng_family import Pcg64Method
        return Pcg64Method()
    if name == "dice":
        from entropy_arena.methods.physical_manual.dice_rolls import ManualDiceRolls
        return ManualDiceRolls(csv_path=str(data / "dice.csv"))
    if name == "coins":
        from entropy_arena.methods.physical_manual.coin_flips import ManualCoinFlips
        return ManualCoinFlips(csv_path=str(data / "coins.csv"))
    if name in ("xor-dice", "xor-coins"):
        # defensa en profundidad: CSPRNG XOR fuente física. Si la física fuera mala, sigue habiendo 256 bits.
        from entropy_arena.methods.hybrid.xor_combiner import XorCombiner
        from entropy_arena.methods.computational.secrets_csprng import SecretsMethod
        return XorCombiner([SecretsMethod(), pick(name.split("-")[1])])
    raise SystemExit(f"método desconocido: {name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--method", default="secrets")
    ap.add_argument("--network", default="testnet", choices=["testnet", "regtest"])
    ap.add_argument("--mnemonic", help="importar un mnemónico existente (queda en el historial: prefiere --ask-mnemonic)")
    ap.add_argument("--ask-mnemonic", action="store_true",
                    help="pide las 24 palabras sin mostrarlas ni guardarlas, y exporta solo datos públicos (ruta 48')")
    a = ap.parse_args()

    if a.ask_mnemonic:
        import getpass
        a.mnemonic = " ".join(getpass.getpass("24 palabras (no se muestran): ").split())
    if a.mnemonic:
        try:
            pub, secret = signer_from_mnemonic(a.mnemonic, a.name, a.network), None
        except ValueError as e:
            raise SystemExit(f"[abortado] {e}")
    else:
        try:
            secret, pub = create_signer(pick(a.method), a.name, a.network)
        except ValueError as e:
            raise SystemExit(f"[abortado] {e}")

    out = ROOT / "data" / "public" / f"signer_{a.name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(pub, indent=2), encoding="utf-8")

    print(f"\n=== Firmante '{a.name}' ({a.network}) ===")
    print(f"fingerprint maestro: {pub['master_fingerprint']}")
    print(f"ruta de cuenta:      {pub['path']}")
    print(f"tpub:                {pub['xpub']}")
    print(f"\nArchivo PÚBLICO (compártelo con el coordinador): {out}")
    if secret:
        print("\n" + "!" * 70)
        print("MNEMÓNICO SECRETO - anótalo en papel, NO lo guardes en archivos ni lo envíes.")
        print("Solo va en TU equipo/Sparrow. No lo incluyas en la entrega.")
        print("!" * 70)
        print(secret)


if __name__ == "__main__":
    main()
