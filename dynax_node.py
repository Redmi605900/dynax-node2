import time
import json
import hashlib
import requests
import os
import hmac
import threading
from flask import Flask, request, jsonify, make_response

CHAIN_FILE = os.path.expanduser("~/dynax_chain.json")
DIFFICULTY = 4
BLOCK_REWARD = 50
SECRET_KEY = "DYNAX_SECRET_v1"
PORT = int(os.environ.get("PORT", 6001))

# ─────────────────────────────────────────────
class Block:
# ─────────────────────────────────────────────
    def __init__(self, index, prev_hash, txs, nonce=0):
        self.index = index
        self.timestamp = int(time.time())
        self.prev_hash = prev_hash
        self.transactions = txs
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        data = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "prev_hash": self.prev_hash,
            "transactions": self.transactions,
            "nonce": self.nonce
        }, sort_keys=True)
        return hashlib.sha3_256(data.encode()).hexdigest()

    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "prev_hash": self.prev_hash,
            "transactions": self.transactions,
            "nonce": self.nonce,
            "hash": self.hash,
            "tx_count": len(self.transactions)
        }

# ─────────────────────────────────────────────
class DYNAXNode:
# ─────────────────────────────────────────────
    def __init__(self):
        self.chain = []
        self.mempool = []
        self.peers = set()   # ใช้ set เพื่อกัน duplicate
        self.lock = threading.Lock()
        self.load_chain()

    # ── Persistence ──────────────────────────
    def save_chain(self):
        with open(CHAIN_FILE, "w") as f:
            json.dump([b.to_dict() for b in self.chain], f, indent=2)

    def load_chain(self):
        if not os.path.exists(CHAIN_FILE):
            genesis_txs = [
                {"from": "GENESIS", "to": "DX5293ada2aa014167fa15942c4318b6235fe7d1", "amount": 300000},
                {"from": "GENESIS", "to": "DXf2a9fc9e0b20602d66af8ecae2032f0e56c20f", "amount": 7000},
                {"from": "GENESIS", "to": "DX8a6e18a35d23368fa553f87552693d91f58ce6", "amount": 445},
                {"from": "GENESIS", "to": "DX9ac31f667d87ec3a5940ac409d9a54de8b0507", "amount": 137}
            ]
            genesis = Block(0, "0" * 64, genesis_txs)
            self.chain.append(genesis)
            self.save_chain()
            return

        with open(CHAIN_FILE) as f:
            data = json.load(f)

        for item in data:
            b = Block(item["index"], item["prev_hash"], item["transactions"], item["nonce"])
            b.timestamp = item["timestamp"]
            b.hash = item["hash"]   # ← แก้ indent ที่นี่
            self.chain.append(b)

    # ── Chain helpers ─────────────────────────
    def last_block(self):
        return self.chain[-1]

    def verify_chain(self, chain=None):
        chain = chain or self.chain
        for i in range(1, len(chain)):
            curr = chain[i]
            prev = chain[i - 1]
            # รองรับทั้ง Block object และ dict
            curr_prev = curr.prev_hash if hasattr(curr, "prev_hash") else curr["prev_hash"]
            prev_hash  = prev.hash     if hasattr(prev,  "hash")     else prev["hash"]
            curr_hash  = curr.hash     if hasattr(curr,  "hash")     else curr["hash"]
            curr_calc  = curr.calculate_hash() if hasattr(curr, "calculate_hash") else None

            if curr_prev != prev_hash:
                return False
            if curr_calc and curr_hash != curr_calc:
                return False
        return True

    # ── P2P: Broadcast ───────────────────────
    def broadcast_block(self, block):
        def _send(peer):
            try:
                requests.post(peer + "/receive_block", json=block.to_dict(), timeout=2)
            except Exception:
                pass

        for peer in list(self.peers):
            threading.Thread(target=_send, args=(peer,), daemon=True).start()

    # ── P2P: Fetch chain from peer ───────────
    def fetch_chain_from_peer(self, peer):
        try:
            r = requests.get(peer + "/chain", timeout=3)
            return r.json()   # list of dicts
        except Exception:
            return None

    # ── P2P: Sync (longest chain wins) ───────
    def sync_from_peers(self):
        best_raw = None
        best_len = len(self.chain)

        for peer in list(self.peers):
            raw = self.fetch_chain_from_peer(peer)
            if raw and isinstance(raw, list) and len(raw) > best_len:
                # ตรวจสอบ chain ก่อน accept
                if self._validate_raw_chain(raw):
                    best_raw = raw
                    best_len = len(raw)

        if best_raw:
            with self.lock:
                self.chain = self._raw_to_blocks(best_raw)
                self.save_chain()
            return True
        return False

    def _validate_raw_chain(self, raw):
        for i in range(1, len(raw)):
            if raw[i]["prev_hash"] != raw[i - 1]["hash"]:
                return False
            b = Block(raw[i]["index"], raw[i]["prev_hash"], raw[i]["transactions"], raw[i]["nonce"])
            b.timestamp = raw[i]["timestamp"]
            if b.calculate_hash() != raw[i]["hash"]:
                return False
        return True

    def _raw_to_blocks(self, raw):
        blocks = []
        for item in raw:
            b = Block(item["index"], item["prev_hash"], item["transactions"], item["nonce"])
            b.timestamp = item["timestamp"]
            b.hash = item["hash"]
            blocks.append(b)
        return blocks

    # ── Peers management ─────────────────────
    def add_peer(self, peer_url):
        peer_url = peer_url.rstrip("/")
        self.peers.add(peer_url)

    # ── Balance ──────────────────────────────
    def get_balance(self, address):
        balance = 0
        for block in self.chain:
            for tx in block.transactions:
                if tx.get("from") == address:
                    balance -= tx["amount"]
                if tx.get("to") == address:
                    balance += tx["amount"]
        return balance

    # ── Transaction ──────────────────────────
    def add_transaction(self, tx):
        for field in ["from", "to", "amount", "signature"]:
            if field not in tx:
                return {"success": False, "error": f"missing {field}"}
        if tx["amount"] <= 0:
            return {"success": False, "error": "invalid amount"}
        balance = self.get_balance(tx["from"])
        if balance < tx["amount"] and tx["from"] != "GENESIS":
            return {"success": False, "error": f"insufficient balance: {balance}"}

        tx_canonical = {"from": tx["from"], "to": tx["to"], "amount": tx["amount"]}
        message = json.dumps(tx_canonical, sort_keys=True).encode()
        expected_sig = hmac.new(SECRET_KEY.encode(), message, hashlib.sha3_256).hexdigest()
        if expected_sig != tx["signature"]:
            return {"success": False, "error": "invalid signature"}

        tx["txid"] = hashlib.sha3_256(json.dumps(tx_canonical, sort_keys=True).encode()).hexdigest()
        tx["timestamp"] = int(time.time())
        self.mempool.append(tx)
        return {"success": True, "txid": tx["txid"]}

    # ── Mining ───────────────────────────────
    def mine(self, miner_address):
        reward_tx = {
            "from": "NETWORK",
            "to": miner_address,
            "amount": BLOCK_REWARD,
            "txid": hashlib.sha3_256(f"reward_{len(self.chain)}".encode()).hexdigest()
        }
        txs = [reward_tx] + self.mempool[:]
        block = Block(len(self.chain), self.last_block().hash, txs)

        print(f"⛏️  Mining block #{block.index}...")
        while not block.hash.startswith("0" * DIFFICULTY):
            block.nonce += 1
            block.hash = block.calculate_hash()

        with self.lock:
            self.chain.append(block)
            self.mempool = []
            self.save_chain()

        self.broadcast_block(block)
        print(f"✅ Block #{block.index} mined: {block.hash[:20]}...")
        return block

    # ── TX lookup ────────────────────────────
    def get_tx(self, txid):
        for block in self.chain:
            for tx in block.transactions:
                if tx.get("txid") == txid:
                    return {"tx": tx, "block": block.index}
        return None

    # ── Info ─────────────────────────────────
    def info(self):
        return {
            "name": "DYNAX",
            "symbol": "DYX",
            "version": "2.0.0",
            "blocks": len(self.chain),
            "mempool": len(self.mempool),
            "peers": len(self.peers),
            "difficulty": DIFFICULTY,
            "reward": BLOCK_REWARD,
            "max_supply": 11000000,
            "valid": self.verify_chain()
        }


# ═════════════════════════════════════════════
# Flask API
# ═════════════════════════════════════════════
app = Flask(__name__)
node = DYNAXNode()

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    return response

@app.route("/", defaults={"path": ""}, methods=["OPTIONS"])
@app.route("/<path:path>", methods=["OPTIONS"])
def options_handler(path):
    return make_response("", 204)

# ── Info ──────────────────────────────────────
@app.route("/")
def index():
    return jsonify(node.info())

# ── Chain ─────────────────────────────────────
@app.route("/chain")
def get_chain():
    return jsonify([b.to_dict() for b in node.chain])

@app.route("/block/<int:index>")
def get_block(index):
    if index < len(node.chain):
        return jsonify(node.chain[index].to_dict())
    return jsonify({"error": "block not found"}), 404

# ── Receive block from peer ───────────────────
@app.route("/receive_block", methods=["POST"])
def receive_block():
    data = request.get_json()

    b = Block(data["index"], data["prev_hash"], data["transactions"], data["nonce"])
    b.timestamp = data["timestamp"]
    b.hash = data["hash"]

    # ตรวจ: ต้องต่อจาก block ล่าสุด
    if b.prev_hash != node.last_block().hash:
        return jsonify({"status": "rejected", "reason": "bad chain"})

    # ตรวจ: hash ต้องถูกต้อง
    if b.calculate_hash() != b.hash:
        return jsonify({"status": "rejected", "reason": "invalid hash"})

    with node.lock:
        node.chain.append(b)
        node.save_chain()

    return jsonify({"status": "accepted", "block": b.index})

# ── TX ────────────────────────────────────────
@app.route("/tx/<txid>")
def get_tx(txid):
    result = node.get_tx(txid)
    if result:
        return jsonify(result)
    return jsonify({"error": "tx not found"}), 404

# ── Balance ───────────────────────────────────
@app.route("/balance/<address>")
def balance(address):
    return jsonify({"address": address, "balance": node.get_balance(address), "symbol": "DYX"})

# ── Mempool ───────────────────────────────────
@app.route("/mempool")
def mempool():
    return jsonify({"mempool": node.mempool, "count": len(node.mempool)})

# ── Send TX ───────────────────────────────────
@app.route("/send", methods=["POST"])
def send():
    tx = request.get_json()
    return jsonify(node.add_transaction(tx))

# ── Mine ──────────────────────────────────────
@app.route("/mine/<address>")
def mine(address):
    block = node.mine(address)
    # trigger consensus บน peers หลัง mine
    threading.Thread(
        target=lambda: [
            requests.get(f"{p}/consensus", timeout=3)
            for p in list(node.peers)
        ],
        daemon=True
    ).start()
    return jsonify({"success": True, "block": block.to_dict()})

# ── Peers ─────────────────────────────────────
@app.route("/peers")
def peers():
    return jsonify({"peers": list(node.peers), "count": len(node.peers)})

@app.route("/peers/add", methods=["POST"])
def add_peer():
    data = request.get_json()
    peer = data.get("peer", "").rstrip("/")
    if peer and peer not in node.peers:
        node.add_peer(peer)
        # แจ้ง peer กลับว่าเราอยู่ที่ไหน (handshake)
        my_url = data.get("self_url", "")
        if my_url:
            try:
                requests.post(peer + "/peers/add", json={"peer": my_url}, timeout=2)
            except Exception:
                pass
    return jsonify({"peers": list(node.peers)})

# ── Sync (pull longest chain) ─────────────────
@app.route("/sync", methods=["POST"])
def sync():
    replaced = node.sync_from_peers()
    return jsonify({"replaced": replaced, "length": len(node.chain)})

# ── Consensus (push: peer calls us to sync) ───
@app.route("/consensus", methods=["GET"])
def consensus():
    replaced = node.sync_from_peers()
    return jsonify({"replaced": replaced, "length": len(node.chain)})


# ═════════════════════════════════════════════
if __name__ == "__main__":
    print("=== DYNAX Node v2.0.0 ===")
    print(json.dumps(node.info(), indent=2))
    print(f"\n🌐 Running on http://0.0.0.0:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
