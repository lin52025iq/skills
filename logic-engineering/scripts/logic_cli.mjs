#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {readJson,writeJson,rootOf,iterNodes,buildNodeIndex,buildSymbolTable,semanticHash,unwrapValue,valueRef,valueType,compatibleTypes,enumContains,validatePlacement} from './lib/model.mjs';

function fail(message,extra={}){console.error(JSON.stringify({ok:false,error:message,...extra},null,2));process.exit(1)}
function option(args,...names){for(const name of names){const i=args.indexOf(name);if(i>=0)return args[i+1]??null}return null}
function refsIn(value,out=[]){if(Array.isArray(value))for(const item of value)refsIn(item,out);else if(value&&typeof value==='object'){if(typeof value.ref==='string')out.push(value.ref);for(const item of Object.values(value))refsIn(item,out)}return out}

function validateTypedValue(value,symbols,errors,owner,location){
  if(!value||typeof value!=='object'||Array.isArray(value)){errors.push({code:'INVALID_TYPED_VALUE',semantic_id:owner,path:location,message:'typed value 必须是对象'});return null}
  const kinds=['ref','literal','enum','null','set'].filter(k=>k in value);if(kinds.length!==1){errors.push({code:'INVALID_TYPED_VALUE',semantic_id:owner,path:location,message:'必须且只能包含 ref/literal/enum/null/set 之一'});return null}
  if(value.ref){if(!symbols[value.ref])errors.push({code:'UNKNOWN_SYMBOL',semantic_id:owner,path:location,message:`未知 symbol: ${value.ref}`});return symbols[value.ref]?.type??null}
  if(value.enum){const type=value.enum.type;if(!symbols[type]||symbols[type].kind!=='enum')errors.push({code:'INVALID_ENUM_TYPE',semantic_id:owner,path:location,message:`非法 enum 类型: ${type}`});else if(!enumContains(symbols,type,value.enum.value))errors.push({code:'INVALID_ENUM_VALUE',semantic_id:owner,path:location,message:`${value.enum.value} 不属于 ${type}`});return type??null}
  if(Array.isArray(value.set)){for(let i=0;i<value.set.length;i++)validateTypedValue(value.set[i],symbols,errors,owner,`${location}.set[${i}]`);return'set'}
  return valueType(value,symbols)
}
function validateExpression(expr,symbols,errors,owner,location='expression'){
  if(!expr||typeof expr!=='object'||Array.isArray(expr)){errors.push({code:'INVALID_TYPED_EXPRESSION',semantic_id:owner,path:location,message:'表达式必须是对象'});return}
  const op=expr.op;
  if(op==='all'||op==='any'){if(!Array.isArray(expr.items)||!expr.items.length){errors.push({code:'INVALID_TYPED_EXPRESSION',semantic_id:owner,path:location,message:`${op} 需要非空 items`});return}expr.items.forEach((x,i)=>validateExpression(x,symbols,errors,owner,`${location}.items[${i}]`));return}
  if(op==='not'){validateExpression(expr.item,symbols,errors,owner,`${location}.item`);return}
  if(!['eq','ne','lt','le','gt','ge','in','not_in'].includes(op)){errors.push({code:'INVALID_TYPED_EXPRESSION',semantic_id:owner,path:location,message:`不支持 op: ${op}`});return}
  const leftType=validateTypedValue(expr.left,symbols,errors,owner,`${location}.left`);
  if(op==='in'||op==='not_in'){
    if(!Array.isArray(expr.right?.set)){errors.push({code:'INVALID_TYPED_EXPRESSION',semantic_id:owner,path:`${location}.right`,message:'in/not_in 右侧必须是 typed set'});return}
    expr.right.set.forEach((item,i)=>{const itemType=validateTypedValue(item,symbols,errors,owner,`${location}.right.set[${i}]`);if(!compatibleTypes(leftType,itemType))errors.push({code:'TYPE_MISMATCH',semantic_id:owner,path:location,message:`集合成员类型 ${itemType} 与 ${leftType} 不兼容`})});return
  }
  const rightType=validateTypedValue(expr.right,symbols,errors,owner,`${location}.right`);if(!compatibleTypes(leftType,rightType))errors.push({code:'TYPE_MISMATCH',semantic_id:owner,path:location,message:`比较类型 ${leftType} 与 ${rightType} 不兼容`})
}
function validateClm(document){
  const root=rootOf(document),errors=[],warnings=[],ids=new Set(),symbols=buildSymbolTable(document),index=buildNodeIndex(document);
  for(const [collection,node] of iterNodes(document)){
    const placement=validatePlacement(node,collection);if(placement)errors.push({code:'NODE_COLLECTION_MISMATCH',semantic_id:node.id,message:placement});if(ids.has(node.id))errors.push({code:'DUPLICATE_SEMANTIC_ID',semantic_id:node.id,message:'语义 ID 重复'});ids.add(node.id);
    for(const ref of refsIn(node)){if(!symbols[ref]&&!index.has(ref)&&!ref.startsWith('error.')&&!ref.startsWith('event.')&&!ref.startsWith('evidence.'))errors.push({code:'BROKEN_REFERENCE',semantic_id:node.id,message:`引用不存在: ${ref}`})}
    for(const key of ['expression','when','guard','condition'])if(node[key]?.op)validateExpression(node[key],symbols,errors,node.id,key);
    if(node.kind==='action'&&node.operation==='assign'){const l=validateTypedValue(node.target,symbols,errors,node.id,'target'),r=validateTypedValue(node.value,symbols,errors,node.id,'value');if(!compatibleTypes(l,r))errors.push({code:'TYPE_MISMATCH',semantic_id:node.id,message:`赋值类型 ${l} 与 ${r} 不兼容`})}
    if(node.kind==='scenario'){for(const section of ['given','then'])for(let i=0;i<(node[section]??[]).length;i++){const a=node[section][i],l=validateTypedValue(a.target,symbols,errors,node.id,`${section}[${i}].target`),r=validateTypedValue(a.value,symbols,errors,node.id,`${section}[${i}].value`);if(!compatibleTypes(l,r))errors.push({code:'TYPE_MISMATCH',semantic_id:node.id,message:`Scenario ${section} 类型不兼容`})}for(const ref of node.when??[])if(!index.has(ref))errors.push({code:'BROKEN_REFERENCE',semantic_id:node.id,message:`Scenario when 引用不存在: ${ref}`})}
    if(node.origin==='observed'&&!(node.evidence_refs??[]).length)errors.push({code:'MISSING_EVIDENCE',semantic_id:node.id,message:'observed 节点必须绑定证据'});
  }
  const transitions=[...iterNodes(document)].map(x=>x[1]).filter(x=>x.kind==='transition'),forbidden=new Set([...iterNodes(document)].map(x=>x[1]).filter(x=>x.kind==='forbidden_transition').map(x=>`${x.from}->${x.to}`));for(const t of transitions)if(forbidden.has(`${t.from}->${t.to}`))errors.push({code:'FORBIDDEN_TRANSITION_CONFLICT',semantic_id:t.id,message:`${t.from} → ${t.to} 同时允许和禁止`});
  return{valid:!errors.length,errors,warnings,stats:{nodes:ids.size,symbols:Object.keys(symbols).length,version:root.version}}
}

function renderValue(value){const v=unwrapValue(value);if(v&&typeof v==='object'&&v.ref)return v.ref;if(Array.isArray(v))return v.map(x=>`“${x}”`).join('、');return String(v)}
function renderExpression(expr){if(!expr?.op)return String(expr??'');if(expr.op==='all')return expr.items.map(renderExpression).join('，并且');if(expr.op==='any')return expr.items.map(renderExpression).join('，或者');if(expr.op==='not')return`不满足（${renderExpression(expr.item)}）`;const labels={eq:'等于',ne:'不等于',lt:'小于',le:'小于等于',gt:'大于',ge:'大于等于',in:'属于',not_in:'不属于'};return`${renderValue(expr.left)}${labels[expr.op]??expr.op}${renderValue(expr.right)}`}
function renderHuman(document){const root=rootOf(document),index=buildNodeIndex(document),chunks=[`# ${root.name??root.id} — 人类可读逻辑`,''];for(const b of root.behaviors??[]){chunks.push(`## ${b.name??b.id}`,'',`标识：\`${b.id}\``);if((b.preconditions??[]).length){chunks.push('','### 前置条件');for(const ref of b.preconditions){const rule=index.get(ref);chunks.push(`- ${rule?.expression?renderExpression(rule.expression):ref}。`)}}if((b.flow??[]).length){chunks.push('','### 处理过程');let n=1;for(const ref of b.flow){const node=index.get(ref);let text=ref;if(node?.kind==='action'&&node.operation==='assign')text=`将 ${renderValue(node.target)} 设置为 ${renderValue(node.value)}`;chunks.push(`${n++}. ${text}。`)}}chunks.push('')}for(const s of root.scenarios??[]){chunks.push(`## 场景：${s.name??s.id}`,'');for(const a of s.given??[])chunks.push(`- 已知：${renderValue(a.target)} = ${renderValue(a.value)}`);chunks.push(`- 当：${(s.when??[]).join('、')}`);for(const a of s.then??[])chunks.push(`- 则：${renderValue(a.target)} = ${renderValue(a.value)}`);chunks.push('')}return chunks.join('\n')}

function testVectors(document){
  const root=rootOf(document),index=buildNodeIndex(document),symbols=buildSymbolTable(document),vectors=[];
  for(const node of index.values()){
    if(node.kind==='rule'&&['in','not_in'].includes(node.expression?.op)){
      const subject=valueRef(node.expression.left),declared=unwrapValue(node.expression.right);if(subject&&Array.isArray(declared)){const expectedDeclared=node.expression.op==='in';for(const value of declared)vectors.push({id:`test.${node.id}.declared.${value}`,source_semantic_id:node.id,kind:expectedDeclared?'rule_positive':'rule_negative',given:{[subject]:value},when:null,expect:{rule_result:expectedDeclared}});const type=symbols[subject]?.type,universe=symbols[type]?.enum_values??[];for(const value of universe.filter(x=>!declared.includes(x))){const expected=node.expression.op==='not_in';vectors.push({id:`test.${node.id}.complement.${value}`,source_semantic_id:node.id,kind:expected?'rule_positive':'rule_negative',given:{[subject]:value},when:null,expect:{rule_result:expected}})}}
    }else if(node.kind==='rule'&&node.expression?.op){vectors.push({id:`test.${node.id}.expression`,source_semantic_id:node.id,kind:'rule_expression_intent',given:{expression:node.expression},when:null,expect:{evaluate_expression:true}})}
    if(node.kind==='scenario'){const map=items=>Object.fromEntries((items??[]).map(a=>[valueRef(a.target),unwrapValue(a.value)]).filter(([k])=>k));vectors.push({id:`test.${node.id}.example`,source_semantic_id:node.id,kind:'scenario',given:map(node.given),when:{behaviors:node.when??[]},expect:map(node.then)})}
    if(node.kind==='transition')vectors.push({id:`test.${node.id}.allowed`,source_semantic_id:node.id,kind:'state_transition',given:{state:node.from},when:{trigger:node.trigger},expect:{state:node.to}});
    if(node.kind==='forbidden_transition')vectors.push({id:`test.${node.id}.forbidden`,source_semantic_id:node.id,kind:'forbidden_state_transition',given:{state:node.from},when:{target_state:node.to},expect:{allowed:false}});
    if(['invariant','precondition','postcondition','constraint'].includes(node.kind)&&node.expression)vectors.push({id:`test.${node.id}.property`,source_semantic_id:node.id,kind:'property_intent',given:{},when:null,expect:{property:node.expression}});
  }
  return{source_clm:root.id,test_vector_version:'0.2',vectors,warnings:vectors.length?[]:['当前模型没有生成测试向量']}
}

function validateIir(document){
  const root=document.iir??document,errors=[],warnings=[];if(String(root.version)!=='0.2')errors.push({code:'IIR_VERSION',message:'IIR version 必须为 0.2'});
  const deps=new Set([...(root.repository_contracts??[]),...(root.external_ports??[])].map(x=>x.id));for(const uc of root.use_cases??[])for(const dep of uc.dependencies??[])if(!deps.has(dep))errors.push({code:'IIR_BROKEN_DEPENDENCY',message:`${uc.id} 依赖不存在: ${dep}`});
  const trace=new Set((root.traceability??[]).map(x=>x.implementation_id));for(const uc of root.use_cases??[])if(!trace.has(uc.id))errors.push({code:'IIR_MISSING_TRACEABILITY',message:`${uc.id} 缺少 traceability`});
  for(const item of root.unresolved??[]){const blocking=typeof item==='string'||item?.severity==='blocking'||item?.blocking===true;if(blocking)errors.push({code:'IIR_BLOCKING_UNRESOLVED',message:typeof item==='string'?item:item.semantic_ref??item.reason});else warnings.push({code:'IIR_UNRESOLVED_WARNING',message:item?.semantic_ref??item?.reason})}
  return{valid:!errors.length,errors,warnings}
}
function verifyManifest(directory){const manifest=readJson(path.join(directory,'manifest.json')),errors=[];for(const artifact of manifest.artifacts??[]){const file=path.join(directory,artifact.path);if(!fs.existsSync(file)){errors.push({code:'GENERATED_FILE_MISSING',path:artifact.path});continue}const contentHash=crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');if(contentHash!==artifact.content_hash)errors.push({code:'GENERATED_FILE_DRIFT',path:artifact.path})}return{valid:!errors.length,errors}}
function usage(){console.log(`logic_cli.mjs <command>\n\ncommands:\n  validate-clm\n  symbols\n  hash\n  render\n  test-vectors\n  validate-iir\n  verify-manifest`)}

const [command,...args]=process.argv.slice(2);
try{
  if(command==='validate-clm'){const result=validateClm(readJson(args[0]));console.log(JSON.stringify(result,null,2));process.exit(result.valid?0:1)}
  if(command==='symbols'){const output=option(args,'-o','--output');if(!output)fail('symbols 需要 -o/--output');writeJson(output,{symbols:buildSymbolTable(readJson(args[0]))})}
  else if(command==='hash')console.log(semanticHash(readJson(args[0])));
  else if(command==='render'){const text=renderHuman(readJson(args[0])),output=option(args,'-o','--output');if(output){fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,text,'utf8')}else console.log(text)}
  else if(command==='test-vectors'){const result=testVectors(readJson(args[0])),output=option(args,'-o','--output');if(output)writeJson(output,result);else console.log(JSON.stringify(result,null,2))}
  else if(command==='validate-iir'){const result=validateIir(readJson(args[0]));console.log(JSON.stringify(result,null,2));process.exit(result.valid?0:1)}
  else if(command==='verify-manifest'){const result=verifyManifest(args[0]);console.log(JSON.stringify(result,null,2));process.exit(result.valid?0:1)}
  else{usage();process.exit(command?1:0)}
}catch(error){fail(error.message,{stack:error.stack})}
