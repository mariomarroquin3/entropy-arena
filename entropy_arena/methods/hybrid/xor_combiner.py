from ..base import EntropyMethod, EntropySample


class XorCombiner(EntropyMethod):
    """XOR de varias fuentes independientes. Si al menos una es impredecible,
    la salida lo es: entropía >= max(componentes), nunca la suma garantizada."""
    category = "hybrid"
    is_deterministic = False
    theoretical_bits_per_unit = None
    unit_description = "byte"

    def __init__(self, methods: list):
        if len(methods) < 2:
            raise ValueError("XorCombiner requiere >= 2 fuentes")
        self.methods = methods
        self.name = "xor(" + "+".join(m.name.split(" ")[0] for m in methods) + ")"

    def generate(self, nbytes: int) -> EntropySample:
        samples = [m.generate(nbytes) for m in self.methods]
        out = bytearray(nbytes)
        for s in samples:
            for i, b in enumerate(s.data[:nbytes]):
                out[i] ^= b
        bits = min(max(s.bits_claimed for s in samples), 8.0 * nbytes)
        return EntropySample(self.name, bytes(out), bits,
                             {"components": [s.method_name for s in samples],
                              "note": "cota inferior: max de bits de los componentes"})
