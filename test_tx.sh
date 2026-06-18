#!/bin/bash

NODE="http://192.168.43.166:6001"
SENDER="DX5293ada2aa014167fa..."
RECIPIENT="DXf2a9fc9e0b20602d66..."
AMOUNT=10

echo "=== 1. ส่ง Transaction ==="
curl -s -X POST $NODE/tx \
  -H "Content-Type: application/json" \
  -d "{\"sender\":\"$SENDER\",\"recipient\":\"$RECIPIENT\",\"amount\":$AMOUNT}"

echo -e "\n\n=== 2. ตรวจสอบ Mempool ==="
curl -s $NODE/mempool

echo -e "\n\n=== 3. ขุด Block ใหม่ ==="
curl -s $NODE/mine/$SENDER

echo -e "\n\n=== 4. เช็ค Balance ของ Sender ==="
curl -s $NODE/balance/$SENDER

echo -e "\n\n=== 5. เช็ค Balance ของ Recipient ==="
curl -s $NODE/balance/$RECIPIENT
