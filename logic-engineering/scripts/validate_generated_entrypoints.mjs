#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {readJson} from './lib/model.mjs';

const [iirFile,generatedDir]=process.argv.slice(2);
if(!iirFile||!generatedDir){console.error('usage: node validate_generated_entrypoints.mjs implementation.iir.json generated-ts');process.exit(2);}

function exported(file,name){
  if(!fs.existsSync(file))return false;
  const text=fs.readFileSync(file,'utf8');
  const escaped=String(name).replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  return new RegExp(`export\\s+(?:class|function|const|type)\\s+${escaped}\\b`).test(text);
}

try{
  const iir=readJson(iirFile).iir??readJson(iirFile),manifest=readJson(path.join(generatedDir,'manifest.json')),errors=[],warnings=[];
  const entries=new Map((manifest.implementation_entrypoints??[]).map(x=>[x.implementation_id,x]));
  const manual=new Map((manifest.manual_composition??[]).map(x=>[x.implementation_id,x]));
  const plans=new Map((iir.transaction_plans??[]).map(x=>[x.id,x]));

  for(const uc of iir.use_cases??[]){
    const planIds=uc.transaction_plan_ids??[];
    if(!planIds.length)continue;
    const entry=entries.get(uc.id);
    if(!entry){errors.push({code:'GENERATED_TRANSACTION_ENTRYPOINT_MISSING',implementation_id:uc.id,message:'事务 Use Case 缺少 manifest implementation_entrypoint'});continue;}
    if(!planIds.includes(entry.transaction_plan_id))errors.push({code:'GENERATED_TRANSACTION_PLAN_MISMATCH',implementation_id:uc.id,message:`入口 transaction_plan_id 不属于 Use Case: ${entry.transaction_plan_id}`});
    const plan=plans.get(entry.transaction_plan_id);
    if(!plan)errors.push({code:'GENERATED_TRANSACTION_PLAN_UNKNOWN',implementation_id:uc.id,message:`入口引用不存在的 transaction plan: ${entry.transaction_plan_id}`});
    if(!String(entry.export_name??'').includes('Transactional'))errors.push({code:'GENERATED_TRANSACTION_BYPASS',implementation_id:uc.id,message:`事务 Use Case 正式入口不能指向非 Transactional export: ${entry.export_name??'<missing>'}`});
    const artifact=path.join(generatedDir,entry.artifact??'');
    if(!entry.artifact||!exported(artifact,entry.export_name))errors.push({code:'GENERATED_ENTRYPOINT_EXPORT_MISSING',implementation_id:uc.id,message:`manifest 入口在 artifact 中不存在: ${entry.artifact??'<missing>'}#${entry.export_name??'<missing>'}`});

    if(entry.fully_composed===true){
      if(entry.artifact!=='composition/generated.ts')errors.push({code:'GENERATED_COMPOSITION_ENTRYPOINT_INVALID',implementation_id:uc.id,message:'fully composed 事务入口必须来自 composition/generated.ts'});
      if(entry.requires_transaction_scoped_factory===true)warnings.push({code:'GENERATED_COMPOSITION_REDUNDANT_FACTORY_FLAG',implementation_id:uc.id,message:'fully composed 入口不需要调用方提供 scoped factory'});
    }else{
      if(entry.requires_transaction_scoped_factory!==true)errors.push({code:'GENERATED_TRANSACTION_FACTORY_CONTRACT_MISSING',implementation_id:uc.id,message:'未 fully composed 的事务入口必须要求 transaction-scoped factory'});
      if(!manual.has(uc.id))errors.push({code:'GENERATED_MANUAL_COMPOSITION_UNDECLARED',implementation_id:uc.id,message:'需要人工 composition 但 manifest.manual_composition 未声明'});
    }
  }

  const result={valid:errors.length===0,errors,warnings,stats:{transactional_use_cases:(iir.use_cases??[]).filter(x=>(x.transaction_plan_ids??[]).length).length,entrypoints:entries.size}};
  console.log(JSON.stringify(result,null,2));process.exit(result.valid?0:1);
}catch(e){console.error(JSON.stringify({valid:false,error:e.message},null,2));process.exit(2);}
