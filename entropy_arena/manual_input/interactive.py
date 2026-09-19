import csv
from datetime import datetime
from pathlib import Path


def _prompt_int(msg: str, valid: set) -> int:
    while True:
        v = input(msg).strip()
        try:
            n = int(v)
            if n in valid:
                return n
        except ValueError:
            pass
        print(f"  Valor inválido. Opciones: {sorted(valid)}")


def record_dice(n: int, out_path: str) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    print(f"\n=== Registrando {n} tiradas de dado (1-6) ===\n")
    rows = []
    for i in range(1, n + 1):
        v = _prompt_int(f"Tirada {i:>3}/{n}: ", {1, 2, 3, 4, 5, 6})
        rows.append((datetime.now().isoformat(timespec="seconds"), v))
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "value"])
        w.writerows(rows)
    print(f"\nGuardado en {out}")
    return out


def record_coins(n: int, out_path: str) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    print(f"\n=== Registrando {n} lanzamientos de moneda (H/T) ===\n")
    rows = []
    for i in range(1, n + 1):
        while True:
            v = input(f"Lanzamiento {i:>3}/{n}: ").strip().upper()
            if v in ("H", "T"):
                break
            print("  Usa H o T.")
        rows.append((datetime.now().isoformat(timespec="seconds"), v))
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "value"])
        w.writerows(rows)
    print(f"\nGuardado en {out}")
    return out


def record_deck_shuffle(out_path: str) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    print("\n=== Registrando permutación de baraja ===")
    print("Introduce 52 números separados por espacios (0..51).")
    while True:
        raw = input("Permutación: ").strip()
        try:
            perm = [int(x) for x in raw.split()]
            if sorted(perm) == list(range(52)):
                break
        except ValueError:
            pass
        print("  Debe ser una permutación de 0..51.")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "permutation"])
        w.writerow([datetime.now().isoformat(timespec="seconds"),
                    " ".join(str(x) for x in perm)])
    print(f"\nGuardado en {out}")
    return out
