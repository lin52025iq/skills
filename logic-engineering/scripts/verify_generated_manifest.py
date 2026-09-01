#!/usr/bin/env python3
"""校验生成产物 manifest 与文件内容哈希是否一致。"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any, Dict, List


def file_hash(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main()->int:
    p=argparse.ArgumentParser(description="校验 generated manifest 与文件漂移")
    p.add_argument("generated_dir",type=Path)
    a=p.parse_args(); manifest_path=a.generated_dir/"manifest.json"
    if not manifest_path.exists():
        print(json.dumps({"valid":False,"errors":[{"code":"MANIFEST_MISSING","message":"缺少 manifest.json"}]},ensure_ascii=False)); return 1
    try: manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(json.dumps({"valid":False,"errors":[{"code":"MANIFEST_INVALID","message":str(exc)}]},ensure_ascii=False)); return 1
    errors=[]; checked=0
    for item in manifest.get("artifacts",[]) or []:
        rel=item.get("path"); expected=item.get("content_hash")
        if not isinstance(rel,str): continue
        path=a.generated_dir/rel
        if not path.exists(): errors.append({"code":"GENERATED_FILE_MISSING","path":rel}); continue
        actual=file_hash(path); checked+=1
        if expected!=actual: errors.append({"code":"GENERATED_FILE_DRIFT","path":rel,"expected":expected,"actual":actual})
    result={"valid":not errors,"checked":checked,"errors":errors,"generator":manifest.get("generator"),"source_semantic_hash":manifest.get("source_semantic_hash")}
    print(json.dumps(result,ensure_ascii=False,indent=2)); return 0 if result["valid"] else 1
if __name__=="__main__": raise SystemExit(main())
