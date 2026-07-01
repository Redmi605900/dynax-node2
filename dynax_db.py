import sqlite3
import json
import time
import threading

DB_FILE="dynax.db"
lock=threading.Lock()

def get_conn():
    conn=sqlite3.connect(DB_FILE,check_same_thread=False)
    conn.row_factory=sqlite3.Row
    return conn

def init_db():
    with lock:
        conn=get_conn()
        c=conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS blocks (idx INTEGER PRIMARY KEY,timestamp INTEGER,transactions TEXT,previous_hash TEXT,nonce INTEGER,hash TEXT UNIQUE,miner TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS contracts (address TEXT PRIMARY KEY,owner TEXT,code TEXT,storage TEXT,balance INTEGER DEFAULT 0,created_at INTEGER,nonce INTEGER DEFAULT 1)")
        c.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT,contract_address TEXT,event_name TEXT,data TEXT,block_number INTEGER,timestamp INTEGER)")
        c.execute("CREATE TABLE IF NOT EXISTS peers (url TEXT PRIMARY KEY,last_seen INTEGER,status TEXT DEFAULT active)")
        c.execute("CREATE TABLE IF NOT EXISTS mempool (tx_hash TEXT PRIMARY KEY,data TEXT,timestamp INTEGER)")
        conn.commit()
        conn.close()
        print("Database initialized")

def save_block(block):
    with lock:
        conn=get_conn()
        c=conn.cursor()
        c.execute("INSERT OR REPLACE INTO blocks VALUES (?,?,?,?,?,?,?)",(block["index"],block["timestamp"],json.dumps(block["transactions"]),block["previous_hash"],block["nonce"],block["hash"],block["miner"]))
        conn.commit()
        conn.close()

def load_all_blocks():
    with lock:
        conn=get_conn()
        c=conn.cursor()
        c.execute("SELECT * FROM blocks ORDER BY idx")
        rows=c.fetchall()
        conn.close()
        blocks=[]
        for r in rows:
            b={}
            b["index"]=r["idx"]
            b["timestamp"]=r["timestamp"]
            b["transactions"]=json.loads(r["transactions"])
            b["previous_hash"]=r["previous_hash"]
            b["nonce"]=r["nonce"]
            b["hash"]=r["hash"]
            b["miner"]=r["miner"]
            blocks.append(b)
        return blocks

def get_last_block():
    with lock:
        conn=get_conn()
        c=conn.cursor()
        c.execute("SELECT * FROM blocks ORDER BY idx DESC LIMIT 1")
        row=c.fetchone()
        conn.close()
        if row:
            b={}
            b["index"]=row["idx"]
            b["timestamp"]=row["timestamp"]
            b["transactions"]=json.loads(row["transactions"])
            b["previous_hash"]=row["previous_hash"]
            b["nonce"]=row["nonce"]
            b["hash"]=row["hash"]
            b["miner"]=row["miner"]
            return b
        return None

def save_contract(addr,owner,code,storage,balance=0,created_at=0,nonce=1):
    with lock:
        conn=get_conn()
        c=conn.cursor()
        c.execute("INSERT OR REPLACE INTO contracts VALUES (?,?,?,?,?,?,?)",(addr,owner,code,json.dumps(storage),balance,created_at,nonce))
        conn.commit()
        conn.close()

def load_all_contracts():
    with lock:
        conn=get_conn()
        c=conn.cursor()
        c.execute("SELECT * FROM contracts")
        rows=c.fetchall()
        conn.close()
        contracts=[]
        for r in rows:
            ct={}
            ct["address"]=r["address"]
            ct["owner"]=r["owner"]
            ct["code"]=r["code"]
            ct["storage"]=json.loads(r["storage"])
            ct["balance"]=r["balance"]
            ct["created_at"]=r["created_at"]
            ct["nonce"]=r["nonce"]
            contracts.append(ct)
        return contracts

def save_event(ca,en,data,bn,ts):
    with lock:
        conn=get_conn()
        c=conn.cursor()
        c.execute("INSERT INTO events (contract_address,event_name,data,block_number,timestamp) VALUES (?,?,?,?,?)",(ca,en,json.dumps(data),bn,ts))
        conn.commit()
        conn.close()

def load_all_events():
    with lock:
        conn=get_conn()
        c=conn.cursor()
        c.execute("SELECT * FROM events ORDER BY id DESC")
        rows=c.fetchall()
        conn.close()
        events=[]
        for r in rows:
            e={}
            e["contract_address"]=r["contract_address"]
            e["event_name"]=r["event_name"]
            e["data"]=json.loads(r["data"])
            e["block_number"]=r["block_number"]
            e["timestamp"]=r["timestamp"]
            events.append(e)
        return events

def save_peer(url):
    with lock:
        conn=get_conn()
        c=conn.cursor()
        c.execute("INSERT OR REPLACE INTO peers VALUES (?,?,active)",(url,int(time.time())))
        conn.commit()
        conn.close()

def load_all_peers():
    with lock:
        conn=get_conn()
        c=conn.cursor()
        c.execute("SELECT url FROM peers WHERE status=active")
        rows=c.fetchall()
        conn.close()
        return [r["url"] for r in rows]

def save_mempool_tx(tx_hash,data):
    with lock:
        conn=get_conn()
        c=conn.cursor()
        c.execute("INSERT OR REPLACE INTO mempool VALUES (?,?,?)",(tx_hash,json.dumps(data),int(time.time())))
        conn.commit()
        conn.close()

def load_mempool():
    with lock:
        conn=get_conn()
        c=conn.cursor()
        c.execute("SELECT * FROM mempool ORDER BY timestamp")
        rows=c.fetchall()
        conn.close()
        txs=[]
        for r in rows:
            t={}
            t["tx_hash"]=r["tx_hash"]
            t["data"]=json.loads(r["data"])
            t["timestamp"]=r["timestamp"]
            txs.append(t)
        return txs

def remove_mempool_tx(tx_hash):
    with lock:
        conn=get_conn()
        c=conn.cursor()
        c.execute("DELETE FROM mempool WHERE tx_hash=?",(tx_hash,))
        conn.commit()
        conn.close()

init_db()
print("DYNAX Database ready")
