import csv
import hashlib
from pathlib import Path
from typing import List, Optional
from ..base import EntropyMethod, EntropySample
from ...manual_input.quality import mcv_bits_per_symbol


class ManualCoinFlips(EntropyMethod):
    name = "manual_coin_flips"
    category = "physical-manual"
    is_deterministic = False
    theoretical_bits_per_unit = 1.0
    unit_description = "flip"

    def __init__(self, csv_path: Optional[str] = None,
                 flips: Optional[List[str]] = None):
        self.csv_path = Path(csv_path) if csv_path else None
        self._flips = list(flips) if flips else []

    def _load(self) -> List[str]:
        if self._flips:
            return self._flips
        if self.csv_path and self.csv_path.exists():
            vals = []
            with open(self.csv_path) as f:
                for row in csv.DictReader(f):
                    vals.append(row["value"].strip().upper())
            return vals
        return []

    def generate(self, nbytes: int) -> EntropySample:
        flips = self._load()
        if not flips:
            raise ValueError("Sin flips para coin_flips")
        bits = [1 if f == "H" else 0 for f in flips]
        data = bytearray()
        for i in range(0, len(bits), 8):
            byte = 0
            chunk = bits[i:i + 8]
            for b in chunk:
                byte = (byte << 1) | b
            byte <<= (8 - len(chunk))
            data.append(byte)
        raw = bytes(data)
        digest = hashlib.sha256(raw).digest()
        while len(digest) < nbytes:
            digest += hashlib.sha256(digest).digest()
        return EntropySample(
            self.name, digest[:nbytes], len(flips) * mcv_bits_per_symbol(flips, 2),
            {"n_flips": len(flips), "csv": str(self.csv_path) if self.csv_path else None}
        )
