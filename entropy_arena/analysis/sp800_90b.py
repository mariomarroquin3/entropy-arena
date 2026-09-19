"""Estimadores de min-entropy de NIST SP 800-90B §6.3 (fuentes no-IID) para
secuencias binarias. Devuelven bits de min-entropy POR BIT (0..1); el estimado final
es el mínimo de los diez, como exige el estándar.

Implementados: MCV, Collision, Markov, Compression, t-Tuple, LRS, MultiMCW, Lag,
MultiMMC, LZ78Y.

Desviaciones respecto al estándar (documentadas para no sobreestimar la fidelidad):
- t-Tuple/LRS limitan la longitud de tupla a 63 bits (cabe en int64).
- Los predictores (MultiMCW, Lag, MultiMMC, LZ78Y) se evalúan sobre los primeros
  `predictor_bits` bits (por coste en Python) y el marcador de subpredictor usa el
  acierto acumulado (sin la ventana de "reciente" del estándar).
- Compression usa bloques de b=6 bits y d=1000, como el estándar.
El estándar pide >= 1 Mbit; con menos, las cotas son más conservadoras."""
import math
import numpy as np

Z = 2.576  # cuantil 99.5% (IC 99% bilateral, como en el estándar)
MAX_TUPLE = 63


def _bits(x) -> np.ndarray:
    if isinstance(x, (bytes, bytearray)):
        return np.unpackbits(np.frombuffer(x, dtype=np.uint8))
    return np.asarray(x, dtype=np.uint8)


def _pu(p: float, n: int) -> float:
    return min(1.0, p + Z * math.sqrt(max(p * (1 - p), 0.0) / (n - 1)))


# ------------------------------------------------------------------ IID-like
def mcv(bits) -> float:
    b = _bits(bits)
    p = max(b.mean(), 1 - b.mean())
    return -math.log2(_pu(p, b.size))


def collision(bits) -> float:
    b = _bits(bits).tolist()
    times, i, n = [], 0, len(b)
    while i + 1 < n:
        if b[i] == b[i + 1]:
            times.append(2)
            i += 2
        elif i + 2 < n:
            times.append(3)
            i += 3
        else:
            break
    v = len(times)
    if v < 2:
        return 1.0
    t = np.asarray(times, dtype=float)
    lower_mean = t.mean() - Z * t.std(ddof=1) / math.sqrt(v)
    if lower_mean >= 2.5:
        return 1.0
    pq = max(0.0, (lower_mean - 2.0) / 2.0)          # E[t] = 2 + 2pq
    p = 0.5 * (1 + math.sqrt(max(0.0, 1 - 4 * pq)))
    return -math.log2(min(1.0, p))


def markov(bits, chain_len: int = 128) -> float:
    b = _bits(bits)
    p1 = b.mean()
    init = np.array([1 - p1, p1])
    trans = np.zeros((2, 2))
    for a in (0, 1):
        m = b[:-1] == a
        tot = m.sum()
        for c in (0, 1):
            trans[a, c] = ((b[1:][m] == c).sum() / tot) if tot else 0.5
    li = np.log2(np.maximum(init, 1e-300))
    lt = np.log2(np.maximum(trans, 1e-300))
    best = li.copy()
    for _ in range(chain_len - 1):
        best = np.array([max(best[a] + lt[a, c] for a in (0, 1)) for c in (0, 1)])
    return min(1.0, -best.max() / chain_len)


def compression(bits, b: int = 6, d: int = 1000) -> float:
    """§6.3.4 (Maurer universal). Distancias entre apariciones de bloques de b bits."""
    x = _bits(bits)
    nblk = x.size // b
    if nblk <= d + 100:
        return 1.0
    blocks = x[:nblk * b].reshape(nblk, b) @ (1 << np.arange(b - 1, -1, -1))
    last = {}
    logs = []
    for i, s in enumerate(blocks.tolist(), start=1):
        if i > d:
            logs.append(math.log2(i - last[s]) if s in last else math.log2(i))
        last[s] = i
    v = len(logs)
    la = np.asarray(logs)
    xbar = la.mean()
    sigma = 0.5907 * la.std(ddof=1)
    xbar_low = xbar - Z * sigma / math.sqrt(v)
    L = nblk
    u = np.arange(1, L + 1, dtype=float)
    logu = np.log2(u)
    t = np.arange(d + 1, L + 1)

    def G(z):
        if z <= 0.0:
            return 0.0
        if z >= 1.0:
            return 0.0
        lp = np.log1p(-z)
        terms = logu * (z * z) * np.exp((u - 1) * lp)
        cum = np.concatenate([[0.0], np.cumsum(terms)])       # cum[k] = sum_{u<=k}
        a = cum[t - 1]                                        # sum_{u=1}^{t-1}
        tail = logu[t - 1] * z * np.exp((t - 1) * lp)
        return float(np.mean(a + tail))

    def E(p):
        q = (1 - p) / (2 ** b - 1)
        return G(p) + (2 ** b - 1) * G(q)

    lo, hi = 1.0 / 2 ** b, 1.0 - 1e-9
    if E(lo) <= xbar_low:  # incluso p uniforme explica menos que lo observado
        return 1.0
    for _ in range(60):     # E decrece con p
        mid = (lo + hi) / 2
        if E(mid) > xbar_low:
            lo = mid
        else:
            hi = mid
    return min(1.0, -math.log2(hi) / b)


# ------------------------------------------------------------------- tuplas
def _window_values(x: np.ndarray, w: int) -> np.ndarray:
    vals = x[: x.size - w + 1].astype(np.int64)
    for k in range(1, w):
        vals = (vals << 1) | x[k: x.size - w + 1 + k]
    return vals


def _tuple_counts(x: np.ndarray, w_max: int):
    """Yield (w, counts de cada w-tupla) para w = 1..w_max, incrementalmente."""
    vals = x[: x.size].astype(np.int64)
    n = x.size
    for w in range(1, w_max + 1):
        if w == 1:
            cur = vals.copy()
        else:
            cur = (cur[:-1] << 1) | x[w - 1:].astype(np.int64)
        yield w, np.unique(cur, return_counts=True)[1], n - w + 1


def t_tuple(bits) -> float:
    x = _bits(bits)
    pmax = 0.0
    for w, counts, m in _tuple_counts(x, MAX_TUPLE):
        c = counts.max()
        if c < 35:
            break
        pmax = max(pmax, (c / m) ** (1.0 / w))
    if pmax == 0.0:  # ninguna tupla llega a 35 apariciones ni con t=1: fuente muy corta
        return 1.0
    return -math.log2(_pu(pmax, x.size))


def lrs(bits) -> float:
    x = _bits(bits)
    u, v, pw = None, 0, {}
    for w, counts, m in _tuple_counts(x, MAX_TUPLE):
        if u is None and counts.max() < 35:
            u = w
        if counts.max() >= 2:
            v = w
        if u is not None:
            if counts.max() < 2:
                break
            pairs = float(np.sum(counts.astype(float) * (counts - 1) / 2.0))
            tot = m * (m - 1) / 2.0
            pw[w] = (pairs / tot) ** (1.0 / w) if tot > 0 else 0.0
    if u is None:      # tuplas de hasta 63 bits aún se repiten >= 35 veces: casi determinista
        return 0.0
    if not pw:
        return 1.0
    return -math.log2(_pu(max(pw.values()), x.size))


# ---------------------------------------------------------------- predictores
def _local_p(n: int, r: int) -> float:
    """p tal que P(racha >= r+1 en n ensayos) = 0.99 (aprox. de Feller, §6.3.7)."""
    rr = r + 1

    def p_no_run(p):
        q = 1 - p
        xx = 1.0
        for _ in range(2000):
            nx = 1 + q * p ** rr * xx ** (rr + 1)
            if abs(nx - xx) < 1e-13:
                break
            xx = nx
            if xx > 1e6:
                return 0.0
        den = (rr + 1 - rr * xx) * q
        if 1 - p * xx <= 0 or den <= 0:
            return 0.0
        return math.exp(math.log((1 - p * xx) / den) - (n + 1) * math.log(xx))

    lo, hi = 0.0, 1.0 - 1e-12
    for _ in range(50):
        mid = (lo + hi) / 2
        if p_no_run(mid) > 0.01:
            lo = mid
        else:
            hi = mid
    return hi


def _predictor_entropy(correct: np.ndarray) -> float:
    n = correct.size
    if n < 100:
        return 1.0
    c = int(correct.sum())
    p_hat = c / n
    p_global = 1 - 0.01 ** (1.0 / n) if c == 0 else min(1.0, p_hat + Z * math.sqrt(p_hat * (1 - p_hat) / (n - 1)))
    r, cur = 0, 0
    for ok in correct.tolist():
        cur = cur + 1 if ok else 0
        r = max(r, cur)
    p_local = _local_p(n, r)
    return -math.log2(max(p_global, p_local, 0.5))


def _scoreboard(C: np.ndarray, start: int) -> np.ndarray:
    """C[k, i]=1 si el subpredictor k acierta en i. Devuelve aciertos del predictor
    global, que en cada i usa el subpredictor con mayor acierto acumulado previo."""
    cum = np.cumsum(C, axis=1, dtype=np.int32)
    idx = np.arange(start, C.shape[1])
    best = np.argmax(cum[:, idx - 1], axis=0)
    return C[best, idx]


def lag(bits, max_lag: int = 128) -> float:
    x = _bits(bits)
    n = x.size
    d = min(max_lag, n // 10)
    C = np.zeros((d, n), dtype=np.uint8)
    for k in range(1, d + 1):
        C[k - 1, k:] = x[k:] == x[:-k]
    return _predictor_entropy(_scoreboard(C, d + 1))


def multimcw(bits, windows=(63, 255, 1023, 4095)) -> float:
    x = _bits(bits)
    n = x.size
    cs = np.concatenate([[0], np.cumsum(x, dtype=np.int64)])
    C = np.zeros((len(windows), n), dtype=np.uint8)
    idx = np.arange(1, n)
    for k, w in enumerate(windows):
        lo = np.maximum(idx - w, 0)
        ones = cs[idx] - cs[lo]
        size = idx - lo
        pred = np.where(2 * ones == size, x[idx - 1], (2 * ones > size).astype(np.uint8))
        C[k, 1:] = pred == x[1:]
    return _predictor_entropy(_scoreboard(C, max(windows[0], 2)))


def multimmc(bits, max_order: int = 16) -> float:
    x = _bits(bits).tolist()
    n = len(x)
    C = np.zeros((max_order, n), dtype=np.uint8)
    for k in range(1, max_order + 1):
        table, ctx, mask = {}, 0, (1 << k) - 1
        for i in range(n):
            if i >= k:
                c = table.get(ctx)
                if c is None:
                    c = table[ctx] = [0, 0]
                if (1 if c[1] > c[0] else 0) == x[i] and (c[0] or c[1]):
                    C[k - 1, i] = 1
                c[x[i]] += 1
            ctx = ((ctx << 1) | x[i]) & mask
    return _predictor_entropy(_scoreboard(C, max_order + 1))


def lz78y(bits, max_len: int = 16, max_dict: int = 65536) -> float:
    x = _bits(bits).tolist()
    n = len(x)
    table, correct = {}, np.zeros(n, dtype=np.uint8)
    for i in range(max_len, n):
        pred = None
        for j in range(max_len, 0, -1):                 # contexto más largo primero
            key = (j, tuple(x[i - j:i]))
            c = table.get(key)
            if c is not None:
                pred = 1 if c[1] > c[0] else 0
                break
        if pred is not None and pred == x[i]:
            correct[i] = 1
        for j in range(1, max_len + 1):
            key = (j, tuple(x[i - j:i]))
            c = table.get(key)
            if c is None:
                if len(table) < max_dict:
                    table[key] = c = [0, 0]
                else:
                    continue
            c[x[i]] += 1
    return _predictor_entropy(correct[max_len:])


IID = {"mcv": mcv, "collision": collision, "markov": markov, "compression": compression,
       "t_tuple": t_tuple, "lrs": lrs}
PREDICTORS = {"multimcw": multimcw, "lag": lag, "multimmc": multimmc, "lz78y": lz78y}


def min_entropy_per_bit(data, predictor_bits: int = 30000) -> dict:
    """{estimador: h, ..., 'min': mínimo} — bits de min-entropy por bit."""
    b = _bits(data)
    res = {k: float(f(b)) for k, f in IID.items()}
    bp = b[:predictor_bits]
    res.update({k: float(f(bp)) for k, f in PREDICTORS.items()})
    res["min"] = min(res.values())
    return res
