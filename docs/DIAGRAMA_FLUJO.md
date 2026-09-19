# Diagrama del flujo: de las claves a la transacción 2-de-3

Los diagramas usan [Mermaid](https://mermaid.js.org/): GitHub los dibuja automáticamente al
abrir este archivo. Las instrucciones con todos los comandos están en
[GUIA_ASSIGNMENT.md](GUIA_ASSIGNMENT.md).

## 1. Creación de la wallet (quién hace qué, y en qué computador)

Cada caja grande es **un computador distinto**. Lo único que viaja entre computadores son
archivos **públicos** (líneas punteadas). Los **secretos** (las 24 palabras) nunca salen de
su computador.

```mermaid
flowchart TB
    subgraph F["PC de CADA firmante (Ana, Beto, Carla) - tres equipos separados"]
        F1["PASO 1<br/>python experiments/signer_export.py NOMBRE<br/>--method secrets --network regtest"]
        F2["El generador usa el modelo secrets de la arena<br/>y crea 24 palabras BIP39 (256 bits)"]
        F3["SECRETO<br/>24 palabras anotadas en PAPEL<br/>nunca se envían ni se fotografían"]
        F4["PUBLICO<br/>data/public/signer_NOMBRE.json<br/>fingerprint + ruta + tpub"]
        F6["PASO 5 - Sparrow del firmante<br/>(tambien conectado al nodo regtest)<br/>Wallet 2-de-3 P2WSH<br/>Keystore propio = sus 24 palabras<br/>Los otros dos = xPub / Watch Only"]
        F1 --> F2
        F2 --> F3
        F2 --> F4
    end

    subgraph K["PC del COORDINADOR"]
        K1["PASO 2<br/>Copia los 3 JSON a data/public/"]
        K2["PASO 3<br/>python experiments/build_descriptor.py<br/>signer_ana.json signer_beto.json signer_carla.json"]
        K3["Descriptor publico<br/>wsh(sortedmulti(2, tpubA, tpubB, tpubC))<br/>+ direccion 0 calculada por Python"]
        K4["PASO 4<br/>python experiments/verify_watch_only.py<br/>descriptor --network regtest --expect DIRECCION"]
        K5["PASO 5 - Sparrow del coordinador<br/>(conectado a Bitcoin Core regtest, RPC 18443)<br/>Wallet 2-de-3 con los 3 keystores<br/>como xPub / Watch Only, sin claves privadas<br/>muestra la direccion 0 de Sparrow"]
        K6{"Las dos direcciones 0<br/>son IGUALES?"}
        K7["OK: Python y Sparrow<br/>calculan lo mismo"]
        K1 --> K2
        K2 --> K3
        K3 --> K4
        K3 -.->|"en paralelo"| K5
        K4 --> K6
        K5 --> K6
        K6 -->|"si"| K7
        K6 -->|"no"| K8["Revisar red regtest,<br/>ruta m/48h/1h/0h/2h y tpub"]
    end

    F4 -.->|"PASO 2: USB o chat<br/>SOLO el JSON, nunca las palabras"| K1
    K2 -.->|"descriptor + JSONs de los otros<br/>(informacion publica)"| F6
    K7 --> P6["PASO 6: fondear con sendtoaddress<br/>y minar 1 bloque (ver diagrama 2)"]
```

### Qué es secreto y qué es público

| Dato | ¿Secreto? | Dónde vive | ¿Va en la entrega? |
|---|---|---|---|
| 24 palabras (mnemónico) | **SÍ** | Papel del firmante y su Sparrow | **NO** |
| `tprv` / claves privadas | **SÍ** | Solo dentro del Sparrow del firmante | **NO** |
| `signer_NOMBRE.json` (fingerprint, ruta, `tpub`) | No | Se envía al coordinador | Sí |
| Descriptor `wsh(sortedmulti(2,…))` | No | Coordinador y firmantes | Sí |
| PSBT (transacción a medio firmar) | No | Pasa de firmante a firmante | Sí (capturas) |

## 2. Gastar con 2 de 3 firmas (firmas separadas)

Ningún computador tiene las tres claves: el PSBT viaja de un firmante al siguiente como
archivo. Con **una** sola firma, Sparrow bloquea el botón *Broadcast*.

```mermaid
sequenceDiagram
    autonumber
    participant K as Coordinador (Sparrow)
    participant A as Firmante A (su Sparrow)
    participant B as Firmante B (su Sparrow)
    participant N as Nodo Core regtest
    participant M as Wallet miner (Core)

    M->>N: sendtoaddress a la direccion 0 de la wallet
    M->>N: generate 1 (confirma el deposito)
    N-->>K: Sparrow ve 1 BTC confirmado
    K->>K: Send: destino, monto 0.25, Create Transaction
    K->>A: Archivo PSBT sin firmas (0 de 2)
    A->>A: Sign con SU clave, queda 1 de 2
    Note over A: Broadcast BLOQUEADO<br/>Captura: una firma no basta
    A->>B: Archivo PSBT con 1 firma
    B->>B: Sign con SU clave, queda 2 de 2
    Note over B: Broadcast HABILITADO
    B->>N: Broadcast de la transaccion
    M->>N: generate 1 (confirma la transaccion)
    N-->>K: Transaccion confirmada
```

## 3. Cómo se generaron las palabras (la parte de la arena)

```mermaid
flowchart LR
    S1["Arena de entropia<br/>16+ metodos comparados"] --> S2["Tests NIST SP 800-22<br/>+ estimadores SP 800-90B<br/>+ ataques de demostracion"]
    S2 --> S3{"Veredicto"}
    S3 -->|"APTO: secrets, os.urandom"| S4["Se usan para las claves<br/>(--method secrets)"]
    S3 -->|"IMITA AZAR: Mersenne Twister,<br/>pi, RANDU, Regla 30..."| S5["Se rechazan: menos de 128<br/>bits reales y se pueden predecir"]
    S4 --> S6["24 palabras BIP39<br/>256 bits de entropia"]
    D["Dados / monedas fisicos<br/>(opcional: --method xor-dice)"] -.->|"XOR con secrets<br/>defensa en profundidad"| S6
```

## Resumen en una línea

**Cada firmante crea su clave en su PC → envía solo el JSON público al coordinador →
el coordinador arma el descriptor → Python y Sparrow calculan la misma dirección → se fondea
desde Core → el PSBT pasa por dos firmantes → se transmite.**
