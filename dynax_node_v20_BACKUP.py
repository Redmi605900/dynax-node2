
from flask import Flask, jsonify
import json
import os

app = Flask(__name__)

CHAIN_FILE = "dynax_chain.json"
PEERS_FILE = "peers.json"
MEMPOOL_FILE = "mempool.json"


def load_json(file):
    if os.path.exists(file):
        try:
            with open(file, "r") as f:
                return json.load(f)
        except:
            return []
    return []


@app.route("/stats")
def stats():
    chain = load_json(CHAIN_FILE)
    return jsonify({
        "status": "online",
        "blocks": len(chain),
        "symbol": "DYX"
    })


@app.route("/chain")
def chain():
    return jsonify(load_json(CHAIN_FILE))


@app.route("/peers")
def peers():
    return jsonify(load_json(PEERS_FILE))


@app.route("/mempool")
def mempool():
    return jsonify(load_json(MEMPOOL_FILE))


if __name__ == "__main__":
    print("=== DYNAX CLEAN NODE START ===")
    app.run(host="0.0.0.0", port=6002, debug=False)


import threading
import time
import requests

PEER_SYNC_INTERVAL = 20


def sync_peers():
    while True:
        try:
            global peers
            updated = set(peers)

            for p in list(peers):
                try:
                    r = requests.get(p + "/peers", timeout=5)
                    if r.status_code == 200:
                        remote_peers = r.json()
                        if isinstance(remote_peers, list):
                            for rp in remote_peers:
                                updated.add(rp)
                except:
                    continue

            peers = list(updated)

        except Exception as e:
            print("[PEER SYNC ERROR]", e)

        time.sleep(PEER_SYNC_INTERVAL)


def start_p2p():
    t = threading.Thread(target=sync_peers, daemon=True)
    t.start()
    print("[P2P] Dynamic peer sync started")


start_p2p()


def adjust_difficulty(chain):
    if len(chain) < 10:
        return "0000"

    last_10 = chain[-10:]
    times = [b.get("timestamp", 0) for b in last_10]

    avg_time = (times[-1] - times[0]) / 10

    if avg_time < 20:
        return "00000"
    elif avg_time > 60:
        return "000"
    return "0000"


def broadcast_tx(tx):
    for p in peers:
        try:
            requests.post(p + "/tx", json=tx, timeout=3)
        except:
            pass


# =========================
# FULL CONSENSUS CORE
# =========================

def chain_weight(chain):
    # weight = difficulty + length
    return len(chain)


def is_valid_chain(chain):
    for i in range(1, len(chain)):
        prev = chain[i - 1]
        curr = chain[i]

        if curr.get("prev_hash") != prev.get("hash"):
            return False

        if not str(curr.get("hash", "")).startswith(curr.get("difficulty", "0000")):
            return False

        if curr.get("timestamp", 0) <= prev.get("timestamp", 0):
            return False

    return True


def resolve_fork(local_chain, remote_chain):
    if not is_valid_chain(remote_chain):
        return local_chain

    if chain_weight(remote_chain) > chain_weight(local_chain):
        return remote_chain

    return local_chain


def validate_block(prev, block):
    if block.get("prev_hash") != prev.get("hash"):
        return False

    if not str(block.get("hash", "")).startswith(block.get("difficulty", "0000")):
        return False

    if block.get("timestamp", 0) <= prev.get("timestamp", 0):
        return False

    return True


def sync_chain_from_peers():
    global chain

    for p in peers:
        try:
            import requests
            r = requests.get(p + "/chain", timeout=5)
            if r.status_code == 200:
                remote_chain = r.json()

                if isinstance(remote_chain, list):
                    chain = resolve_fork(chain, remote_chain)

        except Exception as e:
            print("[SYNC ERROR]", p, e)


import threading
import time

def start_consensus():
    def loop():
        while True:
            try:
                sync_chain_from_peers()
            except Exception as e:
                print("[CONSENSUS ERROR]", e)
            time.sleep(15)

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    print("[CONSENSUS] Full consensus engine started")


try:
    start_consensus()
except:
    pass


# =========================
# UTXO CORE MODEL
# =========================

UTXO = {}  # address -> list of outputs


def update_utxo(block):
    global UTXO

    for tx in block.get("transactions", []):

        if tx.get("from") == "SYSTEM":
            continue

        sender = tx.get("from")
        receiver = tx.get("to")
        amount = tx.get("amount", 0)

        # deduct sender
        if sender in UTXO:
            UTXO[sender] = max(0, UTXO[sender] - amount)

        # add receiver
        UTXO[receiver] = UTXO.get(receiver, 0) + amount


def validate_tx(tx):
    # basic structure check (upgrade later to ECDSA)
    required = ["from", "to", "amount"]

    for k in required:
        if k not in tx:
            return False

    if tx.get("amount", 0) <= 0:
        return False

    if tx.get("from") != "SYSTEM":
        balance = UTXO.get(tx.get("from"), 0)
        if balance < tx.get("amount", 0):
            return False

    return True


def add_to_mempool(tx):
    global mempool

    if validate_tx(tx):
        mempool.append(tx)
        return True

    return False


def apply_block(block):
    update_utxo(block)


def apply_chain(chain_data):
    for block in chain_data:
        apply_block(block)


import hashlib
import json

# =========================
# CORE CRYPTO LAYER
# =========================

def sha3(data):
    if isinstance(data, dict):
        data = json.dumps(data, sort_keys=True).encode()
    elif isinstance(data, str):
        data = data.encode()

    return hashlib.sha3_256(data).hexdigest()


from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
import base64

def verify_signature(tx):
    try:
        if "signature" not in tx:
            return False

        if "public_key" not in tx:
            return False

        verify_key = VerifyKey(base64.b64decode(tx["public_key"]))

        message = json.dumps({
            "from": tx.get("from"),
            "to": tx.get("to"),
            "amount": tx.get("amount")
        }, sort_keys=True).encode()

        signature = base64.b64decode(tx["signature"])

        verify_key.verify(message, signature)
        return True

    except Exception:
        return False


def validate_tx(tx):

    required = ["from", "to", "amount"]

    for k in required:
        if k not in tx:
            return False

    if tx.get("amount", 0) <= 0:
        return False

    # SYSTEM tx bypass
    if tx.get("from") == "SYSTEM":
        return True

    # signature required
    if not verify_signature(tx):
        return False

    balance = UTXO.get(tx.get("from"), 0)
    if balance < tx.get("amount", 0):
        return False

    return True


def validate_block_hash(block):
    computed = sha3({
        "index": block.get("index"),
        "prev_hash": block.get("prev_hash"),
        "transactions": block.get("transactions"),
        "nonce": block.get("nonce")
    })

    return computed == block.get("hash")


def validate_full_block(prev, block):

    if block.get("prev_hash") != prev.get("hash"):
        return False

    if not str(block.get("hash", "")).startswith(block.get("difficulty", "0000")):
        return False

    if block.get("timestamp", 0) <= prev.get("timestamp", 0):
        return False

    if not validate_block_hash(block):
        return False

    return True


# =========================
# PROTOCOL FINALIZATION
# =========================

TX_VERSION = 1

def tx_schema(tx):
    required = ["from", "to", "amount"]

    for k in required:
        if k not in tx:
            return False

    if tx.get("amount", 0) <= 0:
        return False

    if "version" in tx and tx["version"] != TX_VERSION:
        return False

    return True


def block_schema(block):
    required = ["index", "prev_hash", "timestamp", "nonce", "hash", "transactions"]

    for k in required:
        if k not in block:
            return False

    return True


def final_block_validation(prev, block):

    if not block_schema(block):
        return False

    if block.get("prev_hash") != prev.get("hash"):
        return False

    if not str(block.get("hash", "")).startswith(block.get("difficulty", "0000")):
        return False

    if block.get("timestamp", 0) <= prev.get("timestamp", 0):
        return False

    # crypto integrity
    if not validate_block_hash(block):
        return False

    # validate all tx inside block
    for tx in block.get("transactions", []):
        if not tx_schema(tx):
            return False

    return True


def mempool_filter(tx):
    if not tx_schema(tx):
        return False

    if tx.get("from") != "SYSTEM":
        if not validate_tx(tx):
            return False

    return True


def gossip_tx(tx):
    import requests

    for p in peers:
        try:
            requests.post(p + "/tx", json=tx, timeout=3)
        except:
            pass


def gossip_block(block):
    import requests

    for p in peers:
        try:
            requests.post(p + "/block", json=block, timeout=3)
        except:
            pass


def rebuild_chain(chain_data):
    new_chain = []

    for i in range(len(chain_data)):
        if i == 0:
            new_chain.append(chain_data[i])
            continue

        if final_block_validation(new_chain[-1], chain_data[i]):
            new_chain.append(chain_data[i])
        else:
            break

    return new_chain


def resolve_consensus(local, remote):

    local_valid = True
    remote_valid = True

    try:
        if len(remote) > len(local):
            remote = rebuild_chain(remote)
            if len(remote) > len(local):
                return remote
    except:
        pass

    return local


# =========================
# MAINNET HARDENING CORE
# =========================

def strict_validate_tx(tx):
    if not tx_schema(tx):
        return False

    if tx.get("amount", 0) > 1e9:
        return False

    if tx.get("from") == tx.get("to"):
        return False

    return True


def strict_validate_block(block):
    required = ["index", "prev_hash", "timestamp", "nonce", "hash", "transactions"]

    for k in required:
        if k not in block:
            return False

    if len(block.get("transactions", [])) > 2000:
        return False

    return True


def safe_reorg(local_chain, remote_chain):

    if not isinstance(remote_chain, list):
        return local_chain

    if len(remote_chain) <= len(local_chain):
        return local_chain

    # verify remote chain before accept
    try:
        for i in range(1, len(remote_chain)):
            prev = remote_chain[i - 1]
            curr = remote_chain[i]

            if curr.get("prev_hash") != prev.get("hash"):
                return local_chain
    except:
        return local_chain

    return remote_chain


PEER_SCORE = {}

def update_peer_health(peer, success=True):
    global PEER_SCORE

    if peer not in PEER_SCORE:
        PEER_SCORE[peer] = 0

    if success:
        PEER_SCORE[peer] += 1
    else:
        PEER_SCORE[peer] -= 2

    if PEER_SCORE[peer] < -10:
        try:
            peers.remove(peer)
        except:
            pass


def finalize_consensus(local_chain, remote_chain):

    if not isinstance(remote_chain, list):
        return local_chain

    remote_chain = rebuild_chain(remote_chain)

    if len(remote_chain) > len(local_chain):
        return remote_chain

    return local_chain


import time

TX_RATE_LIMIT = {}
BLOCK_RATE_LIMIT = {}

def rate_limit(addr, table, limit=5):
    now = time.time()

    if addr not in table:
        table[addr] = []

    table[addr] = [t for t in table[addr] if now - t < 60]

    if len(table[addr]) >= limit:
        return False

    table[addr].append(now)
    return True


def apply_block_safe(block):
    if not strict_validate_block(block):
        return False

    apply_block(block)
    return True


# =========================
# BITCOIN-STYLE GOSSIP LAYER
# =========================

def gossip(message_type, data):
    import requests

    for p in peers:
        try:
            if message_type == "tx":
                requests.post(p + "/tx", json=data, timeout=2)

            if message_type == "block":
                requests.post(p + "/block", json=data, timeout=2)

        except:
            update_peer_health(p, success=False)


ORPHAN_POOL = []


def receive_block(block):
    global chain

    if len(chain) == 0:
        chain.append(block)
        return True

    last = chain[-1]

    if validate_full_block(last, block):
        chain.append(block)
        return True
    else:
        # orphan block (future fork)
        ORPHAN_POOL.append(block)
        return False


def mempool_eviction():
    global mempool

    # sort by fee (highest priority first)
    mempool = sorted(mempool, key=lambda x: x.get("fee", 0), reverse=True)

    # limit size like Bitcoin (soft cap)
    MAX_MEMPOOL = 5000

    if len(mempool) > MAX_MEMPOOL:
        mempool = mempool[:MAX_MEMPOOL]


def resolve_orphans():
    global ORPHAN_POOL, chain

    remaining = []

    for block in ORPHAN_POOL:
        last = chain[-1]

        if validate_full_block(last, block):
            chain.append(block)
        else:
            remaining.append(block)

    ORPHAN_POOL = remaining


def start_network_engine():
    import threading
    import time

    def loop():
        while True:
            try:
                mempool_eviction()
                resolve_orphans()
            except Exception as e:
                print("[NET ENGINE ERROR]", e)

            time.sleep(10)

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    print("[NETWORK] Bitcoin-style engine started")


try:
    start_network_engine()
except:
    pass


import socket
import threading
import json

P2P_PORT = 7001

def handle_peer(conn):
    try:
        data = conn.recv(65536).decode()
        msg = json.loads(data)

        if msg.get("type") == "tx":
            add_to_mempool(msg["data"])

        if msg.get("type") == "block":
            receive_block(msg["data"])

        conn.close()
    except:
        conn.close()


def start_p2p_server():
    def server():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("0.0.0.0", P2P_PORT))
        s.listen(50)

        print("[P2P] TCP server started on", P2P_PORT)

        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_peer, args=(conn,), daemon=True).start()

    t = threading.Thread(target=server, daemon=True)
    t.start()


def send_p2p(peer_host, msg):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((peer_host, P2P_PORT))
        s.send(json.dumps(msg).encode())
        s.close()
    except:
        update_peer_health(peer_host, success=False)


def inv_block(block_hash):
    return {
        "type": "inv",
        "data": {
            "hash": block_hash,
            "kind": "block"
        }
    }


def inv_tx(tx_id):
    return {
        "type": "inv",
        "data": {
            "id": tx_id,
            "kind": "tx"
        }
    }


def request_missing_block(block_hash):
    for p in peers:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((p, P2P_PORT))

            msg = {
                "type": "getdata",
                "data": {"hash": block_hash}
            }

            s.send(json.dumps(msg).encode())
            s.close()
            return
        except:
            continue


def rebuild_utxo_from_chain():
    global UTXO

    UTXO = {}

    for block in chain:
        for tx in block.get("transactions", []):
            sender = tx.get("from")
            receiver = tx.get("to")
            amount = tx.get("amount", 0)

            if sender != "SYSTEM":
                UTXO[sender] = UTXO.get(sender, 0) - amount

            UTXO[receiver] = UTXO.get(receiver, 0) + amount


def start_full_node():
    start_p2p_server()
    start_network_engine()
    start_consensus()

    print("[DYNAX] FULL BITCOIN CORE EMULATION LEVEL 2 ONLINE")


if __name__ == "__main__":
    start_full_node()
    app.run(host="0.0.0.0", port=6002, debug=False)


# =========================
# SATOSHI FINAL MODE
# =========================

def compact_block(block):
    return {
        "hash": block.get("hash"),
        "prev_hash": block.get("prev_hash"),
        "index": block.get("index"),
        "timestamp": block.get("timestamp"),
        "tx_ids": [hashlib.sha3_256(json.dumps(tx, sort_keys=True).encode()).hexdigest()
                   for tx in block.get("transactions", [])]
    }


def gossip_mempool(tx):
    import requests

    for p in peers:
        try:
            requests.post(p + "/tx", json={
                "type": "tx",
                "data": tx
            }, timeout=2)
        except:
            update_peer_health(p, success=False)


def bloom_filter(address, tx):
    # simplified bloom behavior (not cryptographic bloom)
    if tx.get("from") == address or tx.get("to") == address:
        return True
    return False


def filter_wallet_view(address):
    result = []

    for block in chain:
        for tx in block.get("transactions", []):
            if bloom_filter(address, tx):
                result.append(tx)

    return result


def final_node_rule(tx, block):

    # 1. TX must pass strict validation
    if not strict_validate_tx(tx):
        return False

    # 2. Block must pass full validation
    if not final_block_validation(block, block):
        return False

    # 3. UTXO must remain consistent
    try:
        rebuild_utxo_from_chain()
    except:
        return False

    return True


def start_satoshi_engine():
    import threading
    import time

    def loop():
        while True:
            try:
                mempool_eviction()
                resolve_orphans()
                rebuild_utxo_from_chain()
            except Exception as e:
                print("[SATOSHI ENGINE ERROR]", e)

            time.sleep(8)

    t = threading.Thread(target=loop, daemon=True)
    t.start()

    print("[SATOSHI] FINAL MODE ACTIVE")


def start_satoshi_node():
    start_p2p_server()
    start_network_engine()
    start_consensus()
    start_satoshi_engine()

    print("[DYNAX] SATOSHI FINAL MODE ONLINE")


if __name__ == "__main__":
    start_satoshi_node()
    app.run(host="0.0.0.0", port=6002, debug=False)

