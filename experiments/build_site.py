"""Genera el portal web (site/index.html) a partir de los resultados reproducibles.

Lee results/leaderboard.json, results/estimators.txt, results/structure_tests.txt y
results/attacks.txt, los incrusta en site/template.html y escribe:
  - site/index.html          página autónoma (se abre con doble clic o en GitHub Pages)
  - site/portal_fragment.html  mismo contenido sin <html>/<head> (para publicarlo como Artifact)

Uso: python experiments/build_site.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
SITE = ROOT / "site"


def _lines(name):
    return [l.rstrip("\r") for l in (RES / name).read_text(encoding="utf-8").splitlines()]


def parse_estimators():
    out = []
    for l in _lines("estimators.txt"):
        parts = re.split(r"\s{2,}", l.strip())
        if len(parts) == 5 and re.fullmatch(r"-?\d\.\d+", parts[1]):
            out.append({"source": parts[0], "true": float(parts[1]), "mcv": float(parts[2]),
                        "min10": max(0.0, float(parts[3])), "driver": parts[4]})
    return out


def parse_structure():
    rows, cols = [], ["binary_matrix_rank", "dft_spectral", "approx_entropy",
                      "linear_complexity", "linear_complexity_s32"]
    for l in _lines("structure_tests.txt"):
        parts = re.split(r"\s{2,}", l.strip())
        if len(parts) == 6 and parts[0] not in ("Método", "M�todo") and not parts[0].startswith("-") \
                and not parts[0].startswith("(") and all(re.fullmatch(r"\d+%|-", p) for p in parts[1:]):
            vals = [None if p == "-" else int(p.rstrip("%")) / 100 for p in parts[1:]]
            rows.append({"method": parts[0], "rates": dict(zip(cols, vals))})
    return {"columns": cols, "rows": rows}


def parse_attacks():
    out = []
    for l in _lines("attacks.txt"):
        m = re.match(r"^(.+?)\s{2,}(\d+)\s+(\S+)\s+([\d.]+)s\s*$", l)
        if m:
            out.append({"attack": m.group(1).strip(), "observed": int(m.group(2)),
                        "success": m.group(3) != "no", "seconds": float(m.group(4))})
    return out


def main():
    data = {
        "leaderboard": json.loads((RES / "leaderboard.json").read_text(encoding="utf-8")),
        "estimators": parse_estimators(),
        "structure": parse_structure(),
        "attacks": parse_attacks(),
    }
    assert data["estimators"] and data["structure"]["rows"] and data["attacks"], "no se pudieron leer los resultados"
    tpl = (SITE / "template.html").read_text(encoding="utf-8")
    fragment = tpl.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))
    (SITE / "portal_fragment.html").write_text(fragment, encoding="utf-8")
    page = ('<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n</head>\n<body>\n'
            + fragment + "\n</body>\n</html>\n")
    (SITE / "index.html").write_text(page, encoding="utf-8")
    print(f"OK: {SITE / 'index.html'} ({len(page) // 1024} KB), "
          f"{len(data['leaderboard'])} métodos, {len(data['attacks'])} ataques")


if __name__ == "__main__":
    main()
