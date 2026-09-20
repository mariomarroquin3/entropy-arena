"""Coordinador: combina los JSON públicos de los firmantes en el descriptor de la wallet.

Uso: python experiments/build_descriptor.py data/public/signer_a.json ... [--threshold 2]

Para que el descriptor sea IDÉNTICO al de Sparrow, pasa los JSON en el mismo orden que los
keystores de la wallet en Sparrow (el orden se respeta) y deja --hardened h (por defecto).
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from entropy_arena.wallet.descriptor import (multisig_descriptor, parse_multisig_descriptor,
                                             derive_address)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--threshold", type=int, default=2)
    ap.add_argument("--count", type=int, default=3)
    ap.add_argument("--hardened", choices=["h", "'"], default="h",
                    help="marca de paso endurecido: h (como Sparrow, por defecto) o '")
    a = ap.parse_args()

    pubs = [json.loads(Path(f).read_text(encoding="utf-8")) for f in a.files]
    nets = {p["network"] for p in pubs}
    if len(nets) != 1:
        raise SystemExit(f"redes mezcladas: {nets}")
    net = nets.pop()
    if (len({p["master_fingerprint"] for p in pubs}) != len(pubs)
            or len({p["xpub"] for p in pubs}) != len(pubs)):
        raise SystemExit("firmantes duplicados (misma clave): cada firmante debe ser independiente")
    signers = [{"fingerprint": p["master_fingerprint"], "path": p["path"], "xpub": p["xpub"]}
               for p in pubs]

    multi = multisig_descriptor(a.threshold, signers, "<0;1>", a.hardened)
    recv = multisig_descriptor(a.threshold, signers, "0", a.hardened)
    change = multisig_descriptor(a.threshold, signers, "1", a.hardened)
    out = ROOT / "data" / "public" / "wallet_descriptor.txt"
    out.write_text(f"network: {net}\nmultipath: {multi}\nreceive:   {recv}\nchange:    {change}\n",
                   encoding="utf-8")

    print(f"\n=== Wallet {a.threshold}-de-{len(signers)} P2WSH ({net}) ===")
    for p in pubs:
        print(f"  {p['label']:<12} fp={p['master_fingerprint']}  método={p['method']}  "
              f"bits={p['entropy_bits']}")
    print(f"\nDescriptor (multipath, Sparrow / Core >= 29):\n{multi}")
    print(f"\nDescriptor de recepción:\n{recv}\nDescriptor de cambio:\n{change}")
    info = parse_multisig_descriptor(recv)
    print("\nPrimeras direcciones de recepción (derivadas solo con datos públicos):")
    for i in range(a.count):
        print(f"  {i}: {derive_address(info, 0, i, net)['address']}")
    print(f"\nGuardado en {out}")


if __name__ == "__main__":
    main()
