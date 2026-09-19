import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from entropy_arena.manual_input.quality import dice_report, coin_report, format_report
from entropy_arena.manual_input.interactive import (
    record_dice, record_coins, record_deck_shuffle
)


def main():
    if len(sys.argv) < 2:
        print("Uso:")
        print("  run_manual_session.py dice <n>")
        print("  run_manual_session.py coins <n>")
        print("  run_manual_session.py deck")
        sys.exit(1)

    kind = sys.argv[1].lower()
    data_dir = ROOT / "data" / "manual_rolls"
    data_dir.mkdir(parents=True, exist_ok=True)

    if kind == "dice":
        out = record_dice(int(sys.argv[2]), str(data_dir / "dice.csv"))
        rolls = [int(r["value"]) for r in csv.DictReader(open(out))]
        print(format_report("dados", dice_report(rolls)))
    elif kind == "coins":
        out = record_coins(int(sys.argv[2]), str(data_dir / "coins.csv"))
        flips = [r["value"] for r in csv.DictReader(open(out))]
        print(format_report("monedas", coin_report(flips)))
    elif kind == "deck":
        record_deck_shuffle(str(data_dir / "deck.csv"))
    else:
        print(f"Tipo desconocido: {kind}")
        sys.exit(1)


if __name__ == "__main__":
    main()
