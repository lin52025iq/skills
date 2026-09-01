#!/usr/bin/env python3
"""计算 CLM 的稳定语义哈希，用于变更集前置条件与漂移检测。"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any, Dict

VOLATILE_KEYS={"evidence","evidence_refs","confidence","notes"}

def load_json(path:Path)->Dict[str,Any]: return json.loads(path.read_text(encoding="utf-8"))
def normalize(value:Any)->Any:
    if isinstance(value,dict):
        return {k:normalize(v) for k,v in sorted(value.items()) if k not in VOLATILE_KEYS}
    if isinstance(value,list): return [normalize(v) for v in value]
    return value

def semantic_hash(document:Dict[str,Any])->str:
    root=document.get("clm",document)
    data=json.dumps(normalize(root),ensure_ascii=False,sort_keys=True,separators=(",",":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()
def main():
    p=argparse.ArgumentParser(description="计算 CLM semantic hash"); p.add_argument("clm",type=Path); a=p.parse_args(); h=semantic_hash(load_json(a.clm)); print(json.dumps({"semantic_hash":h},ensure_ascii=False)); return 0
if __name__=="__main__": raise SystemExit(main())
