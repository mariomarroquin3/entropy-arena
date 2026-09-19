"""Prueba de extremo a extremo en regtest con Bitcoin Core (sin Sparrow).

3 firmantes independientes (cada uno con su propia wallet de Core que solo contiene SU
tprv) + un coordinador watch-only. Fondea, crea un PSBT, lo firma por separado con 2 de
3, comprueba que 1 firma NO basta, transmite y confirma.

Uso: python experiments/regtest_e2e.py --bin-dir <carpeta con bitcoind y bitcoin-cli>
Todo ocurre en un directorio temporal y en una red regtest local (sin internet).
"""
import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from entropy_arena.methods.computational.secrets_csprng import SecretsMethod
from entropy_arena.wallet.signer import create_signer, account_path
from entropy_arena.wallet.seed_generator import mnemonic_to_seed
from entropy_arena.wallet.key_derivation import master_key_from_seed, derive_path
from entropy_arena.wallet.xkeys import serialize_priv
from entropy_arena.wallet.descriptor import (checksum, multisig_descriptor,
                                             parse_multisig_descriptor, derive_address)

RPC = ["-regtest", "-rpcport=18543", "-rpcuser=arena", "-rpcpassword=arena"]


class Node:
    def __init__(self, bin_dir: Path, datadir: Path):
        self.bin, self.datadir = Path(bin_dir), datadir
        exe = ".exe" if sys.platform == "win32" else ""
        self.bitcoind, self.cli = self.bin / f"bitcoind{exe}", self.bin / f"bitcoin-cli{exe}"
        self.proc = None

    def start(self):
        self.proc = subprocess.Popen(
            [str(self.bitcoind), "-regtest", f"-datadir={self.datadir}", "-server=1", "-listen=0",
             "-connect=0", "-dnsseed=0", "-fallbackfee=0.0002", "-rpcport=18543",
             "-rpcuser=arena", "-rpcpassword=arena"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                self.call("getblockchaininfo")
                return
            except RuntimeError:
                time.sleep(1)
        raise RuntimeError("bitcoind no arrancó")

    def call(self, *args, wallet=None):
        cmd = [str(self.cli), *RPC, f"-datadir={self.datadir}"]
        if wallet:
            cmd.append(f"-rpcwallet={wallet}")
        cmd += [str(a) for a in args]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"{' '.join(map(str, args[:2]))}: {r.stderr.strip() or r.stdout.strip()}")
        out = r.stdout.strip()
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            return out

    def stop(self):
        try:
            self.call("stop")
        except RuntimeError:
            pass
        if self.proc:
            self.proc.wait(timeout=60)


def step(msg):
    print(f"\n[{msg}]")


def check(cond, msg):
    print(("  OK   " if cond else "  FALLO ") + msg)
    if not cond:
        raise SystemExit(f"prueba fallida: {msg}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin-dir", required=True)
    a = ap.parse_args()
    tmp = tempfile.TemporaryDirectory()
    node = Node(a.bin_dir, Path(tmp.name))
    node.start()
    try:
        run(node)
    finally:
        node.stop()
        tmp.cleanup()


def with_cs(desc: str) -> str:
    return f"{desc}#{checksum(desc)}"


def run(node: Node):
    info = node.call("getblockchaininfo")
    step("Nodo")
    check(info["chain"] == "regtest", f"nodo en {info['chain']} (bloques={info['blocks']})")

    # --- 1. Tres firmantes independientes (mnemónico + tprv solo en su propia wallet)
    step("Firmantes")
    signers = []
    for name in ("ana", "beto", "carla"):
        mnemonic, pub = create_signer(SecretsMethod(), name, network="regtest")
        acct = derive_path(master_key_from_seed(mnemonic_to_seed(mnemonic)), account_path("regtest"))
        signers.append({"name": name, "pub": pub, "tprv": serialize_priv(acct, "testnet")})
        print(f"  {name}: fp={pub['master_fingerprint']}  {pub['xpub'][:16]}...")
    check(len({s["pub"]["master_fingerprint"] for s in signers}) == 3, "3 firmantes con claves distintas")

    public = [{"fingerprint": s["pub"]["master_fingerprint"], "path": s["pub"]["path"],
               "xpub": s["pub"]["xpub"]} for s in signers]

    def desc_for(branch, secret_idx=None):
        parts = []
        for i, s in enumerate(signers):
            key = s["tprv"] if i == secret_idx else s["pub"]["xpub"]
            parts.append(f"[{s['pub']['master_fingerprint']}/{s['pub']['path'].removeprefix('m/')}]{key}/{branch}/*")
        return with_cs(f"wsh(sortedmulti(2,{','.join(parts)}))")

    # --- 2. Wallets: una por firmante (con SU tprv) y una coordinadora watch-only
    step("Wallets en Core")
    def make_wallet(name, watch_only, secret_idx=None):
        node.call("-named", "createwallet", f"wallet_name={name}", "descriptors=true", "blank=true",
                  f"disable_private_keys={'true' if watch_only else 'false'}")
        reqs = [{"desc": desc_for(b, secret_idx), "timestamp": "now", "active": True,
                 "internal": b == 1, "range": [0, 20]} for b in (0, 1)]
        res = node.call("importdescriptors", json.dumps(reqs), wallet=name)
        check(all(r["success"] for r in res), f"wallet '{name}' importada")

    make_wallet("coord", watch_only=True)
    for i, s in enumerate(signers):
        make_wallet(f"sign_{s['name']}", watch_only=False, secret_idx=i)
    node.call("-named", "createwallet", "wallet_name=miner", "descriptors=true")

    # --- 3. La dirección de Core coincide con la derivada por nuestro código
    step("Watch-only: dirección propia vs Core")
    recv = with_cs(desc_for(0).split("#")[0])
    mine = derive_address(parse_multisig_descriptor(multisig_descriptor(2, public, "0")), 0, 0, "regtest")
    core_addr = node.call("getnewaddress", wallet="coord")
    check(core_addr == mine["address"], f"{core_addr}")

    # --- 4. Fondeo
    step("Fondeo")
    miner_addr = node.call("getnewaddress", wallet="miner")
    node.call("generatetoaddress", 101, miner_addr)
    txid_fund = node.call("sendtoaddress", core_addr, 1.0, wallet="miner")
    node.call("generatetoaddress", 1, miner_addr)
    bal = node.call("getbalances", wallet="coord")["mine"]["trusted"]
    check(abs(bal - 1.0) < 1e-8, f"coord ve {bal} BTC en la wallet 2-de-3 (tx {txid_fund[:12]}...)")

    # --- 5. PSBT sin firmas
    step("PSBT")
    dest = node.call("getnewaddress", wallet="miner")
    funded = node.call("walletcreatefundedpsbt", "[]", json.dumps([{dest: 0.25}]), 0,
                       json.dumps({"includeWatching": True}), "true", wallet="coord")
    psbt = funded["psbt"]
    check(True, f"PSBT creado por el coordinador (fee {funded['fee']} BTC)")
    decoded0 = node.call("decodepsbt", psbt)
    check(all("partial_signatures" not in i for i in decoded0["inputs"]), "el PSBT inicial no trae firmas")

    # --- 6. Firmas separadas (cada wallet solo conoce su propia clave)
    step("Firmas independientes")
    signed = {}
    for name in ("ana", "beto", "carla"):
        r = node.call("walletprocesspsbt", psbt, "true", wallet=f"sign_{name}")
        n = len(node.call("decodepsbt", r["psbt"])["inputs"][0].get("partial_signatures", {}))
        signed[name] = r["psbt"]
        print(f"  {name}: {n} firma(s) en su copia; completo={r['complete']}")
        check(n == 1 and not r["complete"], f"{name} aporta exactamente 1 firma")

    # --- 7. Una firma NO basta
    step("Umbral")
    one = node.call("finalizepsbt", signed["ana"])
    check(not one["complete"], "con 1 sola firma el PSBT NO se puede finalizar")
    two = node.call("combinepsbt", json.dumps([signed["ana"], signed["beto"]]))
    fin = node.call("finalizepsbt", two)
    check(fin["complete"], "con 2 firmas (ana+beto) el PSBT se finaliza")
    other = node.call("combinepsbt", json.dumps([signed["beto"], signed["carla"]]))
    check(node.call("finalizepsbt", other)["complete"], "cualquier par sirve (beto+carla)")

    # --- 8. Transmisión y confirmación
    step("Transmisión")
    txid = node.call("sendrawtransaction", fin["hex"])
    node.call("generatetoaddress", 1, miner_addr)
    tx = node.call("gettransaction", txid, wallet="coord")
    check(tx["confirmations"] >= 1, f"tx {txid[:16]}... confirmada")
    raw = node.call("gettransaction", txid, "true", "true", wallet="coord")["decoded"]
    wit = raw["vin"][0]["txinwitness"]
    check(len(wit) == 4 and wit[0] == "", "witness = [vacío, firma, firma, script]  (2 firmas + witnessScript)")
    expected_script = mine["witness_script"]
    check(wit[-1] == expected_script, "el witnessScript gastado es exactamente el que derivó nuestro código")

    print("\nTODO OK: 2-de-3 funcional en regtest (umbral aplicado, firmas independientes, watch-only coincide).")


if __name__ == "__main__":
    main()
