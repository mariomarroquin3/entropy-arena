import csv
import hashlib
from pathlib import Path
from typing import List, Optional
from ..base import EntropyMethod, EntropySample


class CoinVonNeumann(EntropyMethod):
    name = "coin_flips_von_neumann"
    category = "hybrid"
    is_deterministic = False
    theoretical_bits_per_unit = 1.0
    unit_description = "pair"

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
            raise ValueError("Sin flips para von Neumann")
        bits = []
        for i in range(0, len(flips) - 1, 2):
            a, b = flips[i], flips[i + 1]
            if a != b:
                bits.append(1 if a == "H" else 0)
        data = bytearray()
        for i in range(0, len(bits), 8):
            chunk = bits[i:i + 8]
            byte = 0
            for b in chunk:
                byte = (byte << 1) | b
            byte <<= (8 - len(chunk))
            data.append(byte)
        raw = bytes(data)
        digest = hashlib.sha256(raw).digest()
        while len(digest) < nbytes:
            digest += hashlib.sha256(digest).digest()
        return EntropySample(
            self.name, digest[:nbytes], float(len(bits)),
            {"n_flips": len(flips), "n_kept": len(bits),
             "efectividad": len(bits) / max(1, len(flips))}
        )
