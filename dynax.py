from flask import Flask, request
import hashlib
import time
import ecdsa

app = Flask(__name__)

# =========================
# WALLET
# =========================
class Wallet:

    def __init__(self, private_key=None):

        if private_key is None:
            self.sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
        else:
            self.sk = ecdsa.SigningKey.from_string(
                bytes.fromhex(private_key),
                curve=ecdsa.SECP256k1
            )

        self.vk = self.sk.get_verifying_key()

    def address(self):
        pub = self.vk.to_string().hex()
        return hashlib.sha256(pub.encode()).hexdigest()

    def sign(self, msg):
        h = hashlib.sha256(msg.encode()).digest()
        return self.sk.sign(h).hex()

    @staticmethod
    def verify(pubkey_hex, signature_hex, msg):
        try:
            vk = ecdsa.VerifyingKey.from_string(
                bytes.fromhex(pubkey_hex),
                curve=ecdsa.SECP256k1
            )
            h = hashlib.sha256(msg.encode()).digest()
            return vk.verify(bytes.fromhex(signature_hex), h)
        except:
            return False


# =========================
# CHAIN CORE
# =========================
chain = []
mempool = []

# UTXO (simple)
utxos = {}

# Genesis
def create_genesis():
    global chain, utxos

    genesis_tx = {
        "from": "GENESIS",
        "to": "SYSTEM",
        "amount": 1000000
    }

    block = {
        "index": 0,
        "prev": "0",
        "txs": [genesis_tx],
        "hash": "genesis"
    }

    chain.append(block)


create_genesis()


# =========================
# BALANCE (UTXO simple)
# =========================
def balance(addr):
    bal = 0

    for block in chain:
        for tx in block["txs"]:
            if tx["from"] == addr:
                bal -= tx["amount"]
            if tx["to"] == addr:
                bal += tx["amount"]

    return bal


# =========================
# SEND
# =========================
@app.route("/send", methods=["POST"])
def send():

    data = request.get_json()

    from_addr = data["from"]
    to_addr = data["to"]
    amount = data["amount"]
    pub = data["public_key"]
    sig = data["signature"]

    msg = f"{from_addr}{to_addr}{amount}"

    if not Wallet.verify(pub, sig, msg):
        return {"error": "bad signature"}

    if balance(from_addr) < amount:
        return {"error": "insufficient balance"}

    tx = {
        "from": from_addr,
        "to": to_addr,
        "amount": amount,
        "public_key": pub,
        "signature": sig
    }

    mempool.append(tx)

    return {"success": True, "tx": tx}


# =========================
# MINE
# =========================
@app.route("/mine/<addr>")
def mine(addr):

    reward = {
        "from": "NETWORK",
        "to": addr,
        "amount": 50
    }

    block = {
        "index": len(chain),
        "prev": chain[-1]["hash"],
        "txs": mempool + [reward],
        "hash": hashlib.sha256(str(time.time()).encode()).hexdigest()
    }

    chain.append(block)
    mempool.clear()

    return {"success": True, "block": block}


# =========================
# BALANCE API
# =========================
@app.route("/balance/<addr>")
def get_bal(addr):
    return {"address": addr, "balance": balance(addr)}


# =========================
# CHAIN
# =========================
@app.route("/chain")
def get_chain():
    return chain


# =========================
# RUN
# =========================
app.run(host="0.0.0.0", port=6002)
