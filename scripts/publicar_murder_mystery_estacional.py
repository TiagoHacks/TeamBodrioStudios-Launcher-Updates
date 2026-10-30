#!/usr/bin/env python3
"""Actualiza solo Murder Mystery con versiones oficiales de Modrinth y dependencias requeridas."""
import json
import re
import urllib.parse
import urllib.request
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

REPO_MANIFEST = Path("modos/manifest.json")
GAME = "1.21.1"
LOADER = "fabric"
REQUESTED_VERSION_IDS = [
    "9IYnNwkz",  # Custom Player Animations 5.9.10
    "BZugIYq3",  # Allhallows Fabric 1.3.1
    "sv49zrhJ",  # Rainbow Christmas 1.0.2
]
PROJECT_FROM_CDN = re.compile(r"cdn\.modrinth\.com/data/([^/]+)/", re.I)


def api(path, query=None):
    url = "https://api.modrinth.com/v2/" + path.lstrip("/")
    if query:
        url += "?" + urllib.parse.urlencode(query)
    req = urllib.request.Request(
        url, headers={"User-Agent": "TeamBodrioStudios-Launcher/1.0 (github.com/TiagoHacks)"}
    )
    with urllib.request.urlopen(req, timeout=35) as response:
        return json.load(response)


def compatible(version):
    return GAME in version.get("game_versions", []) and LOADER in version.get("loaders", [])


def choose_file(version):
    candidates = [
        f for f in version.get("files", [])
        if str(f.get("filename", "")).lower().endswith(".jar")
        and not str(f.get("filename", "")).lower().endswith("-sources.jar")
        and not str(f.get("filename", "")).lower().endswith("-dev.jar")
    ]
    if not candidates:
        raise ValueError("Sin JAR ejecutable en " + str(version.get("id")))
    f = next((x for x in candidates if x.get("primary")), candidates[0])
    sha512 = f.get("hashes", {}).get("sha512", "")
    if not re.fullmatch("[a-fA-F0-9]{128}", sha512):
        raise ValueError("Modrinth no entregó SHA-512 para " + str(f.get("filename")))
    size = f.get("size")
    if not isinstance(size, int) or size <= 0:
        raise ValueError("Modrinth no entregó tamaño válido para " + str(f.get("filename")))
    url = f.get("url", "")
    if not url.startswith("https://"):
        raise ValueError("Se esperaba URL HTTPS del JAR")
    return {"kind": "mod", "name": f["filename"], "url": url, "sha512": sha512.lower(), "size": size}


def resolve_required(dep):
    if dep.get("version_id"):
        version = api("version/" + dep["version_id"])
        if compatible(version):
            return version
    project_id = dep.get("project_id")
    if not project_id:
        raise ValueError("Dependencia requerida sin proyecto: " + str(dep))
    versions = api("project/" + project_id + "/version", {
        "loaders": json.dumps([LOADER]),
        "game_versions": json.dumps([GAME]),
    })
    versions = [v for v in versions if compatible(v)]
    if not versions:
        raise ValueError("No existe dependencia Fabric 1.21.1 para: " + project_id)
    return next((v for v in versions if v.get("version_type") == "release"), versions[0])


def main():
    data = json.loads(REPO_MANIFEST.read_text(encoding="utf-8-sig"))
    selected = [m for m in data["modes"] if m.get("id") == "murder-mystery"]
    if len(selected) != 1:
        raise ValueError("No existe un modo único 'murder-mystery'")
    mode = selected[0]
    if mode.get("minecraftVersion") != GAME or mode.get("loader", "").lower() != LOADER:
        raise ValueError("El modo dejó de ser Minecraft 1.21.1 Fabric. No modificar.")
    files = mode["files"]
    before = len(files)
    installed_ids = set()
    for f in files:
        match = PROJECT_FROM_CDN.search(f.get("url", ""))
        if match:
            installed_ids.add(match.group(1))
    queued = deque([api("version/" + v) for v in REQUESTED_VERSION_IDS])
    discovered = set()
    new_files = []
    while queued:
        version = queued.popleft()
        vid = version.get("id")
        project_id = version.get("project_id")
        if vid in discovered or project_id in installed_ids:
            continue
        if not compatible(version):
            raise ValueError(f"{vid} no es compatible con Minecraft {GAME} {LOADER}")
        discovered.add(vid)
        chosen = choose_file(version)
        if any(f.get("name", "").lower() == chosen["name"].lower() for f in files + new_files):
            installed_ids.add(project_id)
            continue
        new_files.append(chosen)
        installed_ids.add(project_id)
        print("Agregando:", chosen["name"], chosen["size"], "bytes")
        for dep in version.get("dependencies", []):
            if dep.get("dependency_type") != "required":
                continue
            if dep.get("project_id") in installed_ids:
                continue
            match = resolve_required(dep)
            if match.get("project_id") not in installed_ids:
                queued.append(match)
    if not new_files:
        print("Sin cambios: ya están registradas las versiones requeridas.")
        return
    files.extend(new_files)
    mode["revision"] = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")[:-3]
    REPO_MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {before} -> {len(files)} archivos en Murder Mystery; restantes modos intactos.")
    print("Aviso: Allhallows y Rainbow Christmas son mods de cliente y servidor; deben instalarse en exaroton.")


if __name__ == "__main__":
    main()
