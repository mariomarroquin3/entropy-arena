# Guía completa: Entropy Arena + wallet multisig 2-de-3 (Assignment 2)

> **Diagramas del flujo (quién hace qué y en qué PC): [DIAGRAMA_FLUJO.md](DIAGRAMA_FLUJO.md)**

Todo lo que se construyó y, sobre todo, **cómo reproducir la prueba de principio a fin**:
comandos en orden, listos para copiar en PowerShell (Windows). Red usada: **regtest**
(red local privada; las monedas no tienen valor).

> **Regla de oro del enunciado:** en la entrega solo va información **pública**
> (descriptor, tpub, fingerprints, capturas). Nunca mnemónicos, `tprv`, ni secuencias de
> dados de una wallet real. Ninguna captura debe mostrar palabras.

---

## 0. Qué hace cada pieza

| Pieza | Para qué sirve |
|---|---|
| **Python (este repo)** | Genera las claves (con una fuente de entropía validada), exporta los datos públicos, arma el descriptor y verifica direcciones. |
| **Bitcoin Core** | El nodo (regtest). Valida y mina bloques. |
| **Sparrow** | La interfaz de la wallet: ver saldo, crear la transacción (PSBT), firmar y transmitir. |

Flujo: **Python crea las claves → Python arma el descriptor → Sparrow crea la wallet y la
compara con Python → se fondea desde Core → se gasta con 2 firmas separadas.**

### Qué se construyó en el proyecto
- **Arena de entropía:** compara métodos (secrets, os.urandom, Mersenne Twister, RANDU, PCG64,
  uuid4, mapa logístico, Lorenz, Regla 30, dígitos de π, browniano, jitter de CPU, dados,
  monedas, baraja, von Neumann, XOR de fuentes) con tests NIST SP 800-22 (proporción de
  aprobados + uniformidad de p-values) y estimadores de min-entropy SP 800-90B.
- **Dos ejes por método:** *calidad estadística* (cuánto parece aleatorio) y *bits reales*
  (entropía genuina). Veredictos: `APTO`, `IMITA AZAR`, `FALLA TESTS`.
- **Ataques de demostración:** se rompe el Mersenne Twister con 2496 bytes, RANDU con 8,
  el offset de π y semillas de reloj. Contra `secrets` no hay ataque equivalente.
- **Tests de estructura:** rango binario, espectral, entropía aproximada y complejidad
  lineal por bit-de-palabra (única que distingue al Mersenne Twister de un CSPRNG).
- **Wallet:** BIP39/BIP32/BIP48, xpub/tpub y fingerprints, descriptor
  `wsh(sortedmulti(2,…))`, derivación pública (watch-only), P2WSH. Validada contra vectores
  oficiales y contra Bitcoin Core (regtest, PSBT con firmas separadas).

### ¿Con qué modelo de la arena se generan las palabras?
Por defecto con **`secrets`** (`--method secrets`), el CSPRNG del sistema. En la arena,
`secrets` y `os.urandom` son los únicos que combinan calidad 100 y ≥128 bits reales (`APTO`)
sin depender de una semilla pequeña. Mersenne Twister, π, RANDU, Regla 30, etc. también
"pasan" los tests (calidad ~100) pero salen `IMITA AZAR`: su entropía real es la de una
semilla de 0-64 bits, y se rompen. Opciones para el experimento de creatividad:

| `--method` | Fuente | Cuándo |
|---|---|---|
| `secrets` (**recomendado**) | CSPRNG del SO | Uso normal |
| `urandom` | `os.urandom` | Equivalente |
| `xor-dice` / `xor-coins` | `secrets` XOR tus tiradas físicas | Bonus de dados: si el dado es malo, la seguridad sigue siendo la del CSPRNG |
| `dice` / `coins` | Solo tiradas físicas | Exige ≥128 bits *medidos*; si no, se rechaza |
| `pcg` | numpy PCG64 (semilla de 128 bits) | Solo para comparar |

Los métodos débiles (Mersenne Twister, RANDU…) **se rechazan** automáticamente (< 128 bits).

---

## 1. Requisitos e instalación (cada participante)

### 1.1 Python y dependencias
```powershell
git clone <URL-del-repositorio> entropy-arena     # o copia la carpeta del proyecto
cd entropy-arena
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
```
`pytest` debe terminar en verde (todos los tests pasan). Si PowerShell bloquea el script de
activación: `Set-ExecutionPolicy -Scope Process Bypass` y repite la activación.

### 1.2 Bitcoin Core (solo el coordinador; el nodo)
Descarga `bitcoin-core-31.1` (Windows, zip) de bitcoincore.org y **verifica el hash** contra
`SHA256SUMS` del mismo sitio:
```powershell
Get-FileHash .\bitcoin-31.1-win64.zip -Algorithm SHA256
```
Compara con la línea de `SHA256SUMS` correspondiente. Descomprime en una carpeta permanente:
```powershell
Expand-Archive .\bitcoin-31.1-win64.zip -DestinationPath $HOME\
Rename-Item $HOME\bitcoin-31.1 $HOME\bitcoin-core
```
(Debe quedar `C:\Users\<tú>\bitcoin-core\bin\bitcoind.exe`.)

### 1.3 Sparrow (todos)
Descárgalo de sparrowwallet.com y verifica su firma/hash como indica el sitio.

---

## 2. Prueba de humo sin Sparrow (recomendada antes de todo)

Comprueba que tu entorno hace un ciclo completo (3 firmantes, PSBT, 2 firmas, umbral,
transmisión) en un nodo temporal que se borra al terminar:
```powershell
python experiments/regtest_e2e.py --bin-dir "$HOME\bitcoin-core\bin"
```
Debe terminar con: `TODO OK: 2-de-3 funcional en regtest`.

---

## 3. Nodo regtest persistente (coordinador)

En PowerShell, **una terminal dedicada** (déjala abierta mientras dure la prueba).

> Importante: en PowerShell los argumentos con `=` y punto (`-fallbackfee=0.0002`) deben ir
> **entre comillas**, o darán `unexpected token '.0002'`. El directorio de datos debe existir.

```powershell
New-Item -ItemType Directory -Force "$HOME\regtest-data"
& "$HOME\bitcoin-core\bin\bitcoind.exe" "-regtest" "-server=1" "-txindex=1" "-fallbackfee=0.0002" "-rpcuser=arena" "-rpcpassword=arena" "-datadir=$HOME\regtest-data"
```

En **otra terminal** define atajos (repítelos en cada terminal nueva):
```powershell
$cli = "$HOME\bitcoin-core\bin\bitcoin-cli.exe"
$a = "-regtest","-rpcuser=arena","-rpcpassword=arena","-datadir=$HOME\regtest-data"
```

Comprueba y mina monedas (así el nodo sale del modo "initial block download", que hace que
Sparrow espere/se queje):
```powershell
& $cli @a getblockchaininfo
& $cli @a createwallet miner
& $cli @a "-rpcwallet=miner" -generate 101
& $cli @a getblockchaininfo
```
- **Evidencia del nodo:** `getblockchaininfo` debe mostrar `"chain": "regtest"` y `"blocks": 101`.

Puerto RPC de regtest por defecto: **18443**.

---

## 4. Cada firmante genera SU clave (en SU equipo)

Cada persona, en su propio ordenador, con su propia copia del repo (`.venv` activado):
```powershell
python experiments/signer_export.py ana --method secrets --network regtest
```
(sustituye `ana` por tu nombre; cada firmante usa el suyo: `beto`, `carla`).

Qué imprime:
- `fingerprint maestro`, `ruta de cuenta` (`m/48'/1'/0'/2'`) y `tpub`.
- **24 palabras (mnemónico SECRETO):** anótalas **a mano en papel**. No las guardes en
  archivos, no las envíes por chat, no las incluyas en capturas.
- Crea `data\public\signer_<nombre>.json` con solo datos públicos.

Cada firmante envía **únicamente ese JSON** al coordinador (por chat/USB está bien).

> **Dónde queda el archivo:** la carpeta `data\public\` **se crea sola** la primera vez que
> ejecutas `signer_export.py`, dentro de la carpeta del proyecto **de ese equipo**
> (p. ej. `C:\Users\<tú>\Downloads\entropy-arena\data\public\signer_ana.json`). La ruta exacta
> se imprime al final, en la línea `Archivo PÚBLICO (compártelo con el coordinador): …`.
> Para comprobarlo: `Get-ChildItem data\public`.
>
> **No está en GitHub:** `data\public\` está en el `.gitignore`, así que un clon nuevo del
> repositorio no la trae. Los JSON **no se suben al repo**: cada firmante debe pasárselo al
> coordinador manualmente. El coordinador los copia a su propia carpeta `data\public\` antes
> del paso 5.
>
> Ejecuta el comando **desde la raíz del proyecto** (`cd entropy-arena`, con el `.venv`
> activado); si lo ejecutas desde otra carpeta, los archivos se crean igualmente dentro del
> proyecto, no donde estés parado.

Bonus de dados (opcional; primero registra tus tiradas reales):
```powershell
python experiments/run_manual_session.py dice 100
python experiments/signer_export.py ana --method xor-dice --network regtest
```
El diagnóstico que imprime `run_manual_session.py` dice si las tiradas bastan (≥128 bits medidos).

---

## 5. Coordinador: construir y auditar el descriptor

Con los tres JSON en una carpeta (p. ej. `data\public\`):
```powershell
python experiments/build_descriptor.py data/public/signer_ana.json data/public/signer_beto.json data/public/signer_carla.json
```
Imprime la política, el descriptor **multipath** `wsh(sortedmulti(2,[fp/48'/1'/0'/2']tpub…/<0;1>/*,…))#checksum`,
las variantes de recepción/cambio y las **primeras direcciones**. Apunta la dirección `0:`
(`bcrt1q…`): la compararás con Sparrow. Guarda todo en `data\public\wallet_descriptor.txt`
(esto es la **"public wallet configuration"** de la entrega).

Rechaza firmantes duplicados y mezcla de redes.

---

## 6. Sparrow

### 6.1 Conexión
1. Arranca Sparrow en modo **regtest** (si tu menú no permite elegir red, ejecuta Sparrow con
   el flag `-n regtest`; confirma con `--help`).
2. *Preferences → Server → Bitcoin Core*: URL `127.0.0.1`, puerto `18443`, usuario `arena`,
   clave `arena` → **Test Connection**.
3. Éxito si muestra algo como: `Connected to Cormorant … / Server Banner: /Satoshi:31.1.0/`
   (Cormorant es el servidor Electrum interno de Sparrow sobre tu Core). **Captura de evidencia.**

### 6.2 Una wallet por firmante (cada firmante en SU Sparrow)
Independencia: **nadie debe tener los mnemónicos de otro.** Cada firmante crea, en su equipo:

1. *File → New Wallet* → nombre (p. ej. `multisig_ana`).
2. *Policy Type:* **Multi Signature**. *Script Type:* **Native Segwit (P2WSH)**. *Cosigners:* **3**, *Threshold:* **2**.
3. Pestaña **Keystores** (uno por cosigner):
   - **El propio:** *New or Imported Software Wallet* → *Use 24 Words* → escribe **tus** 24
     palabras (una por casilla, sin unir palabras; si dice "Invalid checksum", revisa que no
     haya dos palabras pegadas ni una faltante) → *Create Keystore* → *Import Keystore*.
   - **Los otros dos:** **xPub / Watch Only Wallet** (mismo panel de keystore, junto a
     "New or Imported Software Wallet"): pega su `tpub`, su fingerprint y la ruta
     `m/48'/1'/0'/2'` (los datos están en sus JSON) → *Import*.
4. *Apply* y ponle contraseña a la wallet si la pide.
5. **Comprobación cruzada (evidencia):** en la pestaña *Receive*, la dirección debe ser
   **idéntica** a la `0:` que imprimió `build_descriptor.py`. Los tpub y fingerprints que
   muestra Sparrow deben coincidir con los JSON.

Wallet del **coordinador** (crea el PSBT): sus tres keystores pueden ser *xPub / Watch Only*
(no necesita ninguna clave privada).

> Si una sola máquina tiene los 3 mnemónicos (por ejemplo para practicar), el flujo funciona
> pero **no sirve como evidencia de independencia de firmantes**.

### 6.3 Verificación watch-only desde el descriptor (reconstruction proof)
En una máquina sin ninguna clave, solo con el descriptor público:
```powershell
python experiments/verify_watch_only.py data/public/wallet_descriptor.txt --network regtest --count 5 --expect <DIRECCION_RECEPCION_0_DE_SPARROW>
```
Debe terminar con `RESULTADO: COINCIDE`. (Sin `--network regtest` las direcciones se derivan
con prefijo de testnet y no coincidirán.) Refuerzo desde Core:
```powershell
& $cli @a deriveaddresses "<descriptor de recepción con #checksum>" "[0,4]"
```
También puedes importar el descriptor en una wallet nueva de Sparrow (*File → Import Wallet →
Output Descriptor*) y comprobar que la dirección 0 coincide.

---

## 7. Fondear la wallet

Copia la dirección de *Receive* (`bcrt1q…`) y envía 1 BTC desde `miner`, luego mina 1 bloque:
```powershell
& $cli @a "-rpcwallet=miner" sendtoaddress <DIRECCION_SPARROW> 1
& $cli @a "-rpcwallet=miner" -generate 1
```
En Sparrow (*Transactions*/*UTXOs*) debe aparecer 1 BTC con 1 confirmación. **Captura.**

---

## 8. Gastar con firmas separadas

Dirección de destino (una de `miner`):
```powershell
& $cli @a "-rpcwallet=miner" getnewaddress
```

1. **Coordinador**, pestaña **Send**: *Pay to* = esa dirección, *Label* = cualquier nota
   (p. ej. `prueba regtest`; solo es un texto tuyo), *Amount* = `0.25`. Si no ves el campo
   Label, agranda la ventana o haz scroll dentro de la pestaña. → **Create Transaction** →
   **Finalize Transaction for Signing**.
2. Botón **Save Transaction** → guarda el **PSBT** en un archivo. Sin firmas, está en `0 of 2`.
3. **Firmante A** (en SU equipo, con SU wallet): *File → Open Transaction → From File*, abre el
   PSBT → **Sign** → *Save Transaction* con otro nombre. Ahora `1 of 2`; **Broadcast sigue
   bloqueado.** **Captura: es la prueba de que una firma no basta.**
4. **Firmante B**: abre el PSBT que guardó A → **Sign** → ahora `2 of 2`.
5. Con `2 of 2`, aparece **Broadcast** → púlsalo.
6. Confirma con un bloque y verifica en Core:
```powershell
& $cli @a "-rpcwallet=miner" -generate 1
& $cli @a getmempoolinfo
```
En Sparrow la transacción pasa a confirmada. **Captura de la tx difundida/confirmada.**

Los archivos PSBT se pasan entre firmantes por USB/chat: contienen firmas, no claves privadas.

---

## 9. Qué entregar (solo información pública)
1. **Configuración pública:** `data\public\wallet_descriptor.txt` (descriptor con tpub,
   fingerprints, rutas y política 2-de-3).
2. **Mapa de arquitectura/custodia:** tabla o diagrama:

   | Firmante | Quién | Dónde se guarda la clave | Fuente de entropía | Qué pasa si se pierde |
   |---|---|---|---|---|
   | 1 | Ana | Papel, caja fuerte A | `secrets` | Beto y Carla gastan |
   | 2 | Beto | Papel, otra ubicación | `secrets` | Ana y Carla gastan |
   | 3 | Carla | Papel/otro medio | `xor-dice` | Ana y Beto gastan |

3. **Prueba funcional:** capturas de nodo regtest, wallet creada, fondeo, `1 of 2`, `2 of 2`,
   transacción difundida y confirmada.
4. **Prueba de reconstrucción:** salida de `verify_watch_only.py` (`COINCIDE`) y la dirección
   de Sparrow.
5. **Reflexión (≤400 palabras):** umbral elegido y por qué, cómo se generaron las claves
   (aquí sirve la arena: por qué `secrets` y no Mersenne Twister), qué se aprendió de los
   descriptores, y el principal *trade-off*.

**Nunca incluyas:** mnemónicos, `tprv`, capturas con palabras visibles, secuencias de dados
de una wallet real.

---

## 10. Preguntas de defensa (respuestas)
1. **¿Qué condición protege los fondos?** Un script P2WSH `2 <pk1> <pk2> <pk3> 3 OP_CHECKMULTISIG`:
   se necesitan 2 firmas válidas de las 3 claves.
2. **¿Qué información pública basta para reconstruir la wallet sin poder gastar?** El descriptor con
   los `tpub`, fingerprints, rutas de derivación y la política. Permite derivar todas las
   direcciones, pero no contiene ninguna clave privada.
3. **¿Qué pasa si se pierden o comprometen firmantes?** Perder 1: los otros 2 gastan; conviene
   migrar a una wallet nueva. Perder 2: fondos bloqueados. Comprometer 1: no basta para gastar;
   comprometer 2: se pierden los fondos.

**Escenario de ataque realista (para la reflexión):** *entropía débil.* Si una clave se genera
con un PRNG predecible (Mersenne Twister, semilla de reloj), un atacante la recupera aunque los
tests estadísticos "pasen" (`python experiments/run_attacks.py` lo demuestra: MT19937 se rompe
con 2496 bytes). En un 2-de-3 con una clave débil, el atacante necesita además otra clave: el
multisig acota el daño, pero deja de ser 2-de-3 efectivo. La contramedida es usar una fuente `APTO`
y rechazar automáticamente fuentes con < 128 bits reales (lo que hace el generador).

---

## 11. Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `Command line contains unexpected token '.0002'` | PowerShell divide `-fallbackfee=0.0002`. Pon **cada argumento entre comillas** (ver §3). |
| `Specified data directory … does not exist` | Créalo: `New-Item -ItemType Directory -Force "$HOME\regtest-data"`. |
| Sparrow dice "sincronizando" o no conecta | El nodo está en `initialblockdownload`. Mina: `& $cli @a "-rpcwallet=miner" -generate 101`. |
| `Invalid checksum` al importar palabras | Alguna palabra está mal, falta una o hay dos pegadas (p. ej. `scrapnotice`). Escribe una palabra por casilla. |
| No aparece el campo *Label* | Ventana pequeña: maximiza o haz scroll. El label es opcional (una nota). |
| No encuentro dónde poner el tpub | En el panel de keystore usa **xPub / Watch Only Wallet** (no *Software Wallet*). |
| Las direcciones de Python y Sparrow no coinciden | Revisa la red (`--network regtest`), la ruta `m/48'/1'/0'/2'`, que el orden de claves da igual (sortedmulti) y que copiaste bien los tpub. |
| `verify_watch_only.py` dice `NO coincide` | Falta `--network regtest`, o comparas una dirección de cambio en vez de recepción. |
| `ModuleNotFoundError: mnemonic` | Faltó `pip install -r requirements.txt` con el `.venv` activado. |
| El firmante `dice` se rechaza | Tus tiradas miden < 128 bits: registra más (`run_manual_session.py dice 100`) o usa `xor-dice`. |

---

## 12. Limitaciones (honestidad técnica)
- La aritmética de curva elíptica y BIP32 es Python puro y educativa (sin protección contra
  canales laterales): **solo regtest/testnet, nunca fondos reales**.
- Los estimadores SP 800-90B están adaptados y trabajan con 100 kbit (el estándar pide 1 Mbit).
- Los pasos de la interfaz de Sparrow pueden variar entre versiones: si un menú no coincide,
  la lógica (keystore propio con 24 palabras + los otros por xPub) es la misma.
- El descriptor de una sola dirección (`wsh(sortedmulti(2,pk…))`) existe en el código para
  compatibilidad, pero el flujo de esta guía usa descriptores con xpub, origen y rango.
