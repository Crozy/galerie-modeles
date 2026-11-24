# Galerie de modèles

Petite galerie web pour visualiser les modèles 3D `.glb` d'un dossier : liste, aperçu 3D, animations,
triangles, taille, dimensions. Lecture seule. Python standard + [model-viewer](https://modelviewer.dev) (inclus dans `static/vendor`).

## En local (test)

```
MODELS_DIR=/chemin/vers/modeles python3 server.py
```
puis http://localhost:8090

## Sur le serveur (Docker)

```
git pull
docker compose up -d --build
```
Le dossier servi est `/mnt/Data2/blender-mcp/exports` (modifiable via la variable `MODELS_DIR`).
Accessible depuis le réseau local sur `http://<ip-du-serveur>:8090` (ne pas rediriger ce port sur la box).
