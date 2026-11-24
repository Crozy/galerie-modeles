"""Galerie de modèles 3D : sert les .glb d'un dossier en lecture seule, avec une page de visualisation.

Aucune dépendance : bibliothèque standard Python uniquement.
  MODELS_DIR  dossier des modèles (défaut : /models)
  PORT        port d'écoute (défaut : 8090)
"""

import json
import os
import struct
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

MODELS_DIR = Path(os.environ.get("MODELS_DIR", "/models")).resolve()
STATIC_DIR = (Path(__file__).parent / "static").resolve()
PORT = int(os.environ.get("PORT", "8090"))

_cache: dict[Path, tuple[float, dict]] = {}


def glb_info(path: Path) -> dict:
    """Lit l'en-tête JSON d'un .glb : triangles, animations, textures (mis en cache par date de modif)."""
    mtime = path.stat().st_mtime
    hit = _cache.get(path)
    if hit and hit[0] == mtime:
        return hit[1]
    info = {"triangles": None, "animations": [], "textures": 0, "error": None}
    try:
        with path.open("rb") as f:
            magic, _version, _length = struct.unpack("<4sII", f.read(12))
            chunk_len, chunk_type = struct.unpack("<I4s", f.read(8))
            if magic != b"glTF" or chunk_type != b"JSON":
                raise ValueError("pas un fichier glb valide")
            gltf = json.loads(f.read(chunk_len))
        accessors = gltf.get("accessors", [])
        meshes = gltf.get("meshes", [])
        # triangles par mesh, multipliés par le nombre de nœuds qui l'utilisent
        per_mesh = []
        for mesh in meshes:
            tris = 0
            for prim in mesh.get("primitives", []):
                if prim.get("mode", 4) != 4:
                    continue
                idx = prim.get("indices")
                count = accessors[idx]["count"] if idx is not None else accessors[prim["attributes"]["POSITION"]]["count"]
                tris += count // 3
            per_mesh.append(tris)
        uses = [0] * len(meshes)
        for node in gltf.get("nodes", []):
            if "mesh" in node:
                uses[node["mesh"]] += 1
        info["triangles"] = sum(t * max(u, 1) for t, u in zip(per_mesh, uses))
        info["animations"] = [a.get("name") or f"animation {i + 1}" for i, a in enumerate(gltf.get("animations", []))]
        info["textures"] = len(gltf.get("images", []))
    except Exception as e:  # un fichier abîmé ne doit pas casser la liste
        info["error"] = str(e)
    _cache[path] = (mtime, info)
    return info


def list_models() -> list[dict]:
    models = []
    for p in sorted(MODELS_DIR.rglob("*.glb")):
        if any(part.startswith(".") for part in p.relative_to(MODELS_DIR).parts):
            continue
        st = p.stat()
        rel = p.relative_to(MODELS_DIR).as_posix()
        models.append({
            "path": rel,
            "name": p.stem,
            "folder": p.parent.relative_to(MODELS_DIR).as_posix() if p.parent != MODELS_DIR else "",
            "size": st.st_size,
            "modified": st.st_mtime,
            **glb_info(p),
        })
    return models


def safe_path(root: Path, rel: str) -> Path | None:
    """Chemin sous `root`, ou None s'il en sort (../, liens…)."""
    p = (root / rel).resolve()
    return p if p.is_relative_to(root) and p.is_file() else None


class Handler(SimpleHTTPRequestHandler):
    server_version = "GalerieModeles"

    def do_GET(self):
        self.route(head=False)

    def do_HEAD(self):
        self.route(head=True)

    def route(self, head: bool):
        path = unquote(urlsplit(self.path).path)
        if path == "/api/models":
            body = json.dumps(list_models()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if not head:
                self.wfile.write(body)
            return
        if path.startswith("/models/"):
            target = safe_path(MODELS_DIR, path[len("/models/"):])
        elif path == "/":
            target = STATIC_DIR / "index.html"
        else:
            target = safe_path(STATIC_DIR, path.lstrip("/"))
        if not target:
            self.send_error(404, "Introuvable")
            return
        self.send_file(target, head)

    def send_file(self, target: Path, head: bool):
        ctype = "model/gltf-binary" if target.suffix == ".glb" else self.guess_type(str(target))
        size = target.stat().st_size
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(size))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        if not head:
            with target.open("rb") as f:
                self.copyfile(f, self.wfile)


if __name__ == "__main__":
    if not MODELS_DIR.is_dir():
        raise SystemExit(f"Dossier des modèles introuvable : {MODELS_DIR}")
    print(f"Galerie : http://0.0.0.0:{PORT}  (modèles : {MODELS_DIR})", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
