#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p backups

# Backup Code
cp dynax_node_v20.py "backups/dynax_node_v20_${DATE}.py"

# Backup Data (ป้องกันข้อมูลบล็อกปัจจุบันหาย)
[ -f dynax_chain.json ] && cp dynax_chain.json "backups/dynax_chain_${DATE}.json"
[ -f peers.json ] && cp peers.json "backups/peers_${DATE}.json"

echo "✅ Backup Completed: Code & Chain Data (${DATE})"
