#!/usr/bin/env python3
import json, os, hashlib, random, socket, threading

CHAIN_FILE = "chain.json"
DIFFICULTY = 2
BLOCK_REWARD = 50
PEERS = []

class Block:
    def __init__(self, index, previous_hash, transactions):
        self.index = index
        self.previous_hash = previous_hash
        self.transactions = transactions
        self.timestamp = str(index)
        self.hash = hashlib.sha256(json.dumps(transactions).encode()).hexdigest()

class DYNAXCore:
    def __init__(self):
        self.chain = []
        self.mempool = []
        self.balances = {}
        self.load_chain()

    def verify_chain(self):
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            if current.previous_hash != previous.hash:
                return False
            recalculated_hash = hashlib.sha256(
                json.dumps(current.transactions).encode()
            ).hexdigest()
            if current.hash != recalculated_hash:
                return False
        return True

    def save_chain(self):
        data = [
            {
                "index": b.index,
                "timestamp": b.timestamp,
                "transactions": b.transactions,
                "previous_hash": b.previous_hash,
                "hash": b.hash
            }
            for b in self.chain
        ]
        with open(CHAIN_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def load_chain(self):
        if not os.path.exists(CHAIN_FILE):
            genesis_txs = [
                {"from": "GENESIS", "to": "DX1", "amount": 300000},
                {"from": "GENESIS", "to": "DX2", "amount": 7100},
                {"from": "GENESIS", "to": "DX3", "amount": 445},
                {"from": "GENESIS", "to": "DX4", "amount": 137}
            ]
            genesis = Block(0, "0"*64, genesis_txs)
            self.chain.append(genesis)
            for tx in genesis_txs:
                self.balances[tx["to"]] = self.balances.get(tx["to"], 0) + tx["amount"]
            self.save_chain()
            return
        with open(CHAIN_FILE) as f:
            data = json.load(f)
        for item in data:
            b = Block(item["index"], item["previous_hash"], item["transactions"])
            b.timestamp = item["timestamp"]
            b.hash = item["hash"]
            self.chain.append(b)
        for block in self.chain:
            for tx in block.transactions:
                if tx["from"] != "GENESIS":
                    self.balances[tx["from"]] = self.balances.get(tx["from"], 0) - tx["amount"]
                self.balances[tx["to"]] = self.balances.get(tx["to"], 0) + tx["amount"]

    def add_transaction(self, sender, recipient, amount):
        tx = {"from": sender, "to": recipient, "amount": amount}
        self.mempool.append(tx)
        broadcast_transaction(tx)
        return tx

    def mine_block(self, miner_address):
        if not self.mempool:
            return None
        previous_block = self.chain[-1]
        new_block = Block(len(self.chain), previous_block.hash, self.mempool)
        self.chain.append(new_block)
        for tx in self.mempool:
            sender = tx["from"]
            recipient = tx["to"]
            amount = tx["amount"]
            if sender != "GENESIS":
                self.balances[sender] = self.balances.get(sender, 0) - amount
            self.balances[recipient] = self.balances.get(recipient, 0) + amount
        self.balances[miner_address] = self.balances.get(miner_address, 0) + BLOCK_REWARD
        self.mempool = []
        self.save_chain()
        broadcast_block(new_block)
        return new_block

    def get_balance(self, address):
        return self.balances.get(address, 0)

# ---------------- Networking ----------------
def handle_client(conn, addr, core):
    while True:
        try:
            data = conn.recv(4096)
            if not data:
                break
            message = json.loads(data.decode())
            if message["type"] == "transaction":
                core.add_transaction(message["from"], message["to"], message["amount"])
            elif message["type"] == "block":
                # TODO: ตรวจสอบและเพิ่ม block ใหม่
                pass
        except:
            break
    conn.close()

def start_server(core, host="0.0.0.0", port=30303):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, port))
    s.listen()
    print(f"Node listening on {host}:{port}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn, addr, core)).start()

def connect_to_peer(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, port))
    PEERS.append(s)
    return s

def broadcast_transaction(tx):
    for peer in PEERS:
        peer.send(json.dumps({"type": "transaction", **tx}).encode())

def broadcast_block(block):
    for peer in PEERS:
        peer.send(json.dumps({"type": "block", "index": block.index,
                              "transactions": block.transactions,
                              "previous_hash": block.previous_hash,
                              "hash": block.hash}).encode())

# ---------------- Run Node ----------------
if __name__ == "__main__":
    core = DYNAXCore()
    threading.Thread(target=start_server, args=(core,)).start()

    wallets = ["DX1","DX2","DX3","DX4"]
    for i in range(5):
        miner = random.choice(wallets)
        core.add_transaction("DX2","DX3",100)
        core.mine_block(miner)
        print(f"Block {len(core.chain)-1} mined by {miner}")

    print("\n=== BALANCES ===")
    for addr in wallets:
        print(f"{addr}: {core.get_balance(addr)} DYX")
    print("\nChain valid:", core.verify_chain())
