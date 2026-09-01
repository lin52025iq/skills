#!/usr/bin/env python3
"""原子应用 Semantic Change Set v0.2。"""
from __future__ import annotations
import argparse, copy, json
from pathlib import Path
from typing import Any, Dict, List, Tuple
from apply_semantic_patch import PatchError, apply_patch
from clm_model import find_node, root_of
from semantic_hash import semantic_hash

class ChangeSetError(ValueError): pass
def load_json(path:Path)->Dict[str,Any]: return json.loads(path.read_text(encoding="utf-8"))
def replace_reference(value:Any,old:str,new:str)->int:
    count=0
    if isinstance(value,dict):
        for k,child in list(value.items()):
            if isinstance(child,str) and child==old: value[k]=new; count+=1
            else: count+=replace_reference(child,old,new)
    elif isinstance(value,list):
        for i,child in enumerate(value):
            if isinstance(child,str) and child==old: value[i]=new; count+=1
            else: count+=replace_reference(child,old,new)
    return count
def apply_relation(model,op,remove):
    root=root_of(model); relation={"source":op.get("source"),"relation":op.get("relation"),"target":op.get("target")}; rels=root.setdefault("relations",[])
    if remove:
        before=len(rels); root["relations"]=[x for x in rels if not all(x.get(k)==v for k,v in relation.items())]
        if len(root["relations"])==before: raise ChangeSetError(f"待移除关系不存在: {relation}")
        return {"type":"relation_removed",**relation}
    if any(all(x.get(k)==v for k,v in relation.items()) for x in rels): return {"type":"relation_unchanged",**relation}
    rels.append(relation); return {"type":"relation_added",**relation}
def apply_one(model,op):
    operation=op.get("operation")
    if operation in {"ADD_RELATION","REMOVE_RELATION"}:
        result=copy.deepcopy(model); return result,apply_relation(result,op,operation=="REMOVE_RELATION")
    if operation=="REPLACE_REFERENCE":
        target_id=op.get("target_semantic_id"); new_ref=op.get("after") or op.get("value"); old_ref=op.get("before")
        if not all(isinstance(x,str) for x in (target_id,new_ref,old_ref)): raise ChangeSetError("REPLACE_REFERENCE 需要 target_semantic_id/before/after")
        result=copy.deepcopy(model); _,node=find_node(result,target_id); count=replace_reference(node,old_ref,new_ref)
        if count==0: raise ChangeSetError(f"节点 {target_id} 中不存在引用 {old_ref}")
        return result,{"type":"reference_replaced","id":target_id,"before":old_ref,"after":new_ref,"count":count}
    patch=dict(op); patch["patch_id"]=op.get("operation_id") or f"patch.change-set.{str(operation).lower()}"
    try: updated,raw=apply_patch(model,patch)
    except PatchError as exc: raise ChangeSetError(str(exc)) from exc
    return updated,{"type":"patch_operation","operation":operation,"changes":raw.get("changes",[])}
def apply_change_set(document,change_set):
    cs=change_set.get("semantic_change_set",change_set); working=copy.deepcopy(document); root=root_of(working)
    expected_version=cs.get("base_model_version")
    if expected_version is not None and str(root.get("version"))!=str(expected_version): raise ChangeSetError(f"模型版本不匹配：期望 {expected_version}，实际 {root.get('version')}")
    expected_hash=cs.get("base_semantic_hash")
    actual_hash=semantic_hash(working)
    if expected_hash is not None and expected_hash!=actual_hash: raise ChangeSetError(f"语义哈希不匹配：期望 {expected_hash}，实际 {actual_hash}")
    diffs=[]; changed=[]
    for i,op in enumerate(cs.get("operations",[])):
        try: working,diff=apply_one(working,op)
        except Exception as exc: raise ChangeSetError(f"第 {i+1} 个操作失败（{op.get('operation')}）：{exc}") from exc
        diffs.append({"index":i,"operation_id":op.get("operation_id"),**diff})
        for c in (op.get("target_semantic_id"),op.get("source"),op.get("target")):
            if isinstance(c,str): changed.append(c)
        after=op.get("after")
        if op.get("operation")=="ADD_NODE" and isinstance(after,dict) and isinstance(after.get("id"),str): changed.append(after["id"])
    return working,{"change_set_id":cs.get("change_set_id"),"intent":cs.get("intent"),"behavior_change_level":cs.get("behavior_change_level"),"base_semantic_hash":actual_hash,"result_semantic_hash":semantic_hash(working),"changed_semantic_ids":list(dict.fromkeys(changed)),"operations":diffs,"verification_required":cs.get("verification_required",[])}
def main():
    p=argparse.ArgumentParser(); p.add_argument("clm",type=Path); p.add_argument("change_set",type=Path); p.add_argument("-o","--output",type=Path,required=True); p.add_argument("--diff-output",type=Path); a=p.parse_args()
    try: updated,diff=apply_change_set(load_json(a.clm),load_json(a.change_set))
    except (OSError,json.JSONDecodeError,ChangeSetError) as exc: print(json.dumps({"ok":False,"error":str(exc)},ensure_ascii=False,indent=2)); return 1
    a.output.write_text(json.dumps(updated,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); text=json.dumps(diff,ensure_ascii=False,indent=2)
    a.diff_output.write_text(text+"\n",encoding="utf-8") if a.diff_output else print(text); return 0
if __name__=="__main__": raise SystemExit(main())
