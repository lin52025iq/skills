#!/usr/bin/env python3
"""从 CLM 直接生成与目标编程语言无关的测试向量。"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any, Dict, List, Optional
from clm_model import build_node_index, root_of
from symbol_table import build_symbol_table

def load_json(path: Path) -> Dict[str, Any]: return json.loads(path.read_text(encoding="utf-8"))
def make_id(source_id: str, suffix: str) -> str: return f"test.{source_id}.{suffix}"
def unwrap_ref(value: Any) -> Optional[str]: return value.get("ref") if isinstance(value,dict) and isinstance(value.get("ref"),str) else None
def unwrap_value(value: Any) -> Any:
    if not isinstance(value,dict): return value
    if "literal" in value: return value["literal"]
    if isinstance(value.get("enum"),dict): return value["enum"].get("value")
    if "null" in value: return None
    if isinstance(value.get("set"),list): return [unwrap_value(x) for x in value["set"]]
    if "ref" in value: return {"ref": value["ref"]}
    return value

def enum_values_for_subject(subject:str,nodes:Dict[str,Dict[str,Any]],symbols:Dict[str,Dict[str,Any]])->Optional[List[Any]]:
    symbol=symbols.get(subject); type_id=symbol.get("type") if symbol else None; enum=nodes.get(type_id) if isinstance(type_id,str) else None
    return enum.get("values") if enum and enum.get("kind")=="enum" and isinstance(enum.get("values"),list) else None

def v02_rule_vectors(rule,nodes,symbols):
    expr=rule.get("expression"); rid=rule["id"]; out=[]
    if not isinstance(expr,dict): return out
    op=expr.get("op")
    if op in {"in","not_in"}:
        subject=unwrap_ref(expr.get("left")); values=unwrap_value(expr.get("right"))
        if isinstance(subject,str) and isinstance(values,list):
            for i,item in enumerate(values,1):
                expected=op=="in"; out.append({"id":make_id(rid,f"declared.{i}"),"source_semantic_id":rid,"kind":"rule_positive" if expected else "rule_negative","given":{subject:item},"when":None,"expect":{"rule_result":expected}})
            universe=enum_values_for_subject(subject,nodes,symbols)
            if universe:
                declared=set(values)
                for i,item in enumerate([v for v in universe if v not in declared],1):
                    expected=op=="not_in"; out.append({"id":make_id(rid,f"enum-counterexample.{i}"),"source_semantic_id":rid,"kind":"rule_positive" if expected else "rule_negative","given":{subject:item},"when":None,"expect":{"rule_result":expected}})
            return out
    if op in {"eq","ne","lt","le","gt","ge"}:
        return [{"id":make_id(rid,"typed-boundary"),"source_semantic_id":rid,"kind":"boundary_intent","given":{"subject":unwrap_ref(expr.get("left")),"operator":op,"boundary":unwrap_value(expr.get("right"))},"when":None,"expect":{"derive_around_boundary":True}}]
    if op in {"all","any","not"}:
        return [{"id":make_id(rid,"logical-combination"),"source_semantic_id":rid,"kind":"condition_assignment_intent","given":{"expression":expr},"when":None,"expect":{"generate_truth_table_subset":True}}]
    return [{"id":make_id(rid,"expression-property"),"source_semantic_id":rid,"kind":"rule_expression_intent","given":{"expression":expr},"when":None,"expect":{"evaluate_expression":True}}]

def v01_rule_vectors(rule,nodes,symbols):
    rid=rule["id"]; op=rule.get("operator"); subject=rule.get("subject"); value=rule.get("value"); out=[]
    if op in {"in","not_in"} and isinstance(subject,str) and isinstance(value,list):
        for i,item in enumerate(value,1):
            expected=op=="in"; out.append({"id":make_id(rid,f"declared.{i}"),"source_semantic_id":rid,"kind":"rule_positive" if expected else "rule_negative","given":{subject:item},"when":None,"expect":{"rule_result":expected}})
        return out
    return out

def rule_vectors(rule,nodes,symbols): return v02_rule_vectors(rule,nodes,symbols) if isinstance(rule.get("expression"),dict) else v01_rule_vectors(rule,nodes,symbols)
def assignment_map(items:Any)->Dict[str,Any]:
    out={}
    for item in items or []:
        if isinstance(item,dict):
            target=unwrap_ref(item.get("target"))
            if target: out[target]=unwrap_value(item.get("value"))
    return out

def scenario_vector(s):
    typed=all(isinstance(x,dict) and "target" in x and "value" in x for x in (s.get("given",[]) or [])+(s.get("then",[]) or []))
    return {"id":make_id(s["id"],"example"),"source_semantic_id":s["id"],"kind":"scenario","given":assignment_map(s.get("given")) if typed else s.get("given",[]),"when":{"behaviors":s.get("when",[])},"expect":assignment_map(s.get("then")) if typed else s.get("then",s.get("expect",[]))}
def transition_vectors(n):
    if n.get("kind")=="transition": return [{"id":make_id(n["id"],"allowed"),"source_semantic_id":n["id"],"kind":"state_transition","given":{"state":n.get("from")},"when":{"trigger":n.get("trigger"),"guard":n.get("guard")},"expect":{"state":n.get("to")}}]
    if n.get("kind")=="forbidden_transition": return [{"id":make_id(n["id"],"forbidden"),"source_semantic_id":n["id"],"kind":"forbidden_state_transition","given":{"state":n.get("from")},"when":{"target_state":n.get("to")},"expect":{"allowed":False}}]
    return []
def constraint_vectors(n):
    if n.get("kind") in {"invariant","postcondition","precondition","constraint"} and n.get("expression") is not None: return [{"id":make_id(n["id"],"property"),"source_semantic_id":n["id"],"kind":"property_intent","given":{},"when":None,"expect":{"property":n.get("expression")}}]
    if n.get("kind")=="temporal": return [{"id":make_id(n["id"],"temporal"),"source_semantic_id":n["id"],"kind":"temporal_integration_intent","given":{},"when":{"trigger":n.get("trigger")},"expect":{"eventually":n.get("requirement"),"time_bound":n.get("time_bound")}}]
    return []
def generate(clm):
    nodes=build_node_index(clm); symbols=build_symbol_table(clm); vectors=[]
    for n in nodes.values():
        k=n.get("kind")
        if k=="rule": vectors.extend(rule_vectors(n,nodes,symbols))
        elif k=="scenario": vectors.append(scenario_vector(n))
        elif k in {"transition","forbidden_transition"}: vectors.extend(transition_vectors(n))
        elif k in {"invariant","postcondition","precondition","constraint","temporal"}: vectors.extend(constraint_vectors(n))
    return {"source_clm":root_of(clm).get("id"),"test_vector_version":"0.2","vectors":vectors,"warnings":[] if vectors else ["当前 CLM 中没有生成任何测试向量。"]}
def main():
    p=argparse.ArgumentParser(); p.add_argument("clm",type=Path); p.add_argument("--output",type=Path); a=p.parse_args(); r=generate(load_json(a.clm)); text=json.dumps(r,ensure_ascii=False,indent=2); a.output.write_text(text+"\n",encoding="utf-8") if a.output else print(text); return 0
if __name__=="__main__": raise SystemExit(main())
