import socket, time, subprocess, os, sys

SYSTEM_ID = sys.argv[1] if len(sys.argv) > 1 else '1FC'
WORK_DIR  = sys.argv[2] if len(sys.argv) > 2 else '/tmp/sktest9'
PORT      = 6800
CONF      = '/tmp/test14.conf'
C_MOUNT   = '/opt/skeygen/dosbox/drive_c'

os.makedirs(WORK_DIR, exist_ok=True)
os.system(f"fuser -k {PORT}/tcp 2>/dev/null")
time.sleep(1)

open(CONF, 'w').write(f"""[sdl]
output=surface

[dosbox]
memsize=16

[cpu]
core=normal
cycles=10000

[serial]
serial1=nullmodem server:127.0.0.1 port:{PORT} transparent:1 telnet:0

[autoexec]
mount C "{C_MOUNT}"
mount D "{WORK_DIR}"
C:
CTTY COM1
SKEYGEN.EXE
EXIT
""")

srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(('127.0.0.1', PORT))
srv.listen(1)
srv.settimeout(30)

env = os.environ.copy()
env['SDL_VIDEODRIVER'] = 'dummy'
env['SDL_AUDIODRIVER'] = 'dummy'
proc = subprocess.Popen(['dosbox-x', '-conf', CONF],
    env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

print(f"Waiting for DOSBox (pid={proc.pid})...")
conn, addr = srv.accept()
conn.settimeout(0.1)
print("Connected!")

def drain(timeout=20, until=None):
    buf = b''
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            chunk = conn.recv(256)
            if chunk:
                buf += chunk
                sys.stdout.buffer.write(chunk)
                sys.stdout.flush()
                if until and until.encode() in buf:
                    return buf
        except socket.timeout:
            pass
    return buf

def flush_rx(seconds=1.5):
    """Discard incoming data for N seconds to clear buffer."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            conn.recv(4096)
        except socket.timeout:
            pass

def send(s):
    conn.sendall(s.encode('ascii'))

# Wait for splash
print("\n--- Waiting for splash ---")
drain(timeout=20, until='Any Key')
send(' ')

# Wait for menu
print("\n--- Waiting for menu ---")
drain(timeout=10, until='Display a system key file')
time.sleep(3)

# Send 1\r repeatedly until system ID prompt appears
print("\n--- Sending 1\\r until system ID prompt ---")
buf = b''
deadline = time.time() + 30
while time.time() < deadline:
    try:
        chunk = conn.recv(4096)
        if chunk:
            buf += chunk
            sys.stdout.buffer.write(chunk)
            sys.stdout.flush()
            if b'system ID' in buf:
                break
    except socket.timeout:
        pass
    send('1\r')
    time.sleep(1.2)

if b'system ID' not in buf:
    print("ERROR: never got system ID prompt")
    proc.terminate()
    sys.exit(1)

# CRITICAL: flush any extra buffered 1\r presses before sending system ID
print("\n--- Flushing buffer before system ID ---")
flush_rx(seconds=0.5)

print(f"\n--- Sending system ID: {SYSTEM_ID} ---")
send(SYSTEM_ID + '\r')

print("\n--- Waiting for path prompt ---")
buf = drain(timeout=10, until='path')
if b'path' not in buf:
    print("ERROR: never got path prompt")
    proc.terminate()
    sys.exit(1)


print("\n--- Sending path ---")
send('D:\\\r')

print("\n--- Waiting for completion ---")
buf = drain(timeout=20, until='End of System')
if b'End of System' in buf:
    print("\n--- SUCCESS ---")
else:
    print("\n--- WARNING: did not see completion message ---")

time.sleep(1)
send(' ')
time.sleep(2)

conn.close()
proc.terminate()
try:
    proc.wait(timeout=5)
except:
    proc.kill()

files = os.listdir(WORK_DIR)
print(f"\nFiles: {files}")
key = [f for f in files if f.upper().endswith('.KEY')]
print(f"KEY files: {key}")
