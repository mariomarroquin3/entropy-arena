import secrets
from ..base import EntropyMethod, EntropySample


class SecretsMethod(EntropyMethod):
    name = "secrets.token_bytes"
    category = "computational"
    is_deterministic = False
    theoretical_bits_per_unit = 8.0
    unit_description = "byte"

    def generate(self, nbytes: int) -> EntropySample:
        data = secrets.token_bytes(nbytes)
        return EntropySample(self.name, data, nbytes * 8.0,
                             {"source": "CSPRNG del sistema operativo"})
