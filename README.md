# Entropy Arena

Compara empíricamente 16+ métodos de generación de aleatoriedad (computacionales,
matemáticos, físicos y manuales) y usa el resultado para generar, con evidencia y no por
costumbre, las claves de una bóveda multisig 2-de-3.

**Idea central:** parecer aleatorio ≠ aportar entropía. Un generador determinista, por
caótico que sea, solo hereda la incertidumbre de su semilla. Cada método recibe dos
medidas independientes:

| Eje | Qué mide | Cómo |
|---|---|---|
| **Calidad** (0-100) | Cuánto *parece* aleatorio | NIST SP 800-22: proporción de muestras que pasan + uniformidad de p-values; min-entropy MCV |
| **Bits reales** | Entropía genuina por muestra | Semilla / entrada física / estimadores SP 800-90B |

Veredicto: `APTO` (calidad ≥ 85 **y** ≥ 128 bits reales), `IMITA AZAR` (pasa los tests
pero con < 128 bits, p. ej. Mersenne Twister, π, Lorenz, RANDU) o `FALLA TESTS`.
**Solo un método `APTO` debe usarse para generar una seed real.**

---

## Cómo generar una seed segura (léase primero)

    python experiments/signer_export.py MI_NOMBRE --method secrets --network regtest

Eso basta para la mayoría de los casos. El resto de esta sección explica **por qué**, para
que la elección no sea un acto de fe.

### Qué fuente usar

| Prioridad | `--method` | Por qué | Cuándo evitarla |
|---|---|---|---|
| **1ª opción** | `secrets` | CSPRNG del sistema operativo (`os.urandom` por debajo). `APTO`: calidad ~90-100, 256 bits reales por seed de 32 bytes. Sin ataque conocido en esta arena ni fuera de ella. Es la fuente recomendada por la propia documentación de Python para material criptográfico. | — |
| Equivalente | `urandom` | Mismo generador del SO que usa `secrets` por debajo; en la práctica, igual de válido. | — |
| Defensa en profundidad | `xor-dice`, `xor-coins` | XOR de `secrets` con tus tiradas físicas. La entropía final es **al menos** la de `secrets` (256 bits), así que un dado cargado no puede debilitar la seed; solo puede sumar. | Si no quieres depender de tiradas registradas correctamente (ver limitaciones). |
| Solo si se audita mucho | `dice`, `coins` (sin XOR) | Entropía física pura, pero **medida**, no supuesta: se exige ≥ 128 bits reales tras aplicar una cota de min-entropy al 99 % de confianza. El generador la rechaza si no llega. | Como única fuente en un despliegue real: un humano no lanza de forma perfectamente uniforme y hacen falta muchas tiradas (≥ 50 dados, ≥ 256 monedas) para llegar al umbral. |
| **Nunca para una seed real** | `pcg`, o cualquier `IMITA AZAR`/`FALLA TESTS` de la arena | Ver la sección siguiente. | Siempre. |

### Por qué no los "top performers" por calidad, sino por veredicto

Si ordenas la arena solo por la columna de calidad, varios generadores deterministas
(Mersenne Twister, RANDU, π, el movimiento browniano) empatan con `secrets` en 99-100.
**Eso es precisamente el hallazgo del proyecto, no una recomendación.** Todos esos
métodos son `IMITA AZAR`: superan los siete tests NIST y aun así se rompen en fracciones
de segundo observando su salida (`python experiments/run_attacks.py`):

| Ataque | Datos observados | Tiempo | Resultado |
|---|---|---|---|
| Reconstruir el estado del Mersenne Twister | 2 496 bytes | ~0.02 s | Predice **todas** las salidas futuras |
| Recuperar el estado de RANDU | 8 bytes | ~0.3 s | Predice todas las salidas futuras |
| Encontrar el offset de los bits de π | 32 bytes | ~0.1 s | Reconstruye la fuente completa |
| Fuerza bruta sobre `random.seed(time.time())` | ventana de 1 día | ~0.1 s | Recupera la semilla exacta |

El mismo ataque contra `secrets` **falla siempre**: no hay estado que reconstruir. Por eso
el criterio de selección de este proyecto no es "¿qué generador saca más nota?", sino
"¿qué generador es `APTO`, es decir, pasa los tests **y** tiene ≥ 128 bits de entropía real
que no dependan de una semilla corta?". `generate_seed_from()` aplica esa regla en código:
rechaza con un `ValueError` cualquier fuente por debajo de 128 bits, salvo que se fuerce
explícitamente con `allow_weak=True` (nunca recomendado).

### El caso ambiguo: numpy PCG64

`Pcg64Method` sale `APTO` en la arena (calidad ~100, 128 bits reales, la de su semilla).
Cumple el umbral y por eso el código lo acepta. Aun así, **no lo recomendamos para
custodiar fondos**: PCG64 es un PRNG estadístico, no un CSPRNG. Su especificación es
pública y su estado interno se puede reconstruir a partir de un número suficiente de
salidas (esta arena no implementa ese ataque, pero es un resultado conocido en la
literatura). El umbral de 128 bits mide *entropía de la semilla*, no *resistencia a la
criptoanálisis*; para eso hace falta además que el algoritmo esté diseñado para ocultar su
estado, que es justo lo que sí garantiza `secrets`.

### El caso físico: jitter de CPU

`cpu_timing_jitter_sha256` también sale `APTO` (temporización de CPU condicionada con
SHA-256, ~12 400 bits reales estimados). Es un buen ejemplo de fuente física genuina, pero
sus bits reales dependen de estimadores SP 800-90B adaptados y no certificados que
trabajan con una muestra menor a la que pide el estándar (ver *Limitaciones*). Úsalo como
fuente secundaria o de investigación, no como la única entrada de una wallet real.

**Resumen para quien solo quiere generar una seed y seguir:** usa `secrets` (o `urandom`).
Si quieres combinar con dados o monedas por variedad de origen, usa `xor-dice`/`xor-coins`,
nunca `dice`/`coins` en solitario salvo que hayas validado tú mismo el diagnóstico de
`run_manual_session.py`. No uses ningún generador `IMITA AZAR`, aunque su calidad estadística
sea perfecta.

---

## Instalación

    pip install -r requirements.txt
    pytest            # ~53 tests, incluye vectores oficiales BIP32/BIP39/BIP173/NIST

## Uso

    # Arena (100 muestras x 100 kbit por método; ~10-15 min por Regla 30 y jitter)
    python experiments/run_arena.py

    # Registrar tiradas manuales (imprime un diagnóstico al terminar: bits medidos, no supuestos)
    python experiments/run_manual_session.py dice 100     # >= 50 recomendado
    python experiments/run_manual_session.py coins 256

    # Un firmante genera SU clave y exporta solo datos públicos (fingerprint, ruta, tpub)
    python experiments/signer_export.py NOMBRE --method secrets --network regtest

    # Coordinador: combina los JSON públicos de los firmantes en un descriptor de wallet
    python experiments/build_descriptor.py data/public/signer_*.json

    # Verifica una wallet en modo watch-only solo con el descriptor público
    python experiments/verify_watch_only.py data/public/wallet_descriptor.txt --network regtest --expect <dirección>

    # Bóveda multisig 2-de-3 P2WSH de un solo uso (BIP39/32/48, testnet por defecto)
    python experiments/run_multisig.py secrets urandom pcg [--show-secrets] [--mainnet] [--allow-weak]

El script imprime también el descriptor `wsh(sortedmulti(2,…))#checksum` (BIP380).
Verificado contra Bitcoin Core 31.1 (`regtest`/`testnet4`): `getdescriptorinfo` acepta el
checksum y `deriveaddresses` devuelve exactamente la misma dirección.

**Portal de resultados:** [`site/index.html`](site/index.html) (autónomo, doble clic para
abrir; se regenera con `python experiments/build_site.py`). **Diagrama del flujo:**
[docs/DIAGRAMA_FLUJO.md](docs/DIAGRAMA_FLUJO.md). **Checklist de evidencias:**
[docs/CHECKLIST_EVIDENCIAS.md](docs/CHECKLIST_EVIDENCIAS.md). **Guía paso a paso con
Sparrow** (firmantes independientes, xpub, watch-only): [docs/GUIA_ASSIGNMENT.md](docs/GUIA_ASSIGNMENT.md).

Fuentes que aceptan `run_multisig.py`/`signer_export.py`: `secrets`, `urandom`, `pcg`,
`dice`, `coins`, `xor-dice`, `xor-coins`. Se **rechaza** cualquier fuente con < 128 bits
reales (salvo `--allow-weak`, que no debe usarse fuera de pruebas) y claves duplicadas
entre firmantes. Los mnemónicos solo se muestran con `--show-secrets`, o se piden por
`getpass` (sin eco ni historial) con `--ask-mnemonic`.

## Métodos evaluados

- **Computacionales:** `secrets`, `os.urandom`, `uuid4` (122 bits/UUID), Mersenne Twister
  (con y sin seed), RANDU, numpy PCG64.
- **Matemáticos** (deterministas; entropía = semilla de 64 bits): movimiento browniano,
  mapa logístico, atractor de Lorenz, Regla 30 (columna central), dígitos binarios de π.
- **Físicos:** jitter de temporización de CPU (crudo y condicionado con SHA-256).
- **Manuales:** dados, monedas, baraja (condicionados con SHA-256); la entropía declarada
  es la *medida* (min-entropy con cota al 99 %), no la teórica.
- **Híbridos:** von Neumann sobre monedas; `XorCombiner` (entropía ≥ máximo de los
  componentes, nunca la suma; es el mecanismo detrás de `xor-dice`/`xor-coins`).

## Tests estadísticos

Monobit, runs, frecuencia por bloques, sumas acumuladas (ambos sentidos), racha más larga
de unos, chi² de bytes (NIST SP 800-22, criterio de proporción + uniformidad, no promedio
de p-values). Estimadores de min-entropy SP 800-90B §6.3 (los 10 para binario): MCV,
Collision, Markov, Compression, t-Tuple, LRS, MultiMCW, Lag, MultiMMC y LZ78Y; el resultado
es su **mínimo**, nunca su promedio. Desviaciones respecto al estándar documentadas en el
docstring de `analysis/sp800_90b.py` (tuplas ≤ 63 bits, predictores sobre los primeros
30 kbit, marcador de subpredictor simplificado).

## Ataques y tests de estructura

    python experiments/run_attacks.py           # rompe MT19937, RANDU, offset de pi y semillas de reloj
    python experiments/run_structure_tests.py   # rango binario, espectral, ApEn, complejidad lineal
    python experiments/regtest_e2e.py --bin-dir <bitcoin/bin>  # multisig 2-de-3 completo en regtest (Core)

- **Ataques** (`entropy_arena/attacks`): recuperación del estado de Mersenne Twister con
  2496 bytes (predice todo lo siguiente), RANDU con 8 bytes, búsqueda del offset en los
  bits de π, fuerza bruta de `random.seed(time)`. Contra `secrets` el mismo ataque falla
  siempre (control negativo).
- **Complejidad lineal por bit-de-palabra** (`strided_linear_complexity`): el Mersenne
  Twister pasa toda la batería NIST y los tests de estructura sobre la secuencia
  concatenada, pero el flujo de un mismo bit de palabras de 32 bits tiene complejidad
  lineal 19 937 ≪ n/2 y se detecta. Es el único test genérico de la batería que lo
  distingue de un CSPRNG.

## Resultados reproducibles

La carpeta [`results/`](results) contiene la salida de la última ejecución completa:
`leaderboard.json`, `ranking.png`, `metric_matrix.png` (arena, 100 muestras x 100 kbit),
`estimators.txt` (`experiments/validate_estimators.py`), `structure_tests.txt`,
`attacks.txt`, `regtest_e2e.txt` (2-de-3 con Bitcoin Core) y `pytest.txt`. El documento
[`docs/methodology.tex`](docs/methodology.tex) (PDF: `docs/methodology.pdf`) explica las
métricas, la física de cada fuente, la lógica booleana del gasto multisig y estos
resultados con demostraciones formales. Umbral del veredicto: un solo test estadístico
fallido por azar no descalifica (calidad ≥ 85); dos o más sí.

## Limitaciones conocidas

Léelas antes de confiar en un veredicto `APTO` para una wallet con fondos reales:

- **La aritmética secp256k1 es Python puro, educativa:** sin protección contra canales
  laterales (timing, caché). **No usar con fondos reales**, solo en `regtest`/`testnet`.
- **El veredicto mide entropía, no resistencia criptográfica.** PCG64 es `APTO` por el
  tamaño de su semilla, pero su estado se puede reconstruir a partir de la salida; no es
  un CSPRNG. Ver *"El caso ambiguo"* arriba.
- **Los estimadores SP 800-90B están adaptados, no certificados**, y trabajan con 100 kbit
  en vez del 1 Mbit que pide el estándar: con poca muestra las cotas son conservadoras
  (una fuente ideal sale con ~0.5-0.9 bits/bit), así que los bits reales del jitter de CPU
  tienden a subestimarse, no a sobreestimarse.
- **Una sesión manual (dados/monedas) es una única muestra fija:** el test de uniformidad
  de p-values no aplica y las proporciones NIST no son fiables con una sola tirada; la
  arena lo avisa explícitamente (`samples_repeated`/nota en el leaderboard).
- **Un humano no lanza ni baraja de forma perfectamente uniforme;** los bits de la baraja
  son el máximo teórico (226), no una medición, a diferencia de dados y monedas.
- **Con 100 muestras por test, una fuente ideal puede fallar un test por azar (~1-2 %).**
  El umbral de calidad (≥ 85, un fallo tolerado) existe justamente por esto: no lo
  interpretes como "el generador es perfecto en todos los tests siempre".
- **Ningún resultado de esta arena es una certificación externa.** Es una herramienta de
  comparación y demostración educativa, verificada contra vectores oficiales (BIP32/39/173,
  NIST) y contra Bitcoin Core, pero no ha pasado una auditoría de terceros.

## Estructura

    entropy_arena/methods/       fuentes de entropía
    entropy_arena/analysis/      tests NIST, SP 800-90B, entropía, estructura
    entropy_arena/attacks/       ataques de demostración (MT19937, RANDU, π, reloj)
    entropy_arena/arena/         runner, scoring, leaderboard
    entropy_arena/manual_input/  captura y diagnóstico de tiradas
    entropy_arena/wallet/        BIP39, BIP32, secp256k1, bech32, descriptores, multisig P2WSH
    experiments/                 scripts ejecutables
    site/                        portal de resultados (build_site.py lo genera desde results/)
    docs/                        metodología, guía de assignment, diagramas, checklist
    tests/                       pytest
