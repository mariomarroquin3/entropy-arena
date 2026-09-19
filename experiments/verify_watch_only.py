"""Reconstrucción watch-only: deriva direcciones SOLO desde el descriptor público.

Uso: python experiments/verify_watch_only.py "<descriptor o archivo>" [--network testnet]
                                             [--count 5] [--expect tb1q...]
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from entropy_arena.wallet.descriptor import parse_multisig_descriptor, derive_address


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("descriptor")
    ap.add_argument("--network", default="testnet", choices=["testnet", "regtest", "mainnet"])
    ap.add_argument("--count", type=int, default=5)
    ap.add_argument("--expect", help="dirección que muestra Sparrow, para comparar")
    a = ap.parse_args()

    p = Path(a.descriptor)
    text = p.read_text(encoding="utf-8") if p.exists() and p.is_file() else a.descriptor
    if "receive:" in text:  # archivo generado por build_descriptor.py
        text = next(l.split(":", 1)[1] for l in text.splitlines() if l.startswith("receive:"))
    info = parse_multisig_descriptor(text.strip())
    print(f"Política: {info['threshold']}-de-{len(info['keys'])}   checksum: "
          f"{'OK' if info['checksum_ok'] else 'no incluido'}")
    for k in info["keys"]:
        print(f"  fp={k['fingerprint']} ruta={k['path']} {k['xpub'][:14]}...")
    found = False
    for chain, name in ((0, "recepción"), (1, "cambio")):
        print(f"\nDirecciones de {name}:")
        for i in range(a.count):
            addr = derive_address(info, chain, i, a.network)["address"]
            mark = ""
            if a.expect and addr == a.expect:
                mark, found = "   <== COINCIDE", True
            print(f"  {chain}/{i}: {addr}{mark}")
    if a.expect:
        print("\nRESULTADO:", "COINCIDE" if found else "NO coincide (revisa red, descriptor o rango)")
        sys.exit(0 if found else 1)


if __name__ == "__main__":
    main()
