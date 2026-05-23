import time
import json
import hashlib
import os
import hmac

CHAIN_FILE = "/data/data/com.termux/files/home/dynax_chain.json"
DIFFICULTY = 4
BLOCK_REWARD = 50
SECRET_KEY = "DYNAX_SECRET_v1"

class Block:
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

class DYNAXCore:
    def __init__(self):
        self.chain = []
        self.mempool = []
        self.load_chain()

    def save_chain(self):
        data = [{"index": b.index, "timestamp": b.timestamp, "prev_hash": b.prev_hash, "transactions": b.transactions, "nonce": b.nonce, "hash": b.hash} for b in self.chain]
        with open(CHAIN_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def load_chain(self):
        if not os.path.exists(CHAIN_FILE):
            genesis_txs = [
                {"from": "GENESIS", "to": "DX5293ada2aa014167fa15942c4318b6235fe7d1", "amount": 300000},
                {"from": "GENESIS", "to": "DXf2a9fc9e0b20602d66af8ecae2032f0e56c20f", "amount": 7000},
                {"from": "GENESIS", "to": "DX8a6e18a35d23368fa553f87552693d91f58ce6", "amount": 445},
                {"from": "GENESIS", "to": "DX9ac31f667d87ec3a5940ac409d9a54de8b0507", "amount": 137}
            ]
            genesis = Block(0, "0"*64, genesis_txs)
            self.chain.append(genesis)
            self.save_chain()
            return
        with open(CHAIN_FILE) as f:
            data = json.load(f)
        for item in data:
            b = Block(item["index"], item["prev_hash"], item["transactions"], item["nonce"])
            b.timestamp = item["timestamp"]
            b.hash = item["hash"]
            self.chain.append(b)

    def last_block(self):
        return self.chain[-1]

    def verify_chain(self):
        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i-1]
            if curr.prev_hash != prev.hash:
                return False
            if curr.hash != curr.calculate_hash():
                return False
        return True

    def add_transaction(self, tx):
        required = ["from", "to", "amount", "signature"]
        for r in required:
            if r not in tx:
                return {"success": False, "error": f"missing {r}"}
        tx_canonical = {"from": tx["from"], "to": tx["to"], "amount": tx["amount"]}
        message = json.dumps(tx_canonical, sort_keys=True).encode()
        expected_sig = hmac.new(SECRET_KEY.encode(), message, hashlib.sha3_256).hexdigest()
        if expected_sig != tx["signature"]:
            return {"success": False, "error": "invalid signature"}
        tx["txid"] = hashlib.sha3_256(json.dumps(tx_canonical, sort_keys=True).encode()).hexdigest()
        self.mempool.append(tx)
        return {"success": True, "txid": tx["txid"]}

    def mine(self, miner_address):
        reward_tx = {"from": "NETWORK", "to": miner_address, "amount": BLOCK_REWARD}
        txs = self.mempool + [reward_tx]
        block = Block(len(self.chain), self.last_block().hash, txs)
        while not block.hash.startswith("0" * DIFFICULTY):
            block.nonce += 1
            block.hash = block.calculate_hash()
        self.chain.append(block)
        self.mempool = []
        self.save_chain()
        return block

    def get_balance(self, address):
        balance = 0
        for block in self.chain:
            for tx in block.transactions:
                if tx.get("from") == address:
                    balance -= tx["amount"]
                if tx.get("to") == address:
                    balance += tx["amount"]
        return balance

    def info(self):
        return {
            "name": "DYNAX",
            "symbol": "DYX",
            "blocks": len(self.chain),
            "difficulty": DIFFICULTY,
            "reward": BLOCK_REWARD,
            "valid": self.verify_chain()
        }

if __name__ == "__main__":
    core = DYNAXCore()
    print("=== DYNAX CORE ===")
    print(core.info())
    print("\nChain valid:", core.verify_chain())
    print("\n=== BALANCES ===")
    for addr in ["DX5293ada2aa014167fa15942c4318b6235fe7d1", "DXf2a9fc9e0b20602d66af8ecae2032f0e56c20f", "DX8a6e18a35d23368fa553f87552693d91f58ce6", "DX9ac31f667d87ec3a5940ac409d9a54de8b0507"]:
        print(f"{addr[:20]}...: {core.get_balance(addr):,} DYX")
