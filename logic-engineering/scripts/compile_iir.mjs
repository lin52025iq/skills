#!/usr/bin/env node
import {readJson,writeJson,rootOf,buildNodeIndex,buildSymbolTable,semanticHash,collectionElementScope,resolveScopedRef,valueType} from './lib/model.mjs';

const pascal=(value)=>String(value??'Generated').split(/[^A-Za-z0-9]+/).filter(Boolean).map(x=>x[0].toUpperCase()+x.slice(1)).join('')||'Generated';
const camel=(value)=>{const p=pascal(value);return p[0].toLowerCase()+p.slice(1);};
const entityOfField=(ref)=>{const p=String(ref).split('.');return p.length>=3?p.slice(0,2).join('.'):null;};
const safeSqlIdentifier=(v)=>typeof v==='string'&&/^[A-Za-z_][A-Za-z0-9_]*$/.test(v);
function collectRefs(v,out=new Set()){if(Array.isArray(v))for(const x of v)collectRefs(x,out);else if(v&&typeof v==='object'){if(typeof v.ref==='string')out.add(v.ref);for(const x of Object.values(v))collectRefs(x,out);}return out;}
function collectGlobalRefs(v,symbols,scope,out=new Set()){
  if(Array.isArray(v)){for(const x of v)collectGlobalRefs(x,symbols,scope,out);return out;}
  if(v&&typeof v==='object'){
    if(typeof v.ref==='string'&&!resolveScopedRef(v.ref,scope,symbols))out.add(v.ref);
    for(const x of Object.values(v))collectGlobalRefs(x,symbols,scope,out);
  }
  return out;
}
function describeValue(v,symbols){
  let cardinality='one';if(Array.isArray(v?.list)||Array.isArray(v?.set))cardinality='many';else if(v?.ref)cardinality=symbols[v.ref]?.cardinality??'one';
  return{type_ref:valueType(v,symbols)??null,cardinality};
}

function compileDomain(root){
  const enums=[],entities=[],runtime=[];
  for(const node of root.domain??[]){
    if(node.kind==='enum')enums.push({semantic_ref:node.id,name:pascal(node.id.replace(/^domain\./,'')),display_name:node.name??null,values:[...(node.values??[])]});
    if(node.kind==='entity'){
      const slot=camel(node.id.replace(/^domain\./,''));
      const fields=(node.fields??[]).map(f=>({semantic_ref:f.id,name:String(f.id).split('.').at(-1),type_ref:f.type,nullable:f.nullable??false,cardinality:f.cardinality??'one'}));
      entities.push({semantic_ref:node.id,name:pascal(node.id.replace(/^domain\./,'')),display_name:node.name??null,slot,fields});
      runtime.push({semantic_ref:node.id,kind:'entity',slot});
      for(const f of fields)runtime.push({semantic_ref:f.semantic_ref,kind:'field',entity_ref:node.id,slot,path:[f.name],type_ref:f.type,cardinality:f.cardinality,nullable:f.nullable});
    }
  }
  return{domain_types:{enums,entities},runtime_bindings:runtime};
}

const repositoryId=(resource)=>`repository.${String(entityOfField(resource)??resource??'resource').replace(/^domain\./,'').replace(/\./g,'_')}`;
function compileContracts(root,symbols,unresolved){
  const repoMap=new Map(),portMap=new Map();
  for(const effect of root.effects??[]){
    if(['read','write','persist'].includes(effect.kind)){
      const entityRef=entityOfField(effect.resource)??effect.resource??'domain.unknown',id=repositoryId(effect.resource);
      if(!repoMap.has(id))repoMap.set(id,{id,kind:'repository_contract',entity_ref:entityRef,semantic_refs:[],operations:[],binding:{strategy:'repository',provider:null,mapping:null}});
      const repo=repoMap.get(id);repo.semantic_refs.push(effect.id);const name=effect.kind==='read'?'load':'save';
      let op=repo.operations.find(x=>x.name===name);if(!op){op={name,semantic_refs:[]};repo.operations.push(op);}op.semantic_refs.push(effect.id);continue;
    }
    if(!['external_call','emit','schedule'].includes(effect.kind))continue;
    const system=effect.system??(effect.kind==='emit'?'event_bus':effect.kind),id=`port.${String(system).replace(/[^A-Za-z0-9_.-]/g,'_')}`,name=effect.operation??(effect.kind==='emit'?'publish':'execute');
    if(!portMap.has(id))portMap.set(id,{id,kind:'external_port',system,semantic_refs:[],operations:[],generation_mode:'contract_only'});
    const port=portMap.get(id);port.semantic_refs.push(effect.id);
    const parameters=(effect.arguments??[]).map(arg=>({name:arg.name,...describeValue(arg.value,symbols),value:structuredClone(arg.value)}));
    const signature=parameters.map(x=>({name:x.name,type_ref:x.type_ref,cardinality:x.cardinality}));
    let op=port.operations.find(x=>x.name===name);
    if(!op){op={name,semantic_refs:[],parameters,failure_refs:[...(effect.failure_refs??[])],return_type:null};port.operations.push(op);}
    else if(JSON.stringify(op.parameters.map(x=>({name:x.name,type_ref:x.type_ref,cardinality:x.cardinality})))!==JSON.stringify(signature)){
      unresolved.push({semantic_ref:effect.id,reason:`External Port ${id}.${name} 出现不兼容参数签名`,required_for:id,severity:'blocking'});
    }
    op.semantic_refs.push(effect.id);op.failure_refs=[...new Set([...(op.failure_refs??[]),...(effect.failure_refs??[])])];
  }
  return{repositories:[...repoMap.values()],ports:[...portMap.values()]};
}

function attachPersistenceMappings(repositories,profile,symbols,unresolved){
  const explicit=profile.persistence_generation==='explicit_mapping',mappings=profile.persistence_mappings??{};
  for(const repo of repositories){
    repo.binding.provider=profile.persistence??null;
    if(!profile.persistence){unresolved.push({semantic_ref:repo.entity_ref,reason:'Target Profile 缺少 persistence provider',required_for:repo.id,severity:'blocking'});continue;}
    const mapping=mappings[repo.entity_ref]??null;repo.binding.mapping=mapping?structuredClone(mapping):null;
    if(!explicit)continue;
    if(!mapping){unresolved.push({semantic_ref:repo.entity_ref,reason:`缺少显式 persistence mapping: ${repo.entity_ref}`,required_for:repo.id,severity:'blocking'});continue;}
    if(!safeSqlIdentifier(mapping.table))unresolved.push({semantic_ref:repo.entity_ref,reason:`非法或缺失 table 名: ${mapping.table??'<missing>'}`,required_for:repo.id,severity:'blocking'});
    const pk=mapping.primary_key,pkSymbol=typeof pk==='string'?symbols[pk]:null;
    if(!pkSymbol||pkSymbol.kind!=='field'||pkSymbol.owner!==repo.entity_ref)unresolved.push({semantic_ref:repo.entity_ref,reason:`primary_key 必须引用 ${repo.entity_ref} 的字段: ${pk??'<missing>'}`,required_for:repo.id,severity:'blocking'});
    const columns=mapping.columns;
    if(!columns||typeof columns!=='object'||Array.isArray(columns)){unresolved.push({semantic_ref:repo.entity_ref,reason:'persistence mapping.columns 必须是对象',required_for:repo.id,severity:'blocking'});continue;}
    const entityFields=Object.values(symbols).filter(x=>x.kind==='field'&&x.owner===repo.entity_ref).map(x=>x.id);
    for(const field of entityFields)if(!Object.hasOwn(columns,field))unresolved.push({semantic_ref:field,reason:`显式 save mapping 缺少字段 column: ${field}`,required_for:repo.id,severity:'blocking'});
    for(const [field,column] of Object.entries(columns)){
      const symbol=symbols[field];if(!symbol||symbol.kind!=='field'||symbol.owner!==repo.entity_ref)unresolved.push({semantic_ref:field,reason:`column mapping 引用了不属于 ${repo.entity_ref} 的字段`,required_for:repo.id,severity:'blocking'});
      if(!safeSqlIdentifier(column))unresolved.push({semantic_ref:field,reason:`非法 SQLite column 名: ${column}`,required_for:repo.id,severity:'blocking'});
    }
    if(typeof pk==='string'&&!Object.hasOwn(columns,pk))unresolved.push({semantic_ref:pk,reason:'primary_key 必须出现在 columns mapping 中',required_for:repo.id,severity:'blocking'});
  }
}

function compilePlans(root,profile,unresolved){
  const transaction_plans=[],concurrency_plans=[],retry_plans=[],idempotency_plans=[],behaviors=new Map((root.behaviors??[]).map(x=>[x.id,x]));
  for(const c of root.constraints??[]){
    if(c.kind==='atomicity'){
      const strategy=profile.transaction_strategy??null,behavior=behaviors.get(c.behavior_ref),members=[...(c.members??[])];let start_index=null,end_index=null,boundary_valid=true;
      if(!behavior){unresolved.push({semantic_ref:c.id,reason:`atomicity.behavior_ref 不存在或不是 Behavior: ${c.behavior_ref??'<missing>'}`,required_for:c.id,severity:'blocking'});boundary_valid=false;}
      else{const flow=behavior.flow??[],positions=members.map(x=>flow.indexOf(x));if(!members.length||positions.some(x=>x<0)){unresolved.push({semantic_ref:c.id,reason:'atomicity.members 必须全部属于 behavior 顶层 flow',required_for:c.behavior_ref,severity:'blocking'});boundary_valid=false;}else{start_index=Math.min(...positions);end_index=Math.max(...positions);const expected=flow.slice(start_index,end_index+1);if(expected.length!==members.length||expected.some((x,i)=>x!==members[i])){unresolved.push({semantic_ref:c.id,reason:'atomicity.members 必须按 behavior flow 顺序形成连续区间',required_for:c.behavior_ref,severity:'blocking'});boundary_valid=false;}}}
      transaction_plans.push({id:`plan.${c.id}`,kind:'transaction_plan',semantic_refs:[c.id],behavior_ref:c.behavior_ref??null,members,strategy,provider:profile.persistence??null,start_index,end_index,boundary_valid});
      if(!strategy)unresolved.push({semantic_ref:c.id,reason:'Target Profile 缺少 transaction_strategy',required_for:c.id,severity:'blocking'});
    }else if(c.kind==='concurrency'){
      const strategy=profile.concurrency_strategy??null;concurrency_plans.push({id:`plan.${c.id}`,kind:'concurrency_plan',semantic_refs:[c.id],resource_ref:c.resource??null,scope:c.scope??null,strategy});if(!strategy)unresolved.push({semantic_ref:c.id,reason:'Target Profile 缺少 concurrency_strategy',required_for:c.id,severity:'blocking'});
    }else if(c.kind==='idempotency'){
      const strategy=profile.idempotency_strategy??c.strategy??null;idempotency_plans.push({id:`plan.${c.id}`,kind:'idempotency_plan',semantic_refs:[c.id],operation_ref:c.operation??null,key_ref:c.key??null,strategy});if(!strategy)unresolved.push({semantic_ref:c.id,reason:'缺少幂等实现策略',required_for:c.id,severity:'blocking'});
    }else if(c.kind==='retry'){
      const strategy=profile.retry_strategy??c.strategy??null;retry_plans.push({id:`plan.${c.id}`,kind:'retry_plan',semantic_refs:[c.id],operation_ref:c.operation??null,strategy,max_attempts:c.max_attempts??null});if(!strategy)unresolved.push({semantic_ref:c.id,reason:'缺少重试实现策略',required_for:c.id,severity:'blocking'});
    }
  }
  return{transaction_plans,concurrency_plans,retry_plans,idempotency_plans};
}

function compileStep(id,index,symbols,unresolved,owner,stack=new Set(),scope=null){
  if(stack.has(id)){unresolved.push({semantic_ref:id,reason:'Flow 中检测到递归步骤引用',required_for:owner,severity:'blocking'});return{semantic_ref:id,kind:'unresolved',unresolved:true};}
  const node=index.get(id);if(!node){unresolved.push({semantic_ref:id,reason:'Behavior flow 节点不存在',required_for:owner,severity:'blocking'});return{semantic_ref:id,kind:'unresolved',unresolved:true};}
  const next=new Set(stack);next.add(id);
  if(node.kind==='decision')return{semantic_ref:id,kind:'decision',when:node.when??null,then_steps:(node.then??[]).map(x=>compileStep(x,index,symbols,unresolved,owner,next,scope)),else_steps:(node.else??[]).map(x=>compileStep(x,index,symbols,unresolved,owner,next,scope))};
  if(node.kind==='foreach'){
    const loopScope=collectionElementScope(node.collection,node.item,symbols);
    if(!loopScope.valid){unresolved.push({semantic_ref:id,reason:loopScope.reason,required_for:owner,severity:'blocking'});return{semantic_ref:id,kind:'foreach',unresolved:true,collection:node.collection??null,item_alias:node.item??'item',do_steps:[]};}
    if(scope&&node.collection?.ref&&resolveScopedRef(node.collection.ref,scope,symbols))unresolved.push({semantic_ref:id,reason:'v0.2 暂不支持嵌套 foreach 使用 scoped collection',required_for:owner,severity:'blocking'});
    return{semantic_ref:id,kind:'foreach',collection:node.collection??null,collection_ref:node.collection?.ref??null,item_alias:loopScope.alias,item_type:loopScope.entityType,when:node.when??null,do_steps:(node.do??[]).map(x=>compileStep(x,index,symbols,unresolved,owner,next,loopScope))};
  }
  return{semantic_ref:id,kind:node.kind,operation:node.operation??null,target:node.target??null,value:node.value??null,effects:node.effects??[],when:node.when??null,scope:scope?{alias:scope.alias,entity_type:scope.entityType}:null};
}
function collectEffects(step,out=new Set()){for(const x of step.effects??[])out.add(x);for(const x of step.then_steps??[])collectEffects(x,out);for(const x of step.else_steps??[])collectEffects(x,out);for(const x of step.do_steps??[])collectEffects(x,out);return out;}
function collectStepRefs(step,out=new Set()){if(step.semantic_ref)out.add(step.semantic_ref);for(const x of step.then_steps??[])collectStepRefs(x,out);for(const x of step.else_steps??[])collectStepRefs(x,out);for(const x of step.do_steps??[])collectStepRefs(x,out);return out;}
function collectStepGlobalRefs(step,symbols,scope,out=new Set()){
  if(step.kind==='foreach'){collectGlobalRefs(step.collection,symbols,scope,out);const loopScope={alias:step.item_alias,entityType:step.item_type};collectGlobalRefs(step.when,symbols,loopScope,out);for(const child of step.do_steps??[])collectStepGlobalRefs(child,symbols,loopScope,out);return out;}
  collectGlobalRefs(step.when,symbols,scope,out);collectGlobalRefs(step.target,symbols,scope,out);collectGlobalRefs(step.value,symbols,scope,out);for(const child of step.then_steps??[])collectStepGlobalRefs(child,symbols,scope,out);for(const child of step.else_steps??[])collectStepGlobalRefs(child,symbols,scope,out);return out;
}

function compileUseCases(root,index,symbols,repositories,ports,transactionPlans,unresolved){
  const use_cases=[],effectsById=new Map((root.effects??[]).map(x=>[x.id,x]));
  for(const b of root.behaviors??[]){
    const guards=[],refs=new Set();
    for(const id of b.preconditions??[]){const n=index.get(id);if(!n){unresolved.push({semantic_ref:id,reason:'Behavior precondition 节点不存在',required_for:b.id,severity:'blocking'});continue;}guards.push({semantic_ref:id,expression:n.expression??null,failure_ref:n.failure??null});collectRefs(n.expression,refs);}
    const steps=(b.flow??[]).map(id=>compileStep(id,index,symbols,unresolved,b.id));for(const step of steps)collectStepGlobalRefs(step,symbols,null,refs);
    const effectIds=new Set();for(const step of steps)collectEffects(step,effectIds);
    for(const effectId of effectIds){const effect=effectsById.get(effectId);if(effect?.arguments)collectGlobalRefs(effect.arguments,symbols,null,refs);}
    for(const post of b.postconditions??[]){const n=index.get(post);if(n?.expression)collectRefs(n.expression,refs);}
    const inputEntities=[...new Set([...refs].map(entityOfField).filter(entity=>entity&&symbols[entity]?.kind==='entity'))];
    const dependencies=[...repositories.filter(x=>x.semantic_refs.some(r=>effectIds.has(r))).map(x=>x.id),...ports.filter(x=>x.semantic_refs.some(r=>effectIds.has(r))).map(x=>x.id)];
    const transaction_plan_ids=transactionPlans.filter(x=>x.behavior_ref===b.id).map(x=>x.id);
    use_cases.push({id:`usecase.${b.id.replace(/^behavior\./,'')}`,kind:'use_case',semantic_refs:[b.id],name:pascal(b.id.replace(/^behavior\./,'')),display_name:b.name??null,input_refs:inputEntities,inputs:inputEntities,guards,steps,outputs:b.outputs??[],failure_refs:b.failures??[],postconditions:b.postconditions??[],dependencies,transaction_plan_ids});
  }
  return use_cases;
}
function compileErrors(root){const refs=new Set();for(const b of root.behaviors??[])for(const x of b.failures??[])refs.add(x);for(const r of root.rules??[])if(r.failure)refs.add(r.failure);for(const e of root.effects??[])for(const x of e.failure_refs??[])refs.add(x);return[...refs].map(ref=>({id:`error_mapping.${ref.replace(/^error\./,'')}`,semantic_error_ref:ref,target_error:`${pascal(ref.replace(/^error\./,''))}Error`}));}

function compile(clm,profile){
  const root=rootOf(clm),index=buildNodeIndex(clm),symbols=buildSymbolTable(clm),unresolved=[],domain=compileDomain(root),contracts=compileContracts(root,symbols,unresolved);
  attachPersistenceMappings(contracts.repositories,profile,symbols,unresolved);
  const plans=compilePlans(root,profile,unresolved),use_cases=compileUseCases(root,index,symbols,contracts.repositories,contracts.ports,plans.transaction_plans,unresolved),error_mappings=compileErrors(root);
  const generation_regions=[...use_cases.map(u=>({id:`region.${u.id}`,mode:'generated',semantic_refs:u.semantic_refs})),...contracts.repositories.map(r=>({id:`region.${r.id}`,mode:'contract_only',semantic_refs:r.semantic_refs.length?r.semantic_refs:[r.entity_ref]})),...contracts.ports.map(p=>({id:`region.${p.id}`,mode:p.generation_mode,semantic_refs:p.semantic_refs}))];
  const traceability=use_cases.map(u=>{const refs=new Set(u.semantic_refs);for(const g of u.guards??[])refs.add(g.semantic_ref);for(const step of u.steps??[])collectStepRefs(step,refs);for(const planId of u.transaction_plan_ids??[]){const plan=plans.transaction_plans.find(x=>x.id===planId);for(const ref of plan?.semantic_refs??[])refs.add(ref);}return{implementation_id:u.id,semantic_refs:[...refs]};});
  return{iir:{version:'0.2',source_clm_id:root.id,source_clm_version:root.version,source_semantic_hash:semanticHash(clm),target_profile:profile,...domain,use_cases,repository_contracts:contracts.repositories,external_ports:contracts.ports,...plans,error_mappings,primitive_bindings:[],generation_regions,traceability,unresolved}};
}

const [clmFile,profileFile,...args]=process.argv.slice(2),oi=args.indexOf('-o')>=0?args.indexOf('-o'):args.indexOf('--output'),output=oi>=0?args[oi+1]:null;
if(!clmFile||!profileFile||!output){console.error('usage: node compile_iir.mjs clm.json target-profile.json -o implementation.iir.json');process.exit(2);}
try{const clm=readJson(clmFile),raw=readJson(profileFile),profile=raw.target_profile??raw;writeJson(output,compile(clm,profile));console.log(JSON.stringify({ok:true,output},null,2));}catch(e){console.error(JSON.stringify({ok:false,error:e.message},null,2));process.exit(1);}
