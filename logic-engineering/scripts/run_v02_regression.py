#!/usr/bin/env python3
"""运行 CLM v0.2 + IIR v0.2 核心回归 Gate。"""
from __future__ import annotations
import json, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
SCRIPTS=ROOT/"scripts"; FIXTURES=ROOT/"evals"/"fixtures"; SCHEMAS=ROOT/"schemas"
CLM_SCHEMA=SCHEMAS/"clm-v0.2.schema.json"; IIR_SCHEMA=SCHEMAS/"iir-v0.2.schema.json"

def run(args,label,expect=0):
    p=subprocess.run([sys.executable,*map(str,args)],text=True,capture_output=True)
    return {"label":label,"ok":p.returncode==expect,"returncode":p.returncode,"stdout":p.stdout[-2000:],"stderr":p.stderr[-2000:]}

def main():
    model=FIXTURES/"order-cancel.v0.2.valid.json"; profile=FIXTURES/"go-postgres.target-profile.json"; change=FIXTURES/"order-cancel.add-paid.change-set.json"
    checks=[]
    with tempfile.TemporaryDirectory(prefix="logic-v02-reg-") as td:
        out=Path(td)
        checks.append(run([SCRIPTS/"validate_clm.py",model,"--schema",CLM_SCHEMA],"CLM v0.2 合法模型通过校验"))
        checks.append(run([SCRIPTS/"render_human_logic.py",model,"-o",out/"human.md"],"中文逻辑投影"))
        checks.append(run([SCRIPTS/"generate_test_vectors.py",model,"--output",out/"tests.json"],"语言无关测试向量生成"))
        checks.append(run([SCRIPTS/"symbol_table.py",model,"-o",out/"symbols.json"],"Symbol Table"))
        checks.append(run([SCRIPTS/"semantic_hash.py",model],"Semantic Hash"))
        checks.append(run([SCRIPTS/"compile_iir.py",model,profile,"-o",out/"iir.json"],"IIR v0.2 编译"))
        if (out/"iir.json").exists():
            checks.append(run([SCRIPTS/"validate_iir.py",out/"iir.json","--schema",IIR_SCHEMA],"IIR v0.2 校验"))
            checks.append(run([SCRIPTS/"compile_target_tests.py",out/"tests.json",out/"iir.json","-o",out/"target-tests.json"],"Target Test Plan 编译"))
        checks.append(run([SCRIPTS/"apply_semantic_change_set.py",model,change,"-o",out/"changed.json","--diff-output",out/"change-diff.json"],"Change Set 原子应用"))
        if (out/"changed.json").exists():
            checks.append(run([SCRIPTS/"validate_clm.py",out/"changed.json","--schema",CLM_SCHEMA],"变更后模型重新校验"))
        checks.append(run([SCRIPTS/"run_logic_pipeline.py",model,"--change-set",change,"--target-profile",profile,"--output-dir",out/"pipeline"],"端到端流水线"))

        semantic_ok=False
        if (out/"tests.json").exists():
            data=json.loads((out/"tests.json").read_text(encoding="utf-8"))
            semantic_ok=any(v.get("kind")=="scenario" and isinstance(v.get("given"),dict) and isinstance(v.get("expect"),dict) for v in data.get("vectors",[]))
        checks.append({"label":"Typed Scenario 标准测试向量","ok":semantic_ok,"returncode":0 if semantic_ok else 1,"stdout":"","stderr":""})

        target_plan_ok=False
        if (out/"target-tests.json").exists():
            plan=json.loads((out/"target-tests.json").read_text(encoding="utf-8")).get("target_test_plan",{})
            target_plan_ok=isinstance(plan.get("cases"),list) and plan.get("summary",{}).get("total",0)>=1
        checks.append({"label":"Target Test Plan 可生成","ok":target_plan_ok,"returncode":0 if target_plan_ok else 1,"stdout":"","stderr":""})

    ok=all(x["ok"] for x in checks)
    print(json.dumps({"ok":ok,"checks":checks},ensure_ascii=False,indent=2))
    return 0 if ok else 1

if __name__=="__main__": raise SystemExit(main())
