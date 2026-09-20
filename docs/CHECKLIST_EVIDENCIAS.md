# Checklist de evidencias para la entrega (Assignment 2)

Cada evidencia indica **qué capturar, en qué momento del flujo** (secciones de
[GUIA_ASSIGNMENT.md](GUIA_ASSIGNMENT.md)) y **qué NO debe verse**. Marca cada casilla al
tenerla. Guarda todo en una carpeta `entrega/` (está en el `.gitignore`: no se sube al repo).

> **Regla de seguridad del enunciado:** nunca entregar mnemónicos, `tprv`/`xprv`, contraseñas
> de wallet, respaldos con material secreto ni secuencias de dados de una wallet real.
> Antes de entregar ejecuta `python experiments/check_submission.py entrega` y revisa **a mano**
> todas las imágenes (el script no puede leerlas).

Estructura sugerida:

    entrega/
      01_descriptor/      configuración pública de la wallet
      02_custodia/        tabla o diagrama de firmantes
      03_funcional/       capturas de creación, fondeo, firmas, transmisión
      04_reconstruccion/  prueba watch-only
      05_nodo/            capturas del nodo regtest
      06_reflexion.md     máx. 400 palabras

---

## Criterio 1 — Multisig funcionando en Sparrow (25 pts)

| # | Evidencia | Cuándo (guía) | Debe verse | NO debe verse |
|---|---|---|---|---|
| [ ] 1.1 | Sparrow conectado al nodo regtest | §6.1 | Mensaje `Connected to … /Satoshi:31.1.0/` y la etiqueta **Regtest** | Contraseña RPC (aunque sea de prueba, tápala) |
| [ ] 1.2 | Wallet creada: política **2 de 3**, script **P2WSH** | §6.2 | Pestaña *Settings* con los 3 keystores y la política | Casillas de mnemónico abiertas |
| [ ] 1.3 | Saldo tras fondear | §7 | Pestaña *UTXOs* o *Transactions* con la confirmación | — |
| [ ] 1.4 | **Una firma no basta:** `1 of 2` con *Broadcast* bloqueado | §8 paso 3 | Panel *Signatures* con 1 casilla llena y 1 vacía | Mnemónico o contraseña |
| [ ] 1.5 | **Dos firmas independientes:** `2 of 2` | §8 paso 4 | Panel *Signatures* con las 2 casillas llenas, hecho por dos firmantes en equipos distintos | — |
| [ ] 1.6 | Transacción transmitida y **confirmada** | §8 pasos 5-6 | Txid y confirmaciones ≥ 1 en Sparrow | — |
| [ ] 1.7 | La misma transacción vista en Core | §8 paso 6 | Salida de `gettransaction` o `getblockcount` tras minar | — |

Tip: si puedes, graba un screen recording corto de las capturas 1.4 → 1.6 (el enunciado lo acepta).

## Criterio 2 — Descriptor y claves públicas (20 pts)

| # | Evidencia | Cuándo | Debe verse |
|---|---|---|---|
| [ ] 2.1 | **Descriptor público** exportado de Sparrow (o `wallet_descriptor.txt`) | §5 | `wsh(sortedmulti(2,[fingerprint/48'/1'/0'/2']tpub…/<0;1>/*,…))#checksum` |
| [ ] 2.2 | Tabla de firmantes: fingerprint, ruta, tpub, cómo se generó cada clave | §5 | Solo datos públicos (los JSON `signer_*.json`) |
| [ ] 2.3 | Explicación escrita de cada parte del descriptor | reflexión | Fingerprint = primeros 4 bytes de HASH160 de la clave maestra; ruta `m/48'/1'/0'/2'` = BIP48, testnet, cuenta 0, P2WSH; `tpub` = clave extendida pública; `sortedmulti(2,…)` = 2 de 3 con claves ordenadas; `<0;1>` = ramas de recepción y cambio |

**Regla:** el descriptor **no** debe contener `tprv` ni el mnemónico.

## Criterio 3 — Independencia de firmantes y custodia (15 pts)

- [ ] 3.1 **Tabla de custodia** (una fila por firmante):

  | Firmante | Persona | Equipo/lugar donde vive la clave | Fuente de entropía | Qué pasa si se pierde |
  |---|---|---|---|---|
  | 1 | (nombre) | Papel en (lugar A) | `secrets` | Los otros 2 gastan; migrar a wallet nueva |
  | 2 | (nombre) | Papel en (lugar B) | `secrets` | Igual |
  | 3 | (nombre) | Papel en (lugar C) | `xor-dice` | Igual |

- [ ] 3.2 **Diagrama de flujo** (ya está hecho): [DIAGRAMA_FLUJO.md](DIAGRAMA_FLUJO.md).
- [ ] 3.3 Evidencia de que las claves están en equipos distintos (p. ej. capturas de cada firmante
  en su Sparrow, cada una mostrando **solo su** keystore como *Software* y los otros como *xPub*).
- [ ] 3.4 El 4.º integrante (coordinador/auditor) confirma por escrito que verificó el descriptor
  y el proceso de reconstrucción **de forma independiente** (pista para el track Standard).
- [ ] 3.5 Modelo de pérdida: qué ocurre si se pierde 1 clave, 2 claves, o se compromete 1 (ver
  [GUIA §10](GUIA_ASSIGNMENT.md)).

## Criterio 4 — Nodo / entorno de pruebas (10 pts)

| # | Evidencia | Cuándo | Comando |
|---|---|---|---|
| [ ] 4.1 | El nodo está en regtest | §3 | `& $cli @a getblockchaininfo` → `"chain": "regtest"` y `"blocks"` |
| [ ] 4.2 | Bloques minados para fondear | §3 y §7 | `-generate 101` y luego `-generate 1` |
| [ ] 4.3 | Explicación breve del papel del nodo | reflexión | Valida bloques y transacciones; Sparrow lo usa (vía Cormorant) para ver saldos y transmitir; en regtest los bloques se minan a mano y las monedas no valen nada |

## Criterio 5 — Reconstrucción watch-only (15 pts)

| # | Evidencia | Cuándo | Comando / captura |
|---|---|---|---|
| [ ] 5.1 | Salida de la verificación desde solo el descriptor | §6.3 | `python experiments/verify_watch_only.py data/public/wallet_descriptor.txt --network regtest --count 5 --expect <DIRECCIÓN_SPARROW>` → `RESULTADO: COINCIDE` |
| [ ] 5.2 | Dirección de recepción en Sparrow | §6.2 | Pestaña *Receive* con la dirección 0 |
| [ ] 5.3 | Confirmación con Core (independiente de mi código) | §6.3 | `& $cli @a deriveaddresses "<descriptor receive con #checksum>" "[0,4]"` |
| [ ] 5.4 | Wallet watch-only en Sparrow importada solo con el descriptor | §6.3 | *File → Import Wallet → Output Descriptor* y su primera dirección coincide |

## Criterio 6 — Razonamiento de seguridad (10 pts)

`entrega/06_reflexion.md` — **máximo 400 palabras** (cuéntalas: `(Get-Content entrega\06_reflexion.md -Raw).Split() | Measure-Object`).
Esquema (una o dos frases por punto):

1. **Umbral elegido:** por qué 2-de-3 (tolera la pérdida de 1 clave sin perder los fondos; un
   solo compromiso no basta para gastar).
2. **Cómo se generaron las claves:** `secrets` (CSPRNG) elegido tras comparar 16+ métodos en la
   arena; los que solo "parecen" aleatorios (Mersenne Twister, π, RANDU) se rechazan por
   entropía real < 128 bits. Opcional: XOR con dados como defensa en profundidad.
3. **Qué se aprendió de los descriptores:** un descriptor concentra política, claves públicas,
   fingerprints y rutas; con él se reconstruye la wallet sin poder gastar.
4. **Escenario de ataque/fallo:** *entropía débil*. Si una clave viene de un PRNG predecible, un
   atacante la recupera (MT19937 se rompe con 2496 bytes: `python experiments/run_attacks.py`)
   aunque los tests estadísticos "pasen". En 2-de-3 necesitaría además otra clave: el multisig
   limita el daño pero no lo elimina.
5. **Principal trade-off:** más seguridad y tolerancia a pérdida frente a mayor complejidad
   operativa (coordinación entre personas, respaldos separados, PSBT pasando entre equipos).
6. **Lección aprendida:** p. ej. que "parecer aleatorio" no equivale a "tener entropía".

## Criterio 7 — Creatividad y exploración (5 pts)

- [ ] 7.1 Resumen de la arena de entropía (tabla de veredictos: `python experiments/run_arena.py`
  → `data/results/leaderboard.json`, `ranking.png`).
- [ ] 7.2 Demostración de ataques (`python experiments/run_attacks.py`).
- [ ] 7.3 (Opcional) Experimento de dados: **solo con una sesión distinta de la de la wallet
  real** (regla de seguridad). Si lo reclamas, incluye el diagnóstico de
  `run_manual_session.py`, pero **no** la secuencia de tiradas.
- [ ] 7.4 (Opcional) Otros extras: flujo con PSBT en archivo entre equipos (air-gapped), prueba
  automática `regtest_e2e.py`.

## Bono 3-de-5 (+5, opcional)

Requiere que los 4 estudiantes controlen un firmante y que la 5.ª clave sea de
recuperación/offline con un rol justificado. Las herramientas aceptan otro umbral
(`build_descriptor.py --threshold 3`), pero `regtest_e2e.py` solo prueba 2-de-3.

---

## Verificación final antes de entregar

```powershell
python experiments/check_submission.py entrega
```
- Debe decir `0 problema(s)`.
- Abre **todas** las imágenes y confirma que no hay palabras de mnemónico, `tprv`, contraseñas
  ni la clave RPC visibles.
- Confirma que las claves de la entrega **no** son las de las pruebas de práctica (esas ya se
  vieron en capturas y chats).
- Prepara las tres respuestas de defensa ([GUIA §10](GUIA_ASSIGNMENT.md)):
  1. ¿Qué condición exacta protege los fondos?
  2. ¿Qué información pública basta para reconstruir la wallet sin poder gastar?
  3. ¿Qué pasa si se pierden o comprometen uno o más firmantes?

**Fecha límite: 27 de septiembre de 2026, 16:00. Presentación en línea.**
