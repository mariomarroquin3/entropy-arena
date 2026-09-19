import os
from ..base import EntropyMethod, EntropySample


class OsUrandomMethod(EntropyMethod):
    name = "os.urandom"
    category = "computational"
    is_deterministic = False
    theoretical_bits_per_unit = 8.0
    unit_description = "byte"

    def generate(self, nbytes: int) -> EntropySample:
        data = os.urandom(nbytes)
        return EntropySample(self.name, data, nbytes * 8.0,
                             {"source": "/dev/urandom o equivalente"})
