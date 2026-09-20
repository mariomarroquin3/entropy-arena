"""Revisa una carpeta de entrega y avisa si contiene material secreto en archivos de texto.

Busca: mnemónicos BIP39 válidos (12-24 palabras seguidas), claves privadas extendidas
(xprv/tprv) y claves privadas WIF. NO puede leer capturas de pantalla: revísalas a mano.

Uso: python experiments/check_submission.py <carpeta>
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mnemonic import Mnemonic

TEXT_EXT = {".txt", ".md", ".json", ".csv", ".log", ".psbt", ".desc", ".py", ".html"}
_M = Mnemonic("english")
_WORDS = set(_M.wordlist)
_XPRV = re.compile(r"\b[xt]prv[1-9A-HJ-NP-Za-km-z]{100,}\b")
_WIF = re.compile(r"\b[5KL9c][1-9A-HJ-NP-Za-km-z]{50,51}\b")


def find_mnemonics(text: str) -> list:
    words = re.findall(r"[a-z]+", text.lower())
    hits = []
    for size in (24, 21, 18, 15, 12):
        for i in range(len(words) - size + 1):
            chunk = words[i:i + size]
            if all(w in _WORDS for w in chunk) and _M.check(" ".join(chunk)):
                hits.append(" ".join(chunk[:3]) + " ...")
    return hits


def scan_text(text: str) -> list:
    problems = []
    for h in find_mnemonics(text):
        problems.append(f"mnemónico BIP39 válido ({h})")
    if _XPRV.search(text):
        problems.append("clave privada extendida (xprv/tprv)")
    if _WIF.search(text):
        problems.append("posible clave privada WIF")
    return problems


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    folder = Path(sys.argv[1])
    bad, checked, images = 0, 0, 0
    for f in sorted(folder.rglob("*")):
        if not f.is_file():
            continue
        if f.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".pdf"}:
            images += 1
            continue
        if f.suffix.lower() not in TEXT_EXT:
            continue
        checked += 1
        try:
            problems = scan_text(f.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
        for p in problems:
            bad += 1
            print(f"[SECRETO] {f}: {p}")
    print(f"\n{checked} archivos de texto revisados, {bad} problema(s).")
    if images:
        print(f"ATENCIÓN: {images} imagen(es)/PDF/video no se pueden revisar automáticamente: "
              "ábrelos y confirma que no muestran palabras, tprv ni contraseñas.")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
