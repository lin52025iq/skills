#!/usr/bin/env node
import {readJson,writeJson,rootOf,buildNodeIndex,semanticHash} from './lib/model.mjs';

function pascal(value){return String(value??'Generated').split(/[^A-Za-z0-9]+/).filter(Boolean).map(x=>x[0].toUpperCase()+x.slice(1)).join('')||'Generated';}
function camel(value){const p=pascal(value);return p[0].toLowerCase()+p.slice(1);}
function entityOfField(ref){const parts=String(ref).split('.');return parts.length>=3?parts.slice(0,2).join('.'):null;}
function collectRefs(v,out=new Set()){if(Array.isArray(v))for(const x of v)collectRefs(x,out);else if(v&&typeof v==='object'){if(typeof v.ref==='string')out.add(v.ref);for(const x of Object.values(v))collectRefs(x,out);}return out;}

function compileDomain(root){
  const enums=[],entities=[],runtime=[];
  for(const node of root.domain??[]){
    if(node.kind==='enum') enums.push({semantic_ref:node.id,name:pascal(node.id.replace(/^domain\./,'')),display_name:node.name??null,values:[...(node.values??[])]});
    if(node.kind==='entity'){
      const slot=camel(node.id.replace(/^domain\./,''));
      const fields=(node.fields??[]).map(f=>({semantic_ref:f.id,name:String(f.id).split('.').at(-1),type_ref:f.type,nullable:f.nullable??false,cardinality:f.cardinality??'one'}));
      entities.push({semantic_ref:node.id,name:pascal(node.id.replace(/^domain\./,'')),display_name:node.name??null,slot,fields});
      runtime.push({semantic_ref:node.id,kind:'entity',slot});
      for(const f of fields) runtime.push({semantic_ref:f.semantic_ref,kind:'field',entity_ref:node.id,slot,path:[f.name]});
    }
  }
  return {domain_types:{enums,entities},runtime_bindings:runtime};
}

function repositoryId(resource){const entity=entityOfField(resource)??resource;return `repository.${String(entity??'resource').replace(/^domain\./,'').replace(/\./g,'_')}`;}
function compileContracts(root){
  const repoMap=new Map(),portMap=new Map();
  for(const e of root.effects??[]){
    if(['read','write','persist'].includes(e.kind)){
      const entityRef=entityOfField(e.resource)??e.resource??'domain.unknown';
      const id=repositoryId(e.resource);
      if(!repoMap.has(id))repoMap.set(id,{id,kind:'repository_contract',entity_ref:entityRef,semantic_refs:[],operations:[],binding:{strategy:'repository',provider:null}});
      const repo=repoMap.get(id);repo.semantic_refs.push(e.id);const name=e.kind==='read'?'load':'save';if(!repo.operations.some(x=>x.name===name))repo.operations.push({name,semantic_refs:[e.id]});
    }else if(['external_call','emit','schedule'].includes(e.kind)){
      const system=e.system??(e.kind==='emit'?'event_bus':e.kind);
      const id=`port.${String(system).replace(/[^A-Za-z0-9_.-]/g,'_')}`;
      if(!portMap.has(id))portMap.set(id,{id,kind:'external_port',system,semantic_refs:[],operations:[],generation_mode:'contract_only'});
      const port=portMap.get(id);port.semantic_refs.push(e.id);const name=e.operation??(e.kind==='emit'?'publish':'execute');if(!port.operations.some(x=>x.name===name))port.operations.push({name,semantic_refs:[e.id]});
    }
  }
  return {repositories:[...repoMap.values()],ports:[...portMap.values()]};
}

function compilePlans(root,profile,unresolved){
  const transaction_plans=[],concurrency_plans=[],retry_plans=[],idempotency_plans=[];
  for(const c of root.constraints??[]){
    if(c.kind==='atomicity'){
      const strategy=profile.transaction_strategy??null;
      transaction_plans.push({id:`plan.${c.id}`,kind:'transaction_plan',semantic_refs:[c.id],members:c.actions??c.members??[],strategy,provider:profile.persistence??null});
      if(!strategy)unresolved.push({semantic_ref:c.id,reason:'Target Profile 缺少 transaction_strategy',required_for:c.id,severity:'blocking'});
    }else if(c.kind==='concurrency'){
      const strategy=profile.concurrency_strategy??null;
      concurrency_plans.push({id:`plan.${c.id}`,kind:'concurrency_plan',semantic_refs:[c.id],resource_ref:c.resource??null,scope:c.scope??null,strategy});
      if(!strategy)unresolved.push({semantic_ref:c.id,reason:'Target Profile 缺少 concurrency_strategy',required_for:c.id,severity:'blocking'});
    }else if(c.kind==='idempotency'){
      const strategy=profile.idempotency_strategy??c.strategy??null;
      idempotency_plans.push({id:`plan.${c.id}`,kind:'idempotency_plan',semantic_refs:[c.id],operation_ref:c.operation??null,key_ref:c.key??null,strategy});
      if(!strategy)unresolved.push({semantic_ref:c.id,reason:'缺少幂等实现策略',required_for:c.id,severity:'blocking'});
    }else if(c.kind==='retry'){
      const strategy=profile.retry_strategy??c.strategy??null;
      retry_plans.push({id:`plan.${c.id}`,kind:'retry_plan',semantic_refs:[c.id],operation_ref:c.operation??null,strategy,max_attempts:c.max_attempts??null});
      if(!strategy)unresolved.push({semantic_ref:c.id,reason:'缺少重试实现策略',required_for:c.id,severity:'blocking'});
    }
  }
  return {transaction_plans,concurrency_plans,retry_plans,idempotency_plans};
}

function compileUseCases(root,index,repositories,ports,unresolved){
  const use_cases=[];
  for(const b of root.behaviors??[]){
    const guards=[];const steps=[];const refs=new Set();
    for(const id of b.preconditions??[]){const n=index.get(id);if(!n){unresolved.push({semantic_ref:id,reason:'Behavior precondition 节点不存在',required_for:b.id,severity:'blocking'});continue;}guards.push({semantic_ref:id,expression:n.expression??null,failure_ref:n.failure??null});collectRefs(n.expression,refs);}
    for(const id of b.flow??[]){const n=index.get(id);if(!n){unresolved.push({semantic_ref:id,reason:'Behavior flow 节点不存在',required_for:b.id,severity:'blocking'});continue;}const step={semantic_ref:id,kind:n.kind,operation:n.operation??null,target:n.target??null,value:n.value??null,effects:n.effects??[],when:n.when??null,then:n.then??[],else:n.else??[]};steps.push(step);collectRefs(step,refs);}
    for(const post of b.postconditions??[]){const n=index.get(post);if(n?.expression)collectRefs(n.expression,refs);}
    const inputEntities=[...new Set([...refs].map(entityOfField).filter(Boolean))];
    const effectIds=new Set(steps.flatMap(s=>s.effects??[]));
    const dependencies=[...repositories.filter(x=>x.semantic_refs.some(r=>effectIds.has(r))).map(x=>x.id),...ports.filter(x=>x.semantic_refs.some(r=>effectIds.has(r))).map(x=>x.id)];
    use_cases.push({id:`usecase.${b.id.replace(/^behavior\./,'')}`,kind:'use_case',semantic_refs:[b.id],name:pascal(b.id.replace(/^behavior\./,'')),display_name:b.name??null,input_refs:inputEntities,inputs:inputEntities,guards,steps,outputs:b.outputs??[],failure_refs:b.failures??[],postconditions:b.postconditions??[],dependencies});
  }
  return use_cases;
}

function compileErrors(root){
  const refs=new Set();for(const b of root.behaviors??[])for(const x of b.failures??[])refs.add(x);for(const r of root.rules??[])if(r.failure)refs.add(r.failure);
  return [...refs].map(ref=>({id:`error_mapping.${ref.replace(/^error\./,'')}`,semantic_error_ref:ref,target_error:`${pascal(ref.replace(/^error\./,''))}Error`}));
}

function compile(clm,profile){
  const root=rootOf(clm),index=buildNodeIndex(clm),unresolved=[];
  const {domain_types,runtime_bindings}=compileDomain(root);
  const {repositories,ports}=compileContracts(root);
  for(const repo of repositories){repo.binding.provider=profile.persistence??null;if(!profile.persistence)unresolved.push({semantic_ref:repo.entity_ref,reason:'Target Profile 缺少 persistence provider',required_for:repo.id,severity:'blocking'});}
  const plans=compilePlans(root,profile,unresolved);
  const use_cases=compileUseCases(root,index,repositories,ports,unresolved);
  const error_mappings=compileErrors(root);
  const generation_regions=[...use_cases.map(u=>({id:`region.${u.id}`,mode:'generated',semantic_refs:u.semantic_refs})),...repositories.map(r=>({id:`region.${r.id}`,mode:'contract_only',semantic_refs:r.semantic_refs.length?r.semantic_refs:[r.entity_ref]})),...ports.map(p=>({id:`region.${p.id}`,mode:p.generation_mode,semantic_refs:p.semantic_refs}))];
  const traceability=use_cases.map(u=>({implementation_id:u.id,semantic_refs:[...u.semantic_refs,...u.guards.map(g=>g.semantic_ref),...u.steps.map(s=>s.semantic_ref)]}));
  return {iir:{version:'0.2',source_clm_id:root.id,source_clm_version:root.version,source_semantic_hash:semanticHash(clm),target_profile:profile,domain_types,runtime_bindings,use_cases,repository_contracts:repositories,external_ports:ports,...plans,error_mappings,primitive_bindings:[],generation_regions,traceability,unresolved}};
}

const [clmFile,profileFile,...args]=process.argv.slice(2);const oi=args.indexOf('-o')>=0?args.indexOf('-o'):args.indexOf('--output');const output=oi>=0?args[oi+1]:null;
if(!clmFile||!profileFile||!output){console.error('usage: node compile_iir.mjs clm.json target-profile.json -o implementation.iir.json');process.exit(2);}
try{const clm=readJson(clmFile),raw=readJson(profileFile),profile=raw.target_profile??raw;writeJson(output,compile(clm,profile));console.log(JSON.stringify({ok:true,output},null,2));}catch(e){console.error(JSON.stringify({ok:false,error:e.message},null,2));process.exit(1);}
