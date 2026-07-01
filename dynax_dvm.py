"""
DYNAX Virtual Machine (DVM) - Smart Contract System
"""

import hashlib
import json
import dynax_db as db
import time
from typing import Dict, List, Optional
from dynax_events import event_log


class DVMContract:
    def __init__(self, address, owner, code):
        self.address = address
        self.owner = owner
        self.code = code
        self.storage = {}
        self.balance = 0
        self.created_at = int(time.time())

    def to_dict(self):
        return {
            "address": self.address,
            "owner": self.owner,
            "code": self.code,
            "storage": self.storage,
            "balance": self.balance,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data):
        c = cls(data["address"], data["owner"], data["code"])
        c.storage = data.get("storage", {})
        c.balance = data.get("balance", 0)
        c.created_at = data.get("created_at", 0)
        return c


class DVM:
    def __init__(self):
        self.contracts = {}
        self.contract_list = []

    def generate_address(self, owner, nonce):
        raw = f"{owner}:{nonce}:{int(time.time())}"
        h = hashlib.sha3_256(raw.encode()).hexdigest()
        return f"CX{h[:40]}"

    def deploy_contract(self, owner, code, nonce):
        try:
            if not code or len(code.strip()) == 0:
                return {"error": "Empty contract code"}
            address = self.generate_address(owner, nonce)
            contract = DVMContract(address, owner, code)
            self.contracts[address] = contract
            self.contract_list.append(address)
            return {"status": "deployed", "address": address, "owner": owner, "code_size": len(code)}
        except Exception as e:
            return {"error": str(e)}

    def execute_contract(self, address, method, args=None, caller=None):
        try:
            if address not in self.contracts:
                return {"error": "Contract not found"}
            contract = self.contracts[address]
            args = args or []
            if method == "get":
                key = args[0] if args else None
                if key and key in contract.storage:
                    return {"result": contract.storage[key]}
                return {"result": None}
            elif method == "set":
                if caller != contract.owner:
                    return {"error": "Only owner can set"}
                if len(args) >= 2:
                    key, value = args[0], args[1]
                    contract.storage[key] = value
                    return {"status": "success", "key": key, "value": value}
                return {"error": "Need key and value"}
            elif method == "balance":
                return {"balance": contract.balance}
            elif method == "transfer":
                if len(args) >= 2:
                    to, amount = args[0], args[1]
                    if contract.balance >= amount:
                        contract.balance -= amount
                        return {"status": "transferred", "to": to, "amount": amount}
                    return {"error": "Insufficient balance"}
                return {"error": "Need to and amount"}
            else:
                return {"error": f"Unknown method: {method}"}
        except Exception as e:
            return {"error": str(e)}

    def get_contract(self, address):
        if address in self.contracts:
            return self.contracts[address].to_dict()
        return None

    def list_contracts(self):
        return [self.contracts[a].to_dict() for a in self.contract_list]

    def save_contracts(self, filename="contracts.json"):
        for addr in self.contracts:
            c = self.contracts[addr]
            db.save_contract(c.address, c.owner, c.code, c.storage, c.balance, c.created_at, 1)
    def load_contracts(self, filename="contracts.json"):
        try:
            contracts = db.load_all_contracts()
            self.contracts = {}
            self.contract_list = []
            for c in contracts:
                contract = DVMContract(c["address"], c["owner"], c["code"])
                contract.storage = c["storage"]
                contract.balance = c["balance"]
                contract.created_at = c["created_at"]
                self.contracts[contract.address] = contract
                self.contract_list.append(contract.address)
            return True
        except Exception as e:
            print(f"Load error: {e}")
            return False

    def execute_contract_with_events(self, address, method, args=None, caller=None, block_number=0):
        """Execute contract พร้อม emit events"""
        result = self.execute_contract(address, method, args, caller)
        
        # Emit events ตาม method
        if method == "set" and result.get("status") == "success":
            key, value = args[0], args[1]
            event_log.emit(
                contract_address=address,
                event_name="StorageChanged",
                data={"key": key, "value": value, "caller": caller},
                block_number=block_number
            )
        
        elif method == "transfer" and result.get("status") == "transferred":
            event_log.emit(
                contract_address=address,
                event_name="Transfer",
                data={"to": args[0], "amount": args[1]},
                block_number=block_number
            )
        
        return result

dvm = DVM()
dvm.load_contracts()
print("DVM loaded, contracts:", len(dvm.contract_list))
