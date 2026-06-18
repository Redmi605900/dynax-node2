from wallet import Wallet

w = Wallet()

print("PRIVATE:", w.get_private_key())
print("PUBLIC :", w.get_public_key())
print("ADDRESS:", w.get_address())
