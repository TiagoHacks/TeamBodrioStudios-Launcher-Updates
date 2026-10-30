#!/usr/bin/env python3
"""Diagnostica los metadatos de los JAR publicados en Murder Mystery sin modificar el catálogo."""
import hashlib
import io
import json
import sys
import urllib.request
import zipfile

MANIFEST = "modos/manifest.json"
with open(MANIFEST, "r", encoding="utf-8-sig") as file:
    catalog = json.load(file)
mode = next(x for x in catalog["modes"] if x["id"] == "murder-mystery")
jars = [f for f in mode["files"] if f["kind"] == "mod" and f["name"].endswith(".jar")]
failures = []
print(f"Verificando {len(jars)} mods de Murder Mystery. Revision: {mode['revision']}", flush=True)
for file in jars:
    name = file["name"]
    try:
        request = urllib.request.Request(file["url"], headers={"User-Agent": "TeamBodrioStudios-JarValidator/1.0"})
        with urllib.request.urlopen(request, timeout=65) as response:
            binary = response.read()
        actual = hashlib.sha512(binary).hexdigest()
        if actual.lower() != file["sha512"].lower():
            raise ValueError("SHA-512 distinto del manifiesto: descarga dañada o archivo sustituido")
        with zipfile.ZipFile(io.BytesIO(binary)) as jar:
            if "fabric.mod.json" in jar.namelist():
                raw = jar.read("fabric.mod.json")
                try:
                    metadata = json.loads(raw)
                except json.JSONDecodeError as exc:
                    problem = raw.splitlines()[exc.lineno - 1] if len(raw.splitlines()) >= exc.lineno else b""
                    raise ValueError(f"fabric.mod.json invalido: {exc}; linea {exc.lineno} contenido {problem[:180]!r}")
                if not isinstance(metadata, dict) or "id" not in metadata:
                    raise ValueError("fabric.mod.json sin 'id'")
                print(f"OK  {name} -> {metadata.get('id')}", flush=True)
            else:
                print(f"OK  {name} (sin fabric.mod.json en raiz)", flush=True)
    except Exception as exc:
        print(f"ERROR  {name}: {exc}", flush=True)
        failures.append(name)
print(f"RESULTADO: {len(jars) - len(failures)}/{len(jars)} JAR validos", flush=True)
if failures:
    print("MODS CON ERROR:", ", ".join(failures), flush=True)
    sys.exit(1)
