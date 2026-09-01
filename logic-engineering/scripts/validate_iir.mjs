#!/usr/bin/env node
import {readJson} from './lib/model.mjs';

function isBlocking(item){return typeof item==='string'||item?.severity==='blocking'||item?.blocking===true;}
function validate(document){
  const root=document.iir??document,errors=[],warnings=[];
  if(String(root.version)!=='0.2')errors.push({code:'IIR_VERSION',message:'IIR version 必须为 0.2'});
  if(!root.domain_types?.entities||!Array.isArray(root.runtime_bindings))errors.push({code:'IIR_RUNTIME_MODEL_MISSING',message:'IIR 缺少 domain_types/runtime_bindings'});
  const deps=new Set([...(root.repository_contracts??[]),...(root.external_ports??[])].map(x=>x.id));
  for(const uc of root.use_cases??[])for(const dep of uc.dependencies??[])if(!deps.has(dep))errors.push({code:'IIR_BROKEN_DEPENDENCY',message:`${uc.id} 依赖不存在: ${dep}`});
  const trace=new Set((root.traceability??[]).map(x=>x.implementation_id));
  for(const uc of root.use_cases??[])if(!trace.has(uc.id))errors.push({code:'IIR_MISSING_TRACEABILITY',message:`${uc.id} 缺少 traceability`});

  if(root.target_profile?.persistence_generation==='explicit_mapping'){
    for(const repo of root.repository_contracts??[]){
      const mapping=repo.binding?.mapping;
      if(!mapping){errors.push({code:'IIR_PERSISTENCE_MAPPING_MISSING',message:`${repo.id} 缺少 explicit mapping`});continue;}
      if(typeof mapping.table!=='string'||!mapping.table)errors.push({code:'IIR_PERSISTENCE_TABLE_MISSING',message:`${repo.id} 缺少 table`});
      if(typeof mapping.primary_key!=='string'||!mapping.primary_key)errors.push({code:'IIR_PERSISTENCE_PRIMARY_KEY_MISSING',message:`${repo.id} 缺少 primary_key`});
      if(!mapping.columns||typeof mapping.columns!=='object'||Array.isArray(mapping.columns))errors.push({code:'IIR_PERSISTENCE_COLUMNS_MISSING',message:`${repo.id} 缺少 columns`});
      else if(mapping.primary_key&&!Object.hasOwn(mapping.columns,mapping.primary_key))errors.push({code:'IIR_PERSISTENCE_PRIMARY_KEY_UNMAPPED',message:`${repo.id} primary_key 未出现在 columns`});
    }
  }

  for(const item of root.unresolved??[]){
    if(isBlocking(item))errors.push({code:'IIR_BLOCKING_UNRESOLVED',message:typeof item==='string'?item:item.semantic_ref??item.reason});
    else warnings.push({code:'IIR_UNRESOLVED_WARNING',message:item?.semantic_ref??item?.reason});
  }
  return{valid:errors.length===0,errors,warnings};
}

const [file]=process.argv.slice(2);
if(!file){console.error('usage: node validate_iir.mjs implementation.iir.json');process.exit(2)}
try{const result=validate(readJson(file));console.log(JSON.stringify(result,null,2));process.exit(result.valid?0:1);}catch(e){console.error(JSON.stringify({valid:false,error:e.message},null,2));process.exit(2)}
