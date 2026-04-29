#!/usr/bin/env python3
import os, re, time, uuid, shutil, subprocess, threading, socket
from pathlib import Path
from flask import Flask, render_template, request, send_file, jsonify, after_this_request

app = Flask(__name__)

BASE_DIR = Path(__file__).parent.parent
EXE_DIR  = BASE_DIR / "dosbox" / "drive_c"
WORK_DIR = BASE_DIR / "work"
WORK_DIR.mkdir(parents=True, exist_ok=True)

SYSID_RE = re.compile(r'^[0-9A-Fa-f]{1,6}$')

def validate_system_id(raw):
    s = raw.strip().upper()
    if not s: return False, "System ID is required."
    if not SYSID_RE.match(s): return False, "System ID must be 1-6 hex characters."
    return True, s

def run_skeygen(work_path, system_id):
    port = 6800
    c_mount = str(EXE_DIR)
    d_mount = str(work_path)
    conf_path = work_path / "dosbox.conf"

    conf_path.write_text(
        '[sdl]\noutput=surface\n\n'
        '[dosbox]\nmemsize=16\n\n'
        '[cpu]\ncore=normal\ncycles=10000\n\n'
        '[serial]\n'
        f'serial1=nullmodem server:127.0.0.1 port:{port} transparent:1 telnet:0\n\n'
        '[autoexec]\n'
        f'mount C "{c_mount}"\n'
        f'mount D "{d_mount}"\n'
        'C:\nCTTY COM1\nSKEYGEN.EXE\nEXIT\n'
    )

    # Start TCP server before DOSBox
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('127.0.0.1', port))
    srv.listen(1)
    srv.settimeout(30)

    env = os.environ.copy()
    env['SDL_VIDEODRIVER'] = 'dummy'
    env['SDL_AUDIODRIVER'] = 'dummy'
    proc = subprocess.Popen(
        ['dosbox-x', '-conf', str(conf_path)],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    try:
        conn, _ = srv.accept()
    except socket.timeout:
        proc.terminate()
        return {"ok": False, "error": "DOSBox did not connect."}
    finally:
        srv.close()

    conn.settimeout(0.1)

    def drain(timeout=20, until=None):
        buf = b''
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                chunk = conn.recv(256)
                if chunk:
                    buf += chunk
                    if until and until.encode() in buf:
                        return buf
            except socket.timeout:
                pass
        return buf

    def flush_rx(seconds=0.5):
        deadline = time.time() + seconds
        while time.time() < deadline:
            try:
                conn.recv(4096)
            except socket.timeout:
                pass

    def send(s):
        conn.sendall(s.encode('ascii'))

    try:
        # Splash
        drain(timeout=20, until='Any Key')
        send(' ')

        # Menu
        drain(timeout=10, until='Display a system key file')
        time.sleep(3)

        # Send 1\r until system ID prompt
        buf = b''
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                chunk = conn.recv(4096)
                if chunk:
                    buf += chunk
                    if b'system ID' in buf:
                        break
            except socket.timeout:
                pass
            send('1\r')
            time.sleep(1.2)

        if b'system ID' not in buf:
            return {"ok": False, "error": "EXE never reached system ID prompt."}

        flush_rx(seconds=0.5)
        send(system_id + '\r')

        buf = drain(timeout=10, until='path')
        if b'path' not in buf:
            return {"ok": False, "error": "EXE never reached path prompt."}

        send('D:\\\r')
        drain(timeout=20, until='End of System')
        time.sleep(1)
        send(' ')
        time.sleep(2)

    finally:
        conn.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except:
            proc.kill()

    key_files = list(work_path.glob("SYS001FC.KEY".replace("1FC", system_id.upper() + "*")))
    key_files = [f for f in work_path.glob("*.KEY") if f.name != "SYS0000D.KEY"]
    if not key_files:
        key_files = list(work_path.glob("*.KEY"))
    if not key_files:
        return {"ok": False, "error": "No .KEY file produced."}

    # Return the one matching our system ID if possible
    target = f"SYS{int(system_id, 16):05X}.KEY"
    exact = work_path / target
    if exact.exists():
        return {"ok": True, "key_file": exact}
    return {"ok": True, "key_file": key_files[0]}

def cleanup_later(path, delay=120):
    def _rm():
        time.sleep(delay)
        shutil.rmtree(path, ignore_errors=True)
    threading.Thread(target=_rm, daemon=True).start()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    ok, result = validate_system_id(request.form.get("system_id", ""))
    if not ok:
        return jsonify({"ok": False, "error": result}), 400

    work_path = WORK_DIR / uuid.uuid4().hex
    work_path.mkdir(parents=True)

    res = run_skeygen(work_path, result)
    if not res["ok"]:
        cleanup_later(work_path)
        return jsonify(res), 500

    key_file = res["key_file"]

    @after_this_request
    def _cleanup(response):
        cleanup_later(work_path)
        return response

    return send_file(str(key_file), as_attachment=True,
                     download_name=key_file.name,
                     mimetype="application/octet-stream")

@app.route("/health")
def health():
    return jsonify({
        "dosbox_x": shutil.which("dosbox-x") is not None,
        "skeygen_exe": (EXE_DIR / "SKEYGEN.EXE").exists(),
        "ready": True,
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
