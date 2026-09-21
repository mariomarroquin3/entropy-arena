"""Crea el JSON público de un firmante a partir de los datos que muestra Sparrow.

Útil cuando las claves salieron de wallets personales (p. ej. m/84'/1'/0') en vez de
`signer_export.py` (m/48'/1'/0'/2'). Valida que la xpub y la ruta sean coherentes.
NO pide ni acepta mnemónicos: solo datos públicos.

Uso:
  python experiments/import_public_keystore.py NOMBRE --fingerprint 58ea39a7 ^
      --path "m/84'/1'/0'" --xpub tpubD...  [--network regtest]

Después: python experiments/build_descriptor.py data/public/signer_*.json
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from entropy_arena.wallet.signer import public_keystore_export


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--fingerprint", required=True, help="master fingerprint (8 hex) del keystore en Sparrow")
    ap.add_argument("--path", required=True, help="ruta de derivación del keystore, p. ej. m/84'/1'/0'")
    ap.add_argument("--xpub", required=True, help="tpub del keystore")
    ap.add_argument("--network", default="regtest", choices=["testnet", "regtest"])
    a = ap.parse_args()
    try:
        pub = public_keystore_export(a.name, a.fingerprint, a.path, a.xpub, a.network)
    except ValueError as e:
        raise SystemExit(f"[rechazado] {e}")
    out = ROOT / "data" / "public" / f"signer_{a.name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(pub, indent=2), encoding="utf-8")
    print(f"OK: {out}")
    print(f"  fingerprint={pub['master_fingerprint']}  ruta={pub['path']}  xpub={pub['xpub'][:16]}...")
    if not pub["path"].startswith("m/48'"):
        print("  Aviso: ruta distinta de BIP48 (m/48'/coin'/0'/2'). Es válido si TODOS los "
              "firmantes declaran la misma ruta con la que se derivó su xpub.")


if __name__ == "__main__":
    main()
