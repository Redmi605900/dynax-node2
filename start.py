import os
if os.path.exists("dynax_chain.json"):
    os.remove("dynax_chain.json")
    print("RESET: removed old dynax_chain.json, will create fresh genesis")

from dynax_node_v20 import app
import threading
from dynax_node_v20 import auto_mine_loop # Import แค่ตัวลูปที่ต้องการจริงๆ

# สั่งรัน Thread ตรงนี้ในไฟล์ start.py เลย
threading.Thread(target=auto_mine_loop, daemon=True).start()

# จบการตั้งค่า
