#!/usr/bin/env python3
"""Publica los tres mods de temporada en Murder Mystery, validando JAR y dependencias."""
from __future__ import annotations
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import io
import json
import re
import urllib.parse
import urllib.request
import zipfile

MANIFEST = Path("modos/manifest.json")
MC = "1.21.1"
LOADER = "fabric"
VERSIONS = {
    "lUJ6xjps": "Macaw's Holidays 1.1.2",
    "27dwvC2t": "Real Events 1.5.9",
    "y17C7oXH": "Furniture Mod Tools Refurbished 1.0.0",
}
EXTRA_OFFICIAL_JARS = [
    (
        "refurbished_furniture-fabric-1.21.1-1.0.22-signed.jar",
        "https://github.com/MrCrayfish/MrCrayfishFurnitureMod-Refurbished/releases/download/v1.21.1-1.0.22/refurbished_furniture-fabric-1.21.1-1.0.22-signed.jar",
    ),
    (
        "framework-fabric-1.21.1-0.13.20-signed.jar",
        "https://github.com/MrCrayfish/Framework/releases/download/v1.21.1-0.13.20/framework-fabric-1.21.1-0.13.20-signed.jar",
    ),
]
URL_ROOT = "https://api.modrinth.com/v2/"
CLIENT_MOD_IDS = {
    "fabric-api", "carpet", "modmenu", "invmove", "sound_physics_remastered",
    "ratatouille", "placeholder-api", "wathe", "cloth-config", "voicechat",
    "teambodrio_interfaz", "iris", "sodium", "tbs_ui_murdermys",
    "cpa", "rainbowchristmas", "player_animation_library", "architectury",
}
BUILTIN = {"minecraft", "fabricloader", "java", "fabric", "fabric-api-base"}
HEX512 = re.compile(r"^[a-fA-F0-9]{128}$")
CDN_PROJECT = re.compile(r"cdn\.modrinth\.com/data/([^/]+)/", re.I)

def readurl(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "TeamBodrioStudios/RC13 dependency validator (github.com/TiagoHacks)"}
    )
    with urllib.request.urlopen(req, timeout=65) as stream:
        return stream.read()

def api(name, params=None):
    url = URL_ROOT + name
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return json.loads(readurl(url))

def supports(v):
    return MC in v.get("game_versions", []) and LOADER in v.get("loaders", [])

def select(v):
    jars = [f for f in v.get("files", [])
            if f.get("filename", "").lower().endswith(".jar")
            and not f.get("filename", "").lower().endswith(("-sources.jar", "-dev.jar"))]
    if not jars:
        raise ValueError("Version sin .jar ejecutable: " + str(v.get("id")))
    f = next((x for x in jars if x.get("primary")), jars[0])
    sha = f.get("hashes", {}).get("sha512", "")
    if not HEX512.fullmatch(sha):
        raise ValueError("SHA-512 no disponible para: " + f["filename"])
    if not isinstance(f.get("size"), int) or f["size"] <= 0:
        raise ValueError("Tamaño no disponible: " + f["filename"])
    if not f.get("url", "").startswith("https://cdn.modrinth.com/"):
        raise ValueError("URL inesperada de descarga: " + f["filename"])
    return {"kind": "mod", "name": f["filename"], "url": f["url"],
            "sha512": sha.lower(), "size": f["size"]}

def inspect_jar(record):
    raw = readurl(record["url"])
    if len(raw) != record["size"] or hashlib.sha512(raw).hexdigest() != record["sha512"]:
        raise ValueError("Integridad SHA-512 o tamaño incorrectos para: " + record["name"])
    with zipfile.ZipFile(io.BytesIO(raw)) as jar:
        info = json.loads(jar.read("fabric.mod.json"))
    if not isinstance(info, dict) or not info.get("id"):
        raise ValueError("fabric.mod.json incompleto en: " + record["name"])
    dependencies = info.get("depends", {}) or {}
    if not isinstance(dependencies, dict):
        raise ValueError("Campo depends inválido en: " + record["name"])
    return info["id"], dependencies

def resolve_required(dependency):
    if dependency.get("version_id"):
        ver = api("version/" + dependency["version_id"])
        if supports(ver):
            return ver
    project = dependency.get("project_id")
    if not project:
        raise ValueError("Dependencia requerida sin project_id/version_id: " + str(dependency))
    versions = api("project/" + project + "/version",
                   {"loaders": json.dumps([LOADER]), "game_versions": json.dumps([MC])})
    versions = [v for v in versions if supports(v)]
    if not versions:
        raise ValueError("Dependencia obligatoria sin versión Fabric 1.21.1: " + project)
    versions.sort(key=lambda v: v.get("date_published", ""), reverse=True)
    return next((v for v in versions if v.get("version_type") == "release"), versions[0])

def get_loader_min(constraint):
    if isinstance(constraint, list):
        nums = [get_loader_min(x) for x in constraint]
        return max((x for x in nums if x), default=None)
    if not isinstance(constraint, str):
        return None
    match = re.search(r">=\s*(\d+)\.(\d+)\.(\d+)", constraint)
    return tuple(map(int, match.groups())) if match else None

def main():
    document = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    targets = [m for m in document["modes"] if m.get("id") == "murder-mystery"]
    if len(targets) != 1:
        raise ValueError("No se encontró un único modo Murder Mystery.")
    mode = targets[0]
    if mode["minecraftVersion"] != MC or mode["loader"].lower() != LOADER:
        raise ValueError("El modo ya no usa Fabric 1.21.1.")
    loader = tuple(map(int, mode["loaderVersion"].split(".")))
    present_projects = set()
    present_names = {f["name"].lower() for f in mode["files"]}
    for f in mode["files"]:
        found = CDN_PROJECT.search(f.get("url", ""))
        if found:
            present_projects.add(found.group(1))
    known_mods = set(CLIENT_MOD_IDS)
    queue = deque(api("version/" + vid) for vid in VERSIONS)
    additions = []
    seen_versions = set()
    requirements = []
    while queue:
        version = queue.popleft()
        if not supports(version):
            raise ValueError("Modrinth no declara Fabric 1.21.1: " + str(version.get("id")))
        project_id = version.get("project_id")
        if version["id"] in seen_versions or project_id in present_projects:
            continue
        seen_versions.add(version["id"])
        file = select(version)
        if file["name"].lower() in present_names:
            present_projects.add(project_id)
            continue
        modid, depends = inspect_jar(file)
        minimum = get_loader_min(depends.get("fabricloader", ""))
        if minimum and minimum > loader:
            raise ValueError(f"{file['name']} requiere Fabric Loader >= {'.'.join(map(str, minimum))}; catálogo usa {mode['loaderVersion']}")
        print(f"VALIDADO {file['name']} id={modid} ({file['size']} bytes), dependencies={depends}", flush=True)
        known_mods.add(modid)
        requirements.append((file["name"], depends))
        additions.append(file)
        present_projects.add(project_id)
        present_names.add(file["name"].lower())
        for dep in version.get("dependencies", []):
            if dep.get("dependency_type") != "required":
                continue
            if dep.get("project_id") in present_projects:
                continue
            queue.append(resolve_required(dep))

    # Los JAR originales del autor se alojan en GitHub Releases (no en Modrinth).
    # Calculamos SHA-512 real y leemos fabric.mod.json antes de escribir el manifiesto.
    for filename, url in EXTRA_OFFICIAL_JARS:
        if filename.lower() in present_names:
            known_mods.add("refurbished_furniture" if filename.startswith("refurbished_") else "framework")
            continue
        binary = readurl(url)
        if len(binary) < 2000:
            raise ValueError("Descarga oficial demasiado pequeña: " + filename)
        entry = {"kind": "mod", "name": filename, "url": url,
                 "sha512": hashlib.sha512(binary).hexdigest(), "size": len(binary)}
        with zipfile.ZipFile(io.BytesIO(binary)) as jar:
            metadata = json.loads(jar.read("fabric.mod.json"))
        modid = metadata.get("id")
        depends = metadata.get("depends", {}) or {}
        if modid not in ("refurbished_furniture", "framework"):
            raise ValueError("Identidad inesperada del JAR oficial: " + filename + " -> " + str(modid))
        minimum = get_loader_min(depends.get("fabricloader", ""))
        if minimum and minimum > loader:
            raise ValueError(f"{filename} requiere Fabric Loader >= {'.'.join(map(str, minimum))}")
        print(f"VALIDADO OFICIAL {filename} id={modid} ({len(binary)} bytes), dependencies={depends}", flush=True)
        known_mods.add(modid)
        requirements.append((filename, depends))
        additions.append(entry)
        present_names.add(filename.lower())

    if not additions:
        print("SIN CAMBIOS: las versiones ya están registradas.", flush=True)
        return

    # Se permiten los IDs de los módulos de Fabric API, provistos por fabric-api.
    for name, deps in requirements:
        for depname, expr in deps.items():
            if depname in BUILTIN or depname in known_mods:
                continue
            if depname.startswith("fabric-") and "fabric-api" in known_mods:
                continue
            raise ValueError(f"{name} depende de '{depname}' ({expr}), ausente en el catálogo. Requiere resolver antes de publicar.")
    before = len(mode["files"])
    mode["files"].extend(additions)
    mode["revision"] = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")[:-3]
    MANIFEST.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"ÉXITO: {before} -> {len(mode['files'])} archivos en Murder Mystery; otros modos intactos.", flush=True)

if __name__ == "__main__":
    main()
