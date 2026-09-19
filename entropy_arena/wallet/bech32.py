"""Bech32 (BIP173) para direcciones SegWit v0."""
CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _polymod(values):
    gen = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
    chk = 1
    for v in values:
        b = chk >> 25
        chk = (chk & 0x1ffffff) << 5 ^ v
        for i in range(5):
            chk ^= gen[i] if (b >> i) & 1 else 0
    return chk


def _hrp_expand(hrp):
    return [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]


def _convert_bits(data, frm, to):
    acc = bits = 0
    out, maxv = [], (1 << to) - 1
    for v in data:
        acc = (acc << frm) | v
        bits += frm
        while bits >= to:
            bits -= to
            out.append((acc >> bits) & maxv)
        acc &= (1 << bits) - 1
    if bits:
        out.append((acc << (to - bits)) & maxv)
    return out


def segwit_v0_address(hrp: str, program: bytes) -> str:
    if len(program) not in (20, 32):
        raise ValueError("programa witness v0 debe medir 20 o 32 bytes")
    data = [0] + _convert_bits(program, 8, 5)
    poly = _polymod(_hrp_expand(hrp) + data + [0] * 6) ^ 1
    checksum = [(poly >> 5 * (5 - i)) & 31 for i in range(6)]
    return hrp + "1" + "".join(CHARSET[d] for d in data + checksum)
