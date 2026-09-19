"""Ataques de demostración: pasar los tests estadísticos no implica ser impredecible.
Todos actúan sobre los propios métodos de la arena, con datos que un atacante vería."""
import random
import time
import numpy as np

from ..methods.mathematical.pi_digits import _pi_bits

M32 = 0xFFFFFFFF


# ------------------------------------------------------------- Mersenne Twister
def _undo_right(y: int, s: int) -> int:
    x = y
    for _ in range(32):
        x = y ^ (x >> s)
    return x


def _undo_left(y: int, s: int, mask: int) -> int:
    x = y
    for _ in range(32):
        x = y ^ ((x << s) & mask & M32)
    return x


def untemper(y: int) -> int:
    y = _undo_right(y, 18)
    y = _undo_left(y, 15, 0xEFC60000)
    y = _undo_left(y, 7, 0x9D2C5680)
    return _undo_right(y, 11)


def mt_clone_from_bytes(observed: bytes) -> random.Random:
    """Reconstruye el estado de random.Random a partir de 624 palabras de 32 bits
    (2496 bytes producidos por MersenneTwister.generate). Devuelve un clon que
    predice todas las salidas siguientes."""
    if len(observed) < 624 * 4:
        raise ValueError("se necesitan 2496 bytes observados")
    n = int.from_bytes(observed[:2496], "big")            # getrandbits(k): palabra 0 = menos significativa
    words = [(n >> (32 * i)) & M32 for i in range(624)]
    clone = random.Random()
    clone.setstate((3, tuple(untemper(w) for w in words) + (624,), None))
    return clone


def attack_mersenne_twister(method, check_bytes: int = 32) -> dict:
    """Observa 2496 bytes de `method` (MersenneTwister) y predice los siguientes."""
    t0 = time.perf_counter()
    observed = method.generate(2496).data
    clone = mt_clone_from_bytes(observed)
    predicted = clone.getrandbits(check_bytes * 8).to_bytes(check_bytes, "big")
    actual = method.generate(check_bytes).data
    return {"attack": "MT19937 state recovery", "observed_bytes": 2496,
            "success": predicted == actual, "seconds": round(time.perf_counter() - t0, 3)}


# ------------------------------------------------------------------------ RANDU
def randu_recover(outputs: bytes, steps: int = 8):
    """RanduMethod emite x>>23 (8 bits altos de 31). Recupera el estado x1 probando
    los 2^23 bajos y filtrando con las salidas siguientes."""
    cand = (np.arange(1 << 23, dtype=np.int64) | (outputs[0] << 23))
    x = cand.copy()
    for i in range(1, steps):
        x = (65539 * x) % (1 << 31)
        keep = (x >> 23) == outputs[i]
        cand, x = cand[keep], x[keep]
        if cand.size == 1:
            break
    return [int(c) for c in cand]


def attack_randu(method, check: int = 16) -> dict:
    t0 = time.perf_counter()
    data = method.generate(8 + check).data
    seen, future = data[:8], data[8:]
    cands = randu_recover(seen)
    ok = False
    if len(cands) == 1:
        x = cands[0]
        for _ in range(7):               # x1 -> estado tras las 8 observaciones
            x = (65539 * x) % (1 << 31)
        pred = bytearray()
        for _ in range(check):
            x = (65539 * x) % (1 << 31)
            pred.append(x >> 23)
        ok = bytes(pred) == future
    return {"attack": "RANDU state recovery", "observed_bytes": 8, "candidates_left": len(cands),
            "success": ok, "seconds": round(time.perf_counter() - t0, 3)}


# -------------------------------------------------------------------- bits de π
def attack_pi_offset(method, observed_bytes: int = 32) -> dict:
    """La 'semilla' de PiBitsMethod es un offset de ~23 bits en una constante pública."""
    s = method.generate(observed_bytes + 32)   # (la 1ª llamada calcula π: no cuenta)
    t0 = time.perf_counter()
    seen = np.unpackbits(np.frombuffer(s.data[:observed_bytes], dtype=np.uint8))
    hay = (_pi_bits() + 48).astype(np.uint8).tobytes()
    off = hay.find((seen + 48).astype(np.uint8).tobytes())
    ok = off == s.metadata["offset"]
    return {"attack": "pi offset search", "observed_bytes": observed_bytes,
            "success": ok, "seconds": round(time.perf_counter() - t0, 3)}


# ---------------------------------------------------------- semilla = reloj (débil)
def attack_time_seeded(window_seconds: int = 86400) -> dict:
    """Víctima: random.seed(int(time.time())). El atacante solo sabe el día aproximado."""
    now = int(time.time())
    secret_seed = now - random.randint(0, window_seconds - 1)
    out = random.Random(secret_seed).getrandbits(128)
    t0 = time.perf_counter()
    found = None
    for s in range(now - window_seconds, now + 1):
        if random.Random(s).getrandbits(128) == out:
            found = s
            break
    return {"attack": "time-seeded PRNG brute force", "search_space": window_seconds,
            "success": found == secret_seed, "seconds": round(time.perf_counter() - t0, 3)}
