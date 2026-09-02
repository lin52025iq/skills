#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {readJson,writeJson} from './lib/model.mjs';

const pascal=(value)=>String(value??'Generated').split(/[^A-Za-z0-9]+/).filter(Boolean).map(x=>x[0].toUpperCase()+x.slice(1)).join('')||'Generated';
const camel=(value)=>{const p=pascal(value);return p[0].toLowerCase()+p.slice(1);};
const prop=(value)=>{const p=String(value??'field').split(/[^A-Za-z0-9]+/).filter(Boolean);return p.length?p[0].toLowerCase()+p.slice(1).map(x=>x[0].toUpperCase()+x.slice(1)).join(''):'field';};
const digest=(content)=>crypto.createHash('sha256').update(content).digest('hex');
const methodName=(operation)=>prop(typeof operation==='string'?operation:(operation?.name??'execute'));
const interfaceName=(node)=>pascal(node.name??node.id);
const guardName=(ref)=>`guard${pascal(String(ref).replace(/^rule\./,''))}`;
const useCaseName=(uc)=>`${pascal(uc.name??uc.semantic_refs?.[0]??uc.id)}UseCase`;
const errorName=(ref)=>`${pascal(String(ref).replace(/^error\./,''))}Error`;
const quoteSql=(identifier)=>`"${String(identifier).replace(/"/g,'""')}"`;

function put(root,relative,content,semanticRefs,artifacts){
  const file=path.join(root,relative);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,content,'utf8');
  artifacts.push({path:relative,semantic_refs:(semanticRefs??[]).filter(Boolean),generation_mode:'generated',content_hash:digest(content)});
}
function modelMaps(root){
  return{
    enums:new Map((root.domain_types?.enums??[]).map(x=>[x.semantic_ref,{...x,tsName:pascal(x.name??x.semantic_ref)}])),
    entities:new Map((root.domain_types?.entities??[]).map(x=>[x.semantic_ref,{...x,tsName:pascal(x.name??x.semantic_ref)}])),
    bindings:new Map((root.runtime_bindings??[]).map(x=>[x.semantic_ref,x])),
  };
}
function tsType(typeRef,maps){
  if(maps.enums.has(typeRef))return maps.enums.get(typeRef).tsName;
  if(maps.entities.has(typeRef))return maps.entities.get(typeRef).tsName;
  return{string:'string',boolean:'boolean',integer:'number',number:'number',datetime:'Date',date:'Date',duration:'number'}[typeRef]??'unknown';
}
function parameterType(parameter,maps){const base=tsType(parameter.type_ref,maps);return parameter.cardinality==='many'?`${base}[]`:base;}
function access(ref,maps,base='input'){
  const binding=maps.bindings.get(ref);if(!binding)return`${base}[${JSON.stringify(ref)}]`;
  const slot=prop(binding.slot);if(binding.kind==='entity')return base?`${base}.${slot}`:slot;
  const tail=(binding.path??[]).map(prop).join('.');return base?`${base}.${slot}.${tail}`:`${slot}.${tail}`;
}
function scopedAccess(ref,maps,scope=null,base='input'){
  if(scope?.alias&&typeof ref==='string'){
    if(ref===scope.alias)return scope.varName;
    if(ref.startsWith(`${scope.alias}.`)){
      const tail=ref.slice(scope.alias.length+1).split('.').filter(Boolean).map(prop).join('.');
      return tail?`${scope.varName}.${tail}`:scope.varName;
    }
  }
  return access(ref,maps,base);
}
function valueTs(value,maps,base='input',scope=null){
  if(value==null)return'undefined';
  if(typeof value!=='object')return JSON.stringify(value);
  if(typeof value.ref==='string')return scopedAccess(value.ref,maps,scope,base);
  if('literal'in value)return JSON.stringify(value.literal);
  if(value.enum)return JSON.stringify(value.enum.value);
  if(value.null)return'null';
  if(Array.isArray(value.set))return`[${value.set.map(x=>valueTs(x,maps,base,scope)).join(', ')}]`;
  if(Array.isArray(value.list))return`[${value.list.map(x=>valueTs(x,maps,base,scope)).join(', ')}]`;
  if(value.object&&typeof value.object==='object'){
    const fields=Object.entries(value.object.fields??{}).map(([ref,v])=>`${prop(String(ref).split('.').at(-1))}: ${valueTs(v,maps,base,scope)}`);
    return`{ ${fields.join(', ')} }`;
  }
  return'undefined';
}
function expressionTs(expression,maps,base='input',scope=null){
  if(!expression?.op)return'false';
  if(expression.op==='all')return`(${(expression.items??[]).map(x=>expressionTs(x,maps,base,scope)).join(' && ')||'true'})`;
  if(expression.op==='any')return`(${(expression.items??[]).map(x=>expressionTs(x,maps,base,scope)).join(' || ')||'false'})`;
  if(expression.op==='not')return`!(${expressionTs(expression.item,maps,base,scope)})`;
  const left=valueTs(expression.left,maps,base,scope),right=valueTs(expression.right,maps,base,scope);
  if(expression.op==='in')return`${right}.includes(${left})`;
  if(expression.op==='not_in')return`!${right}.includes(${left})`;
  return`${left} ${{eq:'===',ne:'!==',lt:'<',le:'<=',gt:'>',ge:'>='}[expression.op]??'==='} ${right}`;
}
function refsIn(value,out=new Set()){
  if(Array.isArray(value))for(const item of value)refsIn(item,out);
  else if(value&&typeof value==='object'){
    if(typeof value.ref==='string')out.add(value.ref);
    for(const item of Object.values(value))refsIn(item,out);
  }
  return out;
}
function entityRefs(expression,maps){
  const out=new Set();
  for(const ref of refsIn(expression)){
    const binding=maps.bindings.get(ref);if(binding?.entity_ref)out.add(binding.entity_ref);else if(binding?.kind==='entity')out.add(ref);
  }
  return[...out];
}
function fieldsByEntity(expression,maps){
  const out=new Map();
  for(const ref of refsIn(expression)){
    const binding=maps.bindings.get(ref);if(binding?.kind!=='field')continue;
    if(!out.has(binding.entity_ref))out.set(binding.entity_ref,new Set());
    out.get(binding.entity_ref).add(prop((binding.path??[]).at(-1)));
  }
  return out;
}
function entityFieldAccess(fieldRef,maps,entityVar='entity'){
  const binding=maps.bindings.get(fieldRef),tail=(binding?.path??[String(fieldRef).split('.').at(-1)]).map(prop).join('.');return`${entityVar}.${tail}`;
}
function assertionMethod(value){return value!==null&&typeof value==='object'?'toEqual':'toBe';}

function domainSource(maps){
  const lines=['// Code generated by logic-engineering. DO NOT EDIT.',''];
  for(const item of maps.enums.values())lines.push(`export type ${item.tsName} = ${(item.values??[]).map(JSON.stringify).join(' | ')||'never'};`,'');
  for(const entity of maps.entities.values()){
    lines.push(`export interface ${entity.tsName} {`);
    for(const field of entity.fields??[]){const base=tsType(field.type_ref,maps),type=field.cardinality==='many'?`${base}[]`:base;lines.push(`  ${prop(field.name)}${field.nullable?'?':''}: ${type}${field.nullable?' | null':''};`);}
    lines.push('}','');
  }
  return lines.join('\n');
}
function portsSource(root,maps){
  const domainTypes=[...new Set([...maps.entities.values(),...maps.enums.values()].map(x=>x.tsName))],lines=['// Code generated by logic-engineering. DO NOT EDIT.'];
  if(domainTypes.length)lines.push(`import type { ${domainTypes.join(', ')} } from '../domain/generated.js';`);lines.push('');
  for(const repo of root.repository_contracts??[]){
    const entityType=maps.entities.get(repo.entity_ref)?.tsName??'unknown';lines.push(`export interface ${interfaceName(repo)} {`);
    for(const operation of repo.operations??[])lines.push(methodName(operation)==='save'?`  save(entity: ${entityType}): Promise<void>;`:`  ${methodName(operation)}(...args: unknown[]): Promise<unknown>;`);
    lines.push('}','');
  }
  for(const port of root.external_ports??[]){
    lines.push(`export interface ${interfaceName(port)} {`);
    for(const operation of port.operations??[]){
      const parameters=(operation.parameters??[]).map(p=>`${prop(p.name)}: ${parameterType(p,maps)}`).join(', '),returnType=operation.return_type?tsType(operation.return_type,maps):'void';
      lines.push(`  ${methodName(operation)}(${parameters}): Promise<${returnType}>;`);
    }
    lines.push('}','');
  }
  return lines.join('\n');
}
function errorsSource(root){
  const lines=['// Code generated by logic-engineering. DO NOT EDIT.','export class GuardViolationError extends Error { constructor(readonly semanticId: string) { super(`guard failed: ${semanticId}`); this.name = "GuardViolationError"; } }',''];
  for(const ref of [...new Set((root.error_mappings??[]).map(x=>x.semantic_error_ref).filter(Boolean))])lines.push(`export class ${errorName(ref)} extends Error { readonly semanticId = ${JSON.stringify(ref)}; constructor(message = ${JSON.stringify(ref)}) { super(message); this.name = ${JSON.stringify(errorName(ref))}; } }`,'');
  return lines.join('\n');
}
function rulesSource(root,maps){
  const typeSet=new Set(),lines=['// Code generated by logic-engineering. DO NOT EDIT.'];
  for(const uc of root.use_cases??[])for(const guard of uc.guards??[])for(const ref of entityRefs(guard.expression,maps)){const type=maps.entities.get(ref)?.tsName;if(type)typeSet.add(type);}
  if(typeSet.size)lines.push(`import type { ${[...typeSet].join(', ')} } from '../domain/generated.js';`);lines.push('');
  const emitted=new Set();
  for(const uc of root.use_cases??[])for(const guard of uc.guards??[]){
    if(!guard.semantic_ref||emitted.has(guard.semantic_ref))continue;emitted.add(guard.semantic_ref);
    const picks=fieldsByEntity(guard.expression,maps),parts=[];
    for(const ref of entityRefs(guard.expression,maps)){const entity=maps.entities.get(ref);if(!entity)continue;const fields=[...(picks.get(ref)??[])],type=fields.length?`Pick<${entity.tsName}, ${fields.map(JSON.stringify).join(' | ')}>`:entity.tsName;parts.push(`${prop(entity.slot)}: ${type}`);}
    lines.push(`export function ${guardName(guard.semantic_ref)}(input: { ${parts.join('; ')} }): boolean {`,`  return ${expressionTs(guard.expression,maps)};`,'}','');
  }
  return lines.join('\n');
}

function effectLines(step,root,maps,dependencies,indent,scope=null){
  const lines=[];
  for(const effectId of step.effects??[]){
    const repo=(root.repository_contracts??[]).find(r=>(r.semantic_refs??[]).includes(effectId));
    if(repo){const dependency=dependencies.find(x=>x.id===repo.id),entity=maps.entities.get(repo.entity_ref);if(dependency&&entity){const target=scope?.entityType===repo.entity_ref?scope.varName:`input.${prop(entity.slot)}`;lines.push(`${indent}await this.${dependency.field}.save(${target});`);}}
    const port=(root.external_ports??[]).find(p=>(p.semantic_refs??[]).includes(effectId));
    if(port){
      const dependency=dependencies.find(x=>x.id===port.id),operation=(port.operations??[]).find(x=>(x.semantic_refs??[]).includes(effectId));
      if(dependency&&operation){const args=(operation.parameters??[]).map(p=>valueTs(p.value,maps,'input',scope)).join(', ');lines.push(`${indent}await this.${dependency.field}.${methodName(operation)}(${args});`);}
    }
  }
  return lines;
}
function emitStep(step,root,maps,dependencies,indent='    ',scope=null){
  const lines=[];
  if(step.kind==='decision'){
    if(!step.when?.op)throw new Error(`Decision ${step.semantic_ref} 缺少 typed when expression`);
    lines.push(`${indent}if (${expressionTs(step.when,maps,'input',scope)}) {`);
    for(const child of step.then_steps??[])lines.push(...emitStep(child,root,maps,dependencies,`${indent}  `,scope));
    if((step.else_steps??[]).length){lines.push(`${indent}} else {`);for(const child of step.else_steps)lines.push(...emitStep(child,root,maps,dependencies,`${indent}  `,scope));}
    lines.push(`${indent}}`);return lines;
  }
  if(step.kind==='foreach'){
    if(!step.collection_ref||!step.item_alias||!step.item_type)throw new Error(`FOREACH_IIR_INCOMPLETE: ${step.semantic_ref}`);
    const variable=prop(step.item_alias),loopScope={alias:step.item_alias,varName:variable,entityType:step.item_type};
    lines.push(`${indent}for (const ${variable} of ${access(step.collection_ref,maps)}) {`);
    if(step.when?.op)lines.push(`${indent}  if (!(${expressionTs(step.when,maps,'input',loopScope)})) continue;`);
    for(const child of step.do_steps??[])lines.push(...emitStep(child,root,maps,dependencies,`${indent}  `,loopScope));
    lines.push(`${indent}}`);return lines;
  }
  if(step.kind==='unresolved'||step.unresolved)throw new Error(`UNRESOLVED_STEP: ${step.semantic_ref}`);
  if(step.kind==='action'&&step.operation==='assign'&&step.target?.ref)lines.push(`${indent}${scopedAccess(step.target.ref,maps,scope)} = ${valueTs(step.value,maps,'input',scope)};`);
  else if(step.operation&&!['assign','invoke'].includes(step.operation))throw new Error(`ACTION_OPERATION_NOT_SUPPORTED: ${step.semantic_ref} operation=${step.operation}`);
  lines.push(...effectLines(step,root,maps,dependencies,indent,scope));return lines;
}
function usecasesSource(root,maps){
  const contracts=new Map([...((root.repository_contracts??[]).map(x=>[x.id,interfaceName(x)])),...((root.external_ports??[]).map(x=>[x.id,interfaceName(x)]))]),contractTypes=[...new Set(contracts.values())],entityTypes=[...new Set((root.use_cases??[]).flatMap(u=>(u.input_refs??[]).map(r=>maps.entities.get(r)?.tsName).filter(Boolean)))],guards=[...new Set((root.use_cases??[]).flatMap(u=>(u.guards??[]).map(g=>guardName(g.semantic_ref))))],lines=['// Code generated by logic-engineering. DO NOT EDIT.'];
  if(contractTypes.length)lines.push(`import type { ${contractTypes.join(', ')} } from '../ports/generated.js';`);if(entityTypes.length)lines.push(`import type { ${entityTypes.join(', ')} } from '../domain/generated.js';`);if(guards.length)lines.push(`import { ${guards.join(', ')} } from '../rules/generated.js';`);lines.push(`import { GuardViolationError } from '../errors/generated.js';`,'');
  for(const uc of root.use_cases??[]){
    const className=useCaseName(uc),inputName=`${className}Input`,dependencies=(uc.dependencies??[]).map(id=>({id,field:camel(id),type:contracts.get(id)??'unknown'}));
    lines.push(`export interface ${inputName} {`);for(const ref of uc.input_refs??[]){const entity=maps.entities.get(ref);if(entity)lines.push(`  ${prop(entity.slot)}: ${entity.tsName};`);}lines.push('}','',`export class ${className} {`,dependencies.length?`  constructor(${dependencies.map(d=>`private readonly ${d.field}: ${d.type}`).join(', ')}) {}`:'  constructor() {}','',`  async execute(input: ${inputName}): Promise<void> {`);
    for(const guard of uc.guards??[])lines.push(`    if (!${guardName(guard.semantic_ref)}(input)) throw new GuardViolationError(${JSON.stringify(guard.semantic_ref)});`);
    for(const step of uc.steps??[])lines.push(...emitStep(step,root,maps,dependencies));
    lines.push('  }','}','');
  }
  return lines.join('\n');
}

function defaultValue(typeRef,maps,seed,cardinality='one'){if(cardinality==='many')return'[]';if(maps.enums.has(typeRef))return JSON.stringify(maps.enums.get(typeRef).values?.[0]??'');if(typeRef==='string')return JSON.stringify(`fixture-${seed}`);if(['integer','number','duration'].includes(typeRef))return'0';if(typeRef==='boolean')return'false';return'undefined as never';}
function fixtureLines(testCase,useCase,maps){
  const values=new Map(Object.entries(testCase.given??{}));
  for(const expression of testCase.fixture_constraints??[]){if(expression?.op==='eq'&&expression.left?.ref&&expression.right?.ref&&!values.has(expression.left.ref)&&!values.has(expression.right.ref)){const sentinel=`fixture-${pascal(expression.left.ref)}`;values.set(expression.left.ref,sentinel);values.set(expression.right.ref,sentinel);}}
  const lines=[];
  for(const ref of useCase?.input_refs??[]){const entity=maps.entities.get(ref);if(!entity)continue;lines.push(`const ${prop(entity.slot)}: ${entity.tsName} = {`);for(const field of entity.fields??[]){const raw=values.get(field.semantic_ref),code=raw!==undefined?JSON.stringify(raw):defaultValue(field.type_ref,maps,field.semantic_ref,field.cardinality);lines.push(`  ${prop(field.name)}: ${code},`);}lines.push('};');}
  return lines;
}
function fakeDependencies(useCase,root){
  const lines=[],args=[];
  for(const id of useCase?.dependencies??[]){const name=camel(id),contract=(root.repository_contracts??[]).find(x=>x.id===id)??(root.external_ports??[]).find(x=>x.id===id);args.push(name);lines.push(`const ${name} = { ${(contract?.operations??[]).map(op=>`${methodName(op)}: async (..._args: unknown[]) => undefined`).join(', ')} };`);}
  return{lines,args};
}
function testsSource(root,plan,maps){
  const cases=(plan.target_test_plan??plan).cases??[],guardFunctions=[...new Set(cases.filter(c=>c.target_kind==='guard').map(c=>guardName(c.target_id)))],useCaseNames=[...new Set(cases.filter(c=>c.target_kind==='use_case').map(c=>useCaseName((root.use_cases??[]).find(u=>u.id===c.use_case_id))).filter(x=>x!=='GeneratedUseCase'))],domainTypes=[...new Set([...maps.entities.values(),...maps.enums.values()].map(x=>x.tsName))],lines=['// Code generated by logic-engineering. DO NOT EDIT.','import { describe, expect, it } from "vitest";'];
  if(domainTypes.length)lines.push(`import type { ${domainTypes.join(', ')} } from '../domain/generated.js';`);if(guardFunctions.length)lines.push(`import { ${guardFunctions.join(', ')} } from '../rules/generated.js';`);if(useCaseNames.length)lines.push(`import { ${useCaseNames.join(', ')} } from '../usecases/generated.js';`);lines.push('','describe("generated logic tests", () => {');
  for(const testCase of cases){
    if((testCase.unsupported??[]).length){lines.push(`  it.todo(${JSON.stringify(`${testCase.id} — ${testCase.unsupported.join('; ')}`)});`);continue;}
    if(testCase.target_kind==='guard'){
      const uc=(root.use_cases??[]).find(u=>(u.guards??[]).some(g=>g.semantic_ref===testCase.target_id)),guard=uc?.guards?.find(x=>x.semantic_ref===testCase.target_id),entities=entityRefs(guard?.expression,maps);
      lines.push(`  it(${JSON.stringify(testCase.id)}, () => {`);for(const line of fixtureLines({given:testCase.given,fixture_constraints:[]},{input_refs:entities},maps))lines.push(`    ${line}`);lines.push(`    expect(${guardName(testCase.target_id)}({ ${entities.map(r=>prop(maps.entities.get(r)?.slot)).join(', ')} })).toBe(${JSON.stringify(testCase.expect?.rule_result)});`,'  });');continue;
    }
    if(testCase.target_kind==='use_case'){
      const uc=(root.use_cases??[]).find(u=>u.id===testCase.use_case_id);if(!uc){lines.push(`  it.todo(${JSON.stringify(`${testCase.id} — missing use case`)});`);continue;}
      lines.push(`  it(${JSON.stringify(testCase.id)}, async () => {`);for(const line of fixtureLines(testCase,uc,maps))lines.push(`    ${line}`);const fakes=fakeDependencies(uc,root);for(const line of fakes.lines)lines.push(`    ${line}`);lines.push(`    const useCase = new ${useCaseName(uc)}(${fakes.args.join(', ')});`,`    await useCase.execute({ ${(uc.input_refs??[]).map(r=>prop(maps.entities.get(r)?.slot)).join(', ')} });`);for(const [ref,value] of Object.entries(testCase.expect??{})){if(!maps.bindings.has(ref))continue;lines.push(`    expect(${access(ref,maps,'')}).${assertionMethod(value)}(${JSON.stringify(value)});`);}lines.push('  });');
    }
  }
  lines.push('});','');return lines.join('\n');
}

function sqliteSource(root,maps){
  const repos=(root.repository_contracts??[]).filter(r=>r.binding?.mapping),entityTypes=[...new Set(repos.map(r=>maps.entities.get(r.entity_ref)?.tsName).filter(Boolean))],repoTypes=[...new Set(repos.map(interfaceName))],lines=['// Code generated by logic-engineering. DO NOT EDIT.'];
  if(entityTypes.length)lines.push(`import type { ${entityTypes.join(', ')} } from '../domain/generated.js';`);if(repoTypes.length)lines.push(`import type { ${repoTypes.join(', ')} } from '../ports/generated.js';`);lines.push('','export interface SqliteExecutor {','  run(sql: string, params: readonly unknown[]): Promise<void>;','}','');
  for(const repo of repos){
    const mapping=repo.binding.mapping,entity=maps.entities.get(repo.entity_ref);if(!entity)throw new Error(`SQLITE_ENTITY_TYPE_MISSING: ${repo.entity_ref}`);
    const unsupported=(repo.operations??[]).map(methodName).filter(name=>name!=='save');if(unsupported.length)throw new Error(`SQLITE_REPOSITORY_OPERATION_NOT_SUPPORTED: ${repo.id} ${unsupported.join(',')}`);
    const columns=entity.fields.map(field=>({field:field.semantic_ref,column:mapping.columns?.[field.semantic_ref],expression:entityFieldAccess(field.semantic_ref,maps,'entity')}));if(columns.some(x=>!x.column))throw new Error(`SQLITE_MAPPING_INCOMPLETE: ${repo.id}`);
    const primary=columns.find(x=>x.field===mapping.primary_key);if(!primary)throw new Error(`SQLITE_PRIMARY_KEY_MAPPING_MISSING: ${repo.id}`);
    const table=quoteSql(mapping.table),columnSql=columns.map(x=>quoteSql(x.column)).join(', '),placeholders=columns.map(()=>'?').join(', '),updates=columns.filter(x=>x.field!==mapping.primary_key).map(x=>`${quoteSql(x.column)} = excluded.${quoteSql(x.column)}`),conflict=updates.length?`ON CONFLICT(${quoteSql(primary.column)}) DO UPDATE SET ${updates.join(', ')}`:`ON CONFLICT(${quoteSql(primary.column)}) DO NOTHING`,sql=`INSERT INTO ${table} (${columnSql}) VALUES (${placeholders}) ${conflict}`;
    lines.push(`export class ${entity.tsName}SqliteRepository implements ${interfaceName(repo)} {`,`  constructor(private readonly db: SqliteExecutor) {}`,'',`  async save(entity: ${entity.tsName}): Promise<void> {`,`    await this.db.run(${JSON.stringify(sql)}, [`,`      ${columns.map(x=>x.expression).join(',\n      ')},`,'    ]);','  }','}','');
  }
  return lines.join('\n')+'\n';
}
const packageSource=()=>JSON.stringify({name:'logic-engineering-generated',private:true,type:'module',scripts:{typecheck:'tsc --noEmit',test:'vitest run'},devDependencies:{typescript:'^5.0.0',vitest:'^2.0.0'}},null,2)+'\n';
const tsconfigSource=()=>JSON.stringify({compilerOptions:{target:'ES2022',module:'NodeNext',moduleResolution:'NodeNext',strict:true,noEmit:true,skipLibCheck:true},include:['domain/**/*.ts','ports/**/*.ts','errors/**/*.ts','rules/**/*.ts','usecases/**/*.ts','adapters/**/*.ts','tests/**/*.ts']},null,2)+'\n';

const [iirFile,planFile,...args]=process.argv.slice(2),outputIndex=args.indexOf('-o')>=0?args.indexOf('-o'):args.indexOf('--output-dir'),outputDir=outputIndex>=0?args[outputIndex+1]:null;
if(!iirFile||!planFile||!outputDir){console.error('usage: node generate_typescript_v02.mjs iir.json target-test-plan.json -o generated-ts');process.exit(2);}
try{
  const document=readJson(iirFile),root=document.iir??document,plan=readJson(planFile),maps=modelMaps(root),blocking=(root.unresolved??[]).filter(x=>x?.severity==='blocking'||x?.blocking===true||typeof x==='string');
  if(!['typescript','ts'].includes(String(root.target_profile?.language??'').toLowerCase()))throw new Error('Target Profile language 必须是 TypeScript');
  if(String(root.target_profile?.persistence??'').toLowerCase()!=='sqlite')throw new Error('Reference Target persistence 必须是 SQLite');
  if(blocking.length)throw new Error(`IIR 存在 blocking unresolved: ${JSON.stringify(blocking)}`);
  fs.mkdirSync(outputDir,{recursive:true});const artifacts=[];
  put(outputDir,'domain/generated.ts',domainSource(maps),[...maps.enums.keys(),...maps.entities.keys()],artifacts);
  put(outputDir,'ports/generated.ts',portsSource(root,maps),[...(root.repository_contracts??[]),...(root.external_ports??[])].map(x=>x.id),artifacts);
  put(outputDir,'errors/generated.ts',errorsSource(root),(root.error_mappings??[]).map(x=>x.semantic_error_ref),artifacts);
  put(outputDir,'rules/generated.ts',rulesSource(root,maps),(root.use_cases??[]).flatMap(x=>(x.guards??[]).map(g=>g.semantic_ref)),artifacts);
  put(outputDir,'usecases/generated.ts',usecasesSource(root,maps),(root.use_cases??[]).map(x=>x.semantic_refs?.[0]),artifacts);
  put(outputDir,'adapters/sqlite.ts',sqliteSource(root,maps),(root.repository_contracts??[]).map(x=>x.id),artifacts);
  put(outputDir,'tests/generated.test.ts',testsSource(root,plan,maps),(plan.target_test_plan??plan).cases?.map(x=>x.source_semantic_id)??[],artifacts);
  put(outputDir,'package.json',packageSource(),[],artifacts);put(outputDir,'tsconfig.json',tsconfigSource(),[],artifacts);
  writeJson(path.join(outputDir,'manifest.json'),{generator:'typescript-v0.2',source_clm:root.source_clm_id,source_semantic_hash:root.source_semantic_hash,iir_version:root.version,target_profile:root.target_profile?.id,artifacts});
  console.log(JSON.stringify({ok:true,output_dir:outputDir,artifacts:artifacts.length,executable_tests:(plan.target_test_plan??plan).summary?.executable??0},null,2));
}catch(error){console.error(JSON.stringify({ok:false,error:error.message},null,2));process.exit(1);}
