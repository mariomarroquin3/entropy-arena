# Comandos para levantar todo (en orden)

Detalle y explicaciones: [GUIA_ASSIGNMENT.md](GUIA_ASSIGNMENT.md). Todo en **PowerShell**.

## 1. Nodo (Terminal 1, déjala abierta y no escribas en ella)
```powershell
& "$HOME\bitcoin-core\bin\bitcoind.exe" "-regtest" "-server=1" "-txindex=1" "-fallbackfee=0.0002" "-rpcuser=arena" "-rpcpassword=arena" "-datadir=$HOME\regtest-data"
```

## 2. Comandos al nodo (Terminal 2)
```powershell
$cli = "$HOME\bitcoin-core\bin\bitcoin-cli.exe"
$a = "-regtest","-rpcuser=arena","-rpcpassword=arena","-datadir=$HOME\regtest-data"
& $cli @a loadwallet miner
& $cli @a "-rpcwallet=miner" getbalance
```
Si el saldo es 0: `& $cli @a "-rpcwallet=miner" -generate 101`

## 3. Claves nuevas (cada firmante, en SU equipo, desde la carpeta del proyecto)
```powershell
cd C:\Users\mario\Downloads\entropy-arena
.\.venv\Scripts\Activate.ps1
python experiments/signer_export.py NOMBRE --method secrets --network regtest
```
Anota las 24 palabras **en papel**. Se envía solo `data\public\signer_NOMBRE.json`.

## 4. Coordinador: descriptor y comprobación
```powershell
python experiments/build_descriptor.py data/public/signer_a.json data/public/signer_b.json data/public/signer_c.json
python experiments/verify_watch_only.py data/public/wallet_descriptor.txt --network regtest --expect <DIRECCION_0_DE_SPARROW>
```
Debe decir `RESULTADO: COINCIDE`.

## 5. Sparrow
1. Abrir en modo **regtest**. *Preferences → Server → Bitcoin Core*: `127.0.0.1`, puerto `18443`, usuario `arena`, clave `arena` → *Test Connection*.
2. Wallet 2-de-3 P2WSH: tu keystore por *24 palabras*, los otros por **xPub / Watch Only** (tpub + fingerprint + `m/48'/1'/0'/2'`).
3. Comprobar que la dirección 0 de *Receive* coincide con la de Python.

## 6. Fondear
```powershell
& $cli @a "-rpcwallet=miner" sendtoaddress <DIRECCION_SPARROW> 1
& $cli @a "-rpcwallet=miner" -generate 1
```

## 7. Gastar con 2 firmas
Destino: `& $cli @a "-rpcwallet=miner" getnewaddress`

1. **Coordinador:** *Send* → dirección, monto, label → *Create Transaction* → *Finalize Transaction for Signing* → **Save Transaction**.
2. **Firmante A:** *File → Open Transaction → From File* → **Sign** → Save (`1 of 2`, Broadcast bloqueado: captura).
3. **Firmante B:** abre el archivo → **Sign** → Save (`2 of 2`).
4. **Coordinador:** *Load Transaction* con el archivo final → **Broadcast**.
5. Confirmar: `& $cli @a "-rpcwallet=miner" -generate 1`

## 8. Al terminar
```powershell
& $cli @a stop
python experiments/check_submission.py entrega
```
