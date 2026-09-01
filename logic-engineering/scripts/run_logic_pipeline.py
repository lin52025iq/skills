#!/usr/bin/env python3
"""运行逻辑工程统一流水线。

流程：
1. 自动识别 CLM 版本并选择 schema
2. 校验原始 CLM
3. 可选应用 Semantic Patch 或原子 Semantic Change Set
4. 校验更新后的 CLM
5. 分析修改影响范围
6. 生成 Symbol Table
7. 生成中文逻辑投影
8. 从 CLM 独立生成语言无关测试向量
9. 可选编译 IIR v0.2
10. 校验 IIR v0.2
11. 编译 Target Test Plan
12. 可选生成 Go 代码骨架
13. 校验 generated manifest / 漂移
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
from typing import Any, Dict, List
SCRIPT_DIR=Path(__file__).resolve().parent; SCHEMA_DIR=SCRIPT_DIR.parent/"schemas"
def run(cmd:List[str],label:str)->str:
    p=subprocess.run(cmd,text=True,capture_output=True)
    if p.returncode!=0:
        print(json.dumps({"ok":False,"stage":label,"command":cmd,"stdout":p.stdout,"stderr":p.stderr},ensure_ascii=False,indent=2)); raise SystemExit(p.returncode)
    if p.stdout.strip(): print(f"[{label}]\n{p.stdout.strip()}")
    return p.stdout
def load_json(path:Path)->Dict[str,Any]: return json.loads(path.read_text(encoding="utf-8"))
def detect_schema(path:Path)->Path:
    root=load_json(path).get("clm",load_json(path)); version=str(root.get("version","0.1")); return SCHEMA_DIR/("clm-v0.2.schema.json" if version in {"0.2","2","2.0"} else "clm-v0.1.schema.json")
def patch_changed_ids(path:Path)->List[str]:
    p=load_json(path); p=p.get("semantic_patch",p); t=p.get("target_semantic_id") or p.get("target"); return [t] if isinstance(t,str) else []
def change_set_changed_ids(path:Path)->List[str]:
    cs=load_json(path); cs=cs.get("semantic_change_set",cs); ids=[]
    for op in cs.get("operations",[]) or []:
        if not isinstance(op,dict): continue
        for key in ("target_semantic_id","source","target"):
            v=op.get(key)
            if isinstance(v,str): ids.append(v)
        after=op.get("after")
        if op.get("operation")=="ADD_NODE" and isinstance(after,dict) and isinstance(after.get("id"),str): ids.append(after["id"])
    return list(dict.fromkeys(ids))
def validate_model(path:Path,schema:Path,label:str): run([sys.executable,str(SCRIPT_DIR/"validate_clm.py"),str(path),"--schema",str(schema)],label)
def main()->int:
    ap=argparse.ArgumentParser(description="运行逻辑工程统一流水线"); ap.add_argument("clm",type=Path)
    mut=ap.add_mutually_exclusive_group(); mut.add_argument("--patch",type=Path); mut.add_argument("--change-set",type=Path)
    ap.add_argument("--target-profile",type=Path); ap.add_argument("--generate-go",action="store_true",help="IIR 校验通过后生成 Go v0.1 骨架")
    ap.add_argument("--output-dir",type=Path,default=Path(".logic-engineering-output")); ap.add_argument("--schema",type=Path); a=ap.parse_args()
    out=a.output_dir; out.mkdir(parents=True,exist_ok=True); working=a.clm; schema=a.schema or detect_schema(working); validate_model(working,schema,"校验原始 CLM")
    impact=None; changed=[]; semantic_diff=None
    if a.patch or a.change_set:
        updated=out/"updated.clm.json"; semantic_diff=out/"semantic-diff.json"
        if a.patch:
            changed=patch_changed_ids(a.patch); run([sys.executable,str(SCRIPT_DIR/"apply_semantic_patch.py"),str(working),str(a.patch),"-o",str(updated),"--diff-output",str(semantic_diff)],"应用语义补丁")
        else:
            changed=change_set_changed_ids(a.change_set); run([sys.executable,str(SCRIPT_DIR/"apply_semantic_change_set.py"),str(working),str(a.change_set),"-o",str(updated),"--diff-output",str(semantic_diff)],"应用语义变更集")
        working=updated; schema=a.schema or detect_schema(working); validate_model(working,schema,"校验更新后的 CLM")
        if changed:
            impact=out/"impact-analysis.json"; run([sys.executable,str(SCRIPT_DIR/"analyze_impact.py"),str(working),*changed,"--output",str(impact)],"分析语义影响")
    symbols=out/"symbol-table.json"; run([sys.executable,str(SCRIPT_DIR/"symbol_table.py"),str(working),"-o",str(symbols)],"生成 Symbol Table")
    human=out/"human-logic.md"; run([sys.executable,str(SCRIPT_DIR/"render_human_logic.py"),str(working),"-o",str(human)],"生成中文逻辑投影")
    vectors=out/"test-vectors.json"; run([sys.executable,str(SCRIPT_DIR/"generate_test_vectors.py"),str(working),"--output",str(vectors)],"生成测试向量")
    iir=None; target_tests=None; generated=None
    if a.target_profile:
        iir=out/"implementation.iir.json"; run([sys.executable,str(SCRIPT_DIR/"compile_iir.py"),str(working),str(a.target_profile),"-o",str(iir)],"编译 IIR v0.2")
        run([sys.executable,str(SCRIPT_DIR/"validate_iir.py"),str(iir),"--schema",str(SCHEMA_DIR/"iir-v0.2.schema.json")],"校验 IIR v0.2")
        target_tests=out/"target-test-plan.json"; run([sys.executable,str(SCRIPT_DIR/"compile_target_tests.py"),str(vectors),str(iir),"-o",str(target_tests)],"编译目标测试计划")
        if a.generate_go:
            generated=out/"generated-go"; run([sys.executable,str(SCRIPT_DIR/"generate_go.py"),str(iir),str(target_tests),"-o",str(generated)],"生成 Go v0.1")
            run([sys.executable,str(SCRIPT_DIR/"verify_generated_manifest.py"),str(generated)],"校验生成产物完整性")
    elif a.generate_go:
        print(json.dumps({"ok":False,"error":"--generate-go 需要 --target-profile"},ensure_ascii=False)); return 2
    print(json.dumps({"ok":True,"schema":str(schema),"clm":str(working),"symbol_table":str(symbols),"human_logic":str(human),"semantic_diff":str(semantic_diff) if semantic_diff else None,"impact_analysis":str(impact) if impact else None,"test_vectors":str(vectors),"iir":str(iir) if iir else None,"target_test_plan":str(target_tests) if target_tests else None,"generated_go":str(generated) if generated else None},ensure_ascii=False,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
