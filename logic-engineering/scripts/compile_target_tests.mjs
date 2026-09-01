#!/usr/bin/env node
import {readJson,writeJson} from './lib/model.mjs';

function findUseCaseByBehavior(root,behavior){return (root.use_cases??[]).find(u=>(u.semantic_refs??[]).includes(behavior)||u.semantic_id===behavior);}
function findUseCaseByGuard(root,rule){return (root.use_cases??[]).find(u=>(u.guards??[]).some(g=>g.semantic_ref===rule));}
function guardFor(root,rule){for(const u of root.use_cases??[]){const g=(u.guards??[]).find(x=>x.semantic_ref===rule);if(g)return {useCase:u,guard:g};}return null;}

function compile(vectorsDoc,iirDoc){
  const root=iirDoc.iir??iirDoc,cases=[];
  for(const v of vectorsDoc.vectors??[]){
    const item={id:v.id,source_semantic_id:v.source_semantic_id,kind:v.kind,given:v.given??{},when:v.when??null,expect:v.expect??{},target_kind:null,target_id:null,use_case_id:null,fake_dependencies:[],required_input_refs:[],fixture_constraints:[],unsupported:[]};
    if(['rule_positive','rule_negative','boundary_intent','condition_assignment_intent','rule_expression_intent'].includes(v.kind)){
      const hit=guardFor(root,v.source_semantic_id);
      if(hit){item.target_kind='guard';item.target_id=hit.guard.semantic_ref;item.use_case_id=hit.useCase.id;item.required_input_refs=hit.useCase.input_refs??[];item.fixture_constraints=[hit.guard.expression].filter(Boolean);item.fake_dependencies=hit.useCase.dependencies??[];}
      else item.unsupported.push('没有找到引用该 Rule 的 IIR Guard');
    }else if(v.kind==='scenario'){
      const behavior=(v.when?.behaviors??[])[0],uc=findUseCaseByBehavior(root,behavior);
      if(uc){item.target_kind='use_case';item.target_id=uc.id;item.use_case_id=uc.id;item.required_input_refs=uc.input_refs??[];item.fixture_constraints=(uc.guards??[]).map(g=>g.expression).filter(Boolean);item.fake_dependencies=uc.dependencies??[];}
      else item.unsupported.push(`无法定位 Scenario 对应 Use Case: ${behavior??'<missing>'}`);
    }else if(v.kind==='state_transition'){
      item.target_kind='state_transition';item.unsupported.push('状态迁移执行器尚未生成，保留测试计划');
    }else{
      item.unsupported.push(`当前 Target Test Compiler 尚未实现 kind=${v.kind}`);
    }
    cases.push(item);
  }
  return {target_test_plan:{version:'0.2',target_profile:root.target_profile?.id??null,source_clm:root.source_clm_id,source_semantic_hash:root.source_semantic_hash,cases,summary:{total:cases.length,executable:cases.filter(x=>x.unsupported.length===0).length,unsupported:cases.filter(x=>x.unsupported.length>0).length}}};
}

const [vectorsFile,iirFile,...args]=process.argv.slice(2);const oi=args.indexOf('-o')>=0?args.indexOf('-o'):args.indexOf('--output');const output=oi>=0?args[oi+1]:null;
if(!vectorsFile||!iirFile||!output){console.error('usage: node compile_target_tests.mjs test-vectors.json iir.json -o target-test-plan.json');process.exit(2);}
try{writeJson(output,compile(readJson(vectorsFile),readJson(iirFile)));console.log(JSON.stringify({ok:true,output},null,2));}catch(e){console.error(JSON.stringify({ok:false,error:e.message},null,2));process.exit(1);}
