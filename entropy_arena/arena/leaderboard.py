import json
from pathlib import Path


def print_leaderboard(results: list) -> None:
    print()
    print("=" * 112)
    print(f"{'#':>2}  {'Método':<32} {'Categoría':<15} {'Calidad':>7} "
          f"{'Bits reales':>11} {'MinEnt':>7} {'n':>4}  Veredicto")
    print("-" * 112)
    for i, r in enumerate(results, 1):
        m = r.get("metrics", {})
        print(f"{i:>2}  {r['method'][:32]:<32} {r['category']:<15} "
              f"{r['score']:>7.1f} {r.get('real_bits', 0):>11.1f} "
              f"{m.get('min_entropy', 0):>7.3f} {r['samples_ok']:>4}  {r['verdict']}")
        if r.get("note"):
            print(f"      ! {r['note']}")
    print("=" * 112)
    print("Calidad = apariencia estadística (NIST prop.+uniformidad, min-entropy MCV).")
    print("Bits reales = entropía genuina por muestra (techo: seed/entrada física).")
    print()


def save_results(results: list, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"[arena] Resultados guardados en {out_path}")
