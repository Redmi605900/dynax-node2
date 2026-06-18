from ecdsa import SigningKey, SECP256k1
import hashlib, json

def create_wallet():
    sk = SigningKey.generate(curve=SECP256k1)
    vk = sk.verifying_key
    private = sk.to_string().hex()
    public = vk.to_string().hex()
    address = hashlib.sha256(vk.to_string()).hexdigest()
    return {"private": private, "public": public, "address": address}

wallet = create_wallet()
print(wallet)

with open("wallet/wallet.json", "w") as f:
    json.dump(wallet, f, indent=2)
