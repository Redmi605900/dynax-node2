from flask import Flask, jsonify
import json
import os
from config import *

app = Flask(__name__)

def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default

@app.get("/stats")
def stats():
    chain = load_json(CHAIN_FILE, [])
    peers = load_json(PEERS_FILE, [])
    return jsonify({
        "status": "online",
        "symbol": SYMBOL,
        "hash": HASH_ALGORITHM,
        "blocks": len(chain),
        "peers": len(peers)
    })

@app.get("/chain")
def chain():
    return jsonify(load_json(CHAIN_FILE, []))

@app.get("/peers")
def peers():
    return jsonify(load_json(PEERS_FILE, []))

if __name__ == "__main__":
    print("=== DYNAX CORE v21 ===")
    app.run(host=HOST, port=PORT, debug=False)
