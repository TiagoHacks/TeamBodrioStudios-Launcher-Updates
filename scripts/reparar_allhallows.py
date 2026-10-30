#!/usr/bin/env python3
"""Reemplaza un Allhallows con JSON inválido por la versión Fabric 1.21.1 más reciente que pase validación; o lo retira."""
import hashlib, io, json, re, urllib.parse, urllib.request, zipfile
from datetime import datetime, timezone
from pathlib import Path

path = Path("modos/manifest.json")
data = json.loads(path.read_text(encoding="utf-8-sig"))
mode = next(m for m in data["modes"] if m["id"] == "murder-mystery")
matches = [f for f in mode["files"] if f["name"].lower().startswith("allhallows-") and f["kind"] == "mod"]
if len(matches) != 1:
    raise RuntimeError(f"Se esperaba un único Allhallows, encontrados {len(matches)}")
old = matches[0]
def api(url):
    request = urllib.request.Request(url, headers={"User-Agent":"TeamBodrioStudios-Validator/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()
def valid_file(f):
    binary = api(f["url"])
    if hashlib.sha512(binary).hexdigest().lower() != f["sha512"].lower():
        raise ValueError("SHA512 incorrecto")
    with zipfile.ZipFile(io.BytesIO(binary)) as jar:
        raw = jar.read("fabric.mod.json")
        obj = json.loads(raw)
        if not isinstance(obj, dict) or not obj.get("id"):
            raise ValueError("Metadata sin id")
        return obj["id"]

query = urllib.parse.urlencode({"loaders":json.dumps(["fabric"]),"game_versions":json.dumps(["1.21.1"])})
versions = json.loads(api("https://api.modrinth.com/v2/project/CnV6ArGR/version?" + query))
versions.sort(key=lambda v:v.get("date_published", ""),reverse=True)
replacement = None
for v in versions:
    if v.get("id") == "BZugIYq3":
        continue
    for f in sorted(v.get("files",[]), key=lambda x:not x.get("primary", False)):
        if not f.get("filename", "").lower().endswith(".jar"):
            continue
        h = f.get("hashes", {}).get("sha512", "")
        if not re.fullmatch("[a-fA-F0-9]{128}",h): continue
        candidate={"kind":"mod","name":f["filename"],"url":f["url"],"sha512":h.lower(),"size":f["size"]}
        try:
            modid = valid_file(candidate)
        except Exception as exc:
            print(f"DESCARTADA {f['filename']}: {exc}",flush=True)
            continue
        if modid != "allhallows":
            print(f"DESCARTADA {f['filename']}: id de mod inesperado {modid}",flush=True)
            continue
        replacement = candidate
        print(f"ALTERNATIVA VALIDA: {candidate['name']} ({v['id']})",flush=True)
        break
    if replacement: break

index = mode["files"].index(old)
if replacement:
    mode["files"][index] = replacement
else:
    mode["files"].pop(index)
    print("No hay alternativa valida: Allhallows retirado temporalmente del catálogo.",flush=True)

mode["revision"] = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")[:-3]
path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print(f"ACTUALIZADO: {old['name']} -> {replacement['name'] if replacement else 'RETIRADO'}",flush=True)
