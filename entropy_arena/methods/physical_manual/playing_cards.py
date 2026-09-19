import csv
import hashlib
import math
from pathlib import Path
from typing import List, Optional
from ..base import EntropyMethod, EntropySample


class ManualDeckShuffle(EntropyMethod):
    name = "manual_deck_shuffle"
    category = "physical-manual"
    is_deterministic = False
    theoretical_bits_per_unit = math.log2(math.factorial(52)) / 52
    unit_description = "card"

    def __init__(self, csv_path: Optional[str] = None,
                 permutation: Optional[List[int]] = None):
        self.csv_path = Path(csv_path) if csv_path else None
        self._perm = list(permutation) if permutation else []

    def _load(self) -> List[int]:
        if self._perm:
            return self._perm
        if self.csv_path and self.csv_path.exists():
            with open(self.csv_path) as f:
                row = next(csv.DictReader(f))
            return [int(x) for x in row["permutation"].split()]
        return []

    def generate(self, nbytes: int) -> EntropySample:
        perm = self._load()
        if not perm:
            raise ValueError("Sin permutación de baraja")
        if sorted(perm) != list(range(52)):
            raise ValueError("La permutación debe contener 0..51 sin repetir")
        n = 0
        available = list(range(52))
        for c in perm:
            idx = available.index(c)
            n = n * len(available) + idx
            available.pop(idx)
        raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
        digest = hashlib.sha256(raw).digest()
        while len(digest) < nbytes:
            digest += hashlib.sha256(digest).digest()
        return EntropySample(
            self.name, digest[:nbytes], math.log2(math.factorial(52)),
            {"n_cards": 52}
        )
