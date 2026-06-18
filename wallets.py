import hashlib
import secrets

wallets = []

for i in range(4):
    private_key = secrets.token_hex(32)

    address = "DX" + hashlib.sha256(
        private_key.encode()
    ).hexdigest()[:40]

    wallets.append({
        "wallet": i + 1,
        "address": address,
        "private_key": private_key
    })

for w in wallets:
    print(w)
