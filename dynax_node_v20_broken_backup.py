import time
import requests
import threading
import json
import hashlib

import os
from flask import Flask, jsonify, request
from ecdsa import VerifyingKey, SECP256k1

app = Flask(__name__)

def pubkey_to_address(pubkey_bytes):
    h = hashlib.sha3_256(pubkey_bytes).hexdigest()
    return "DX" + h[:40]

def verify_signature(from_addr, msg_text, sig_hex):



# =========================
# FIXED CORE VALIDATION LAYER
# =========================

    if block.get("prev_hash") != prev.get("hash"):
        return False
    if not block.get("hash", "").startswith("0000"):
        return False
    if block.get("timestamp", 0) <= prev.get("timestamp", 0):
        return False
    return True


# =========================
# RECOVERED VALIDATION LAYER
# =========================

def validate_transaction_pool(mempool):
    seen = set()
    valid = []

    for tx in mempool:
        if not isinstance(tx, dict):
            continue

        key = str(tx.get("from")) + str(tx.get("amount", 0))

        if key in seen:
            continue

        seen.add(key)
        valid.append(tx)

    return valid


def validate_block(prev, block):
    if not isinstance(block, dict) or not isinstance(prev, dict):
        return False

    if block.get("prev_hash") != prev.get("hash"):
        return False

    if not str(block.get("hash", "")).startswith("0000"):
        return False

    if block.get("timestamp", 0) <= prev.get("timestamp", 0):
        return False

    return True


import traceback

try:
    main()
except Exception as e:
    print("FATAL ERROR:")
    traceback.print_exc()


# =========================
# FORCE SERVER START (FIX)
# =========================

from flask import Flask


@app.route("/stats")
def stats():
    return {"status": "running"}

if __name__ == "__main__":
    print("[DYNAX] FORCE START SERVER")


# =========================
# MISSING API ENDPOINTS FIX
# =========================

@app.route("/chain")
def chain():
    try:
        return {"chain": getattr(globals().get("self", None), "chain", [])}
    except:
        return {"chain": []}


@app.route("/peers")
def peers():
    try:
        return {"peers": list(KNOWN_PEERS) if "KNOWN_PEERS" in globals() else []}
    except:
        return {"peers": []}


@app.route("/mempool")
def mempool():
    try:
        return {"mempool": getattr(globals().get("self", None), "mempool", [])}
    except:
        return {"mempool": []}


# =========================
# SINGLE ENTRY POINT
# =========================

if __name__ == "__main__":
    print("[DYNAX] NODE STARTING...")
    app.run(host="0.0.0.0", port=6002, debug=False)


# =========================
# GLOBAL STATE FIX
# =========================

if "chain" not in globals():
    chain = []

if "peers" not in globals():
    peers = []

if "mempool" not in globals():
    mempool = []

@app.route("/chain")
def chain_api():
    return {"chain": chain}

@app.route("/peers")
def peers_api():
    return {"peers": peers}

@app.route("/mempool")
def mempool_api():
    return {"mempool": mempool}


# =========================
# REAL FILE-BASED STATE LOADER
# =========================

import json
import os

CHAIN_FILE = "dynax_chain.json"
PEERS_FILE = "peers.json"
MEMPOOL_FILE = "mempool.json"




def load_mempool():
    if os.path.exists(MEMPOOL_FILE):
        if os.path.exists(MEMPOOL_FILE):
            with open(MEMPOOL_FILE, "r") as f:
                return json.load(f)
    return []


@app.route("/chain")
def chain_api():
    chain = load_chain()
    return {
        "chain": chain,
        "height": len(chain),
        "source": "dynax_chain.json"
    }


@app.route("/peers")
def peers_api():
    peers = load_peers()
    return {
        "peers": peers,
        "count": len(peers),
        "source": "peers.json"
    }


@app.route("/mempool")
def mempool_api():
    mempool = load_mempool()
    return {
        "mempool": mempool,
        "size": len(mempool),
        "source": "file"
    }


# =========================
# SAFE FILE LOADER (FIXED)
# =========================

import json
import os

def load_chain():
    print("[DEBUG] loading chain file")
    if os.path.exists("dynax_chain.json"):
        with open("dynax_chain.json", "r") as f:
            return json.load(f)
    return []


def load_peers():
    print("[DEBUG] loading peers file")
    if os.path.exists("peers.json"):
        with open("peers.json", "r") as f:
            return json.load(f)
    return []


def load_mempool():
    print("[DEBUG] loading mempool file")
    if os.path.exists("mempool.json"):
        with open("mempool.json", "r") as f:
            return json.load(f)
    return []

