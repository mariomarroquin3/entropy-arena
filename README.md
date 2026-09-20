# Entropy Arena

Compara empíricamente métodos de generación de aleatoriedad (computacionales,
matemáticos, físicos y manuales) y los usa como fuentes de una bóveda multisig 2-de-3.

**Idea central:** parecer aleatorio ≠ aportar entropía. Cada método recibe dos
medidas independientes:

| Eje | Qué mide | Cómo |
|---|---|---|
| **Calidad** (0-100) | Cuánto *parece* aleatorio | NIST SP 800-22: proporción de muestras que pasan + uniformidad de p-values; min-entropy MCV |
| **Bits reales** | Entropía genuina por muestra | Semilla / entrada física / estimadores SP 800-90B |

Veredicto: `APTO` (calidad ≥ 85 y ≥ 128 bits reales), `IMITA AZAR` (pasa los tests
pero con < 128 bits, p. ej. Mersenne Twister, π, Lorenz, RANDU) o `FALLA TESTS`.

## Instalación

    pip install -r requirements.txt
    pytest            # ~46 tests, incluye vectores oficiales BIP32/BIP39/BIP173/NIST

## Uso

    # Arena (100 muestras x 100 kbit por método; ~10-15 min por Regla 30 y jitter)
    python experiments/run_arena.py

    # Registrar tiradas manuales (imprime un diagnóstico al terminar)
    python experiments/run_manual_session.py dice 100     # >= 50 recomendado
    python experiments/run_manual_session.py coins 256

    # Bóveda multisig 2-de-3 P2WSH (BIP39/32/48, testnet por defecto)
    python experiments/run_multisig.py secrets dice coins
    python experiments/run_multisig.py secrets urandom pcg [--show-secrets] [--mainnet] [--allow-weak]

El script imprime también el descriptor `wsh(sortedmulti(2,…))#checksum` (BIP380). Verificado contra Bitcoin Core 31.1 (`-testnet4`): `getdescriptorinfo` acepta el checksum y `deriveaddresses` devuelve exactamente la misma dirección `tb1q…`.

**Checklist de evidencias:** [docs/CHECKLIST_EVIDENCIAS.md](docs/CHECKLIST_EVIDENCIAS.md). **Diagrama del flujo:** [docs/DIAGRAMA_FLUJO.md](docs/DIAGRAMA_FLUJO.md). **Assignment multisig con Sparrow (firmantes independientes, xpub, watch-only):** ver [docs/GUIA_ASSIGNMENT.md](docs/GUIA_ASSIGNMENT.md) (`signer_export.py`, `build_descriptor.py`, `verify_watch_only.py`).

Fuentes para el multisig: `secrets`, `urandom`, `pcg`, `dice`, `coins`. Se **rechaza**
cualquier fuente con < 128 bits reales (salvo `--allow-weak`) y claves duplicadas.
Los mnemónicos solo se muestran con `--show-secrets`.

## Métodos

- **Computacionales:** `secrets`, `os.urandom`, `uuid4` (122 bits/UUID), Mersenne Twister
  (con y sin seed), RANDU, numpy PCG64.
- **Matemáticos** (deterministas; entropía = semilla de 64 bits): movimiento browniano,
  mapa logístico, atractor de Lorenz, Regla 30 (columna central), dígitos binarios de π.
- **Físicos:** jitter de temporización de CPU (crudo y condicionado con SHA-256).
- **Manuales:** dados, monedas, baraja (condicionados con SHA-256); la entropía declarada
  es la *medida* (min-entropy con cota al 99%), no la teórica.
- **Híbridos:** von Neumann sobre monedas; `XorCombiner` (entropía ≥ máximo de los
  componentes, nunca la suma).

## Tests estadísticos

Monobit, runs, frecuencia por bloques, sumas acumuladas (ambos sentidos), racha más
larga de unos, chi² de bytes. Estimadores de min-entropy SP 800-90B §6.3 (los 10 para binario): MCV, Collision,
Markov, Compression, t-Tuple, LRS, MultiMCW, Lag, MultiMMC y LZ78Y; el resultado es su
mínimo. Desviaciones respecto al estándar en el docstring de `analysis/sp800_90b.py`
(tuplas ≤ 63 bits, predictores sobre los primeros 30 kbit, marcador simplificado).

## Ataques y tests de estructura

    python experiments/run_attacks.py           # rompe MT19937, RANDU, offset de pi y semillas de reloj
    python experiments/run_structure_tests.py   # rango binario, espectral, ApEn, complejidad lineal
    python experiments/regtest_e2e.py --bin-dir <bitcoin/bin>  # multisig 2-de-3 completo en regtest (Core)

- **Ataques** (`entropy_arena/attacks`): recuperación del estado de Mersenne Twister con 2496 bytes
  (predice todo lo siguiente), RANDU con 8 bytes, búsqueda del offset en los bits de pi, fuerza bruta
  de `random.seed(time)`. Contra `secrets` el mismo ataque falla (control).
- **Complejidad lineal por bit-de-palabra** (`strided_linear_complexity`): el MT pasa toda la batería
  NIST y los tests de estructura sobre la secuencia concatenada, pero el flujo de un mismo bit de
  palabras de 32 bits tiene complejidad lineal 19937 << n/2 y se detecta. Es el único test genérico
  de la batería que lo distingue de un CSPRNG.

## Resultados reproducibles

La carpeta [`results/`](results) contiene la salida de la última ejecución completa:
`leaderboard.json`, `ranking.png`, `metric_matrix.png` (arena, 100 muestras x 100 kbit),
`estimators.txt` (`experiments/validate_estimators.py`), `structure_tests.txt`, `attacks.txt`,
`regtest_e2e.txt` (2-de-3 con Bitcoin Core) y `pytest.txt`. El documento
[`docs/methodology.tex`](docs/methodology.tex) (PDF: `docs/methodology.pdf`) explica las
métricas, la física de cada fuente y estos resultados. Umbral del veredicto: un solo test
fallido por azar no descalifica (Q >= 85); dos o más sí.

## Limitaciones conocidas

- La aritmética secp256k1 es Python puro, educativa: sin protección contra
  canales laterales. **No usar con fondos reales.**
- Los estimadores 90B están adaptados (no certificados) y trabajan con 100 kbit en vez
  de 1 Mbit: con poca muestra las cotas son conservadoras (una fuente ideal sale con
  ~0.5-0.9 bits/bit), así que los bits reales del jitter tienden a subestimarse.
- Una sesión manual es una única muestra fija: el test de uniformidad no aplica y las
  proporciones NIST no son fiables (la arena lo avisa).
- Un humano no baraja ni lanza de forma uniforme; los bits de la baraja son el máximo
  teórico (226), no una medición.
- Con 100 muestras por test, una fuente ideal puede fallar un test por azar (~1-2 %).

## Estructura

    entropy_arena/methods/    fuentes de entropía
    entropy_arena/analysis/   tests NIST, SP 800-90B, entropía
    entropy_arena/arena/      runner, scoring, leaderboard
    entropy_arena/manual_input/  captura y diagnóstico de tiradas
    entropy_arena/wallet/     BIP39, BIP32, secp256k1, bech32, multisig P2WSH
    experiments/              scripts ejecutables      tests/   pytest
