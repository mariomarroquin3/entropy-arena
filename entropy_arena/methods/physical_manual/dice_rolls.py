import csv
import hashlib
from pathlib import Path
from typing import List, Optional
from ..base import EntropyMethod, EntropySample
from ...manual_input.quality import mcv_bits_per_symbol


class ManualDiceRolls(EntropyMethod):
    name = "manual_dice_rolls"
    category = "physical-manual"
    is_deterministic = False
    theoretical_bits_per_unit = 2.585
    unit_description = "roll"

    def __init__(self, csv_path: Optional[str] = None,
                 rolls: Optional[List[int]] = None):
        self.csv_path = Path(csv_path) if csv_path else None
        self._rolls = list(rolls) if rolls else []

    def _load(self) -> List[int]:
        if self._rolls:
            return self._rolls
        if self.csv_path and self.csv_path.exists():
            vals = []
            with open(self.csv_path) as f:
                for row in csv.DictReader(f):
                    vals.append(int(row["value"]))
            return vals
        return []

    def generate(self, nbytes: int) -> EntropySample:
        rolls = self._load()
        if not rolls:
            raise ValueError(f"Sin tiradas para '{self.name}'.")
        n = 0
        for r in rolls:
            if not 1 <= r <= 6:
                raise ValueError(f"Tirada inválida: {r}")
            n = n * 6 + (r - 1)
        raw = n.to_bytes((n.bit_length() + 7) // 8, "big") or b"\x00"
        data = hashlib.sha256(raw).digest()
        while len(data) < nbytes:
            data += hashlib.sha256(data).digest()
        data = data[:nbytes]
        return EntropySample(
            self.name, data, len(rolls) * mcv_bits_per_symbol(rolls, 6),
            {"n_rolls": len(rolls), "csv": str(self.csv_path) if self.csv_path else None}
        )
