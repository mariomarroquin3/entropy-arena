import uuid
from ..base import EntropyMethod, EntropySample


class UUID4Method(EntropyMethod):
    name = "uuid.uuid4"
    category = "computational"
    is_deterministic = False
    theoretical_bits_per_unit = 122.0 / 16.0
    unit_description = "byte"

    def generate(self, nbytes: int) -> EntropySample:
        buf = bytearray()
        while len(buf) < nbytes:
            buf.extend(uuid.uuid4().bytes)
        data = bytes(buf[:nbytes])
        return EntropySample(self.name, data, nbytes * 8.0 * 122 / 128,
                             {"note": "122 bits de entropía por UUID"})
