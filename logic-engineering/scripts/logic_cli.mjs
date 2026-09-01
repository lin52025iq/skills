#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {readJson,writeJson,rootOf,buildNodeIndex,buildSymbolTable,semanticHash,unwrapValue,valueRef} from './lib/model.mjs';

function fail(message,extra={}){console.error(JSON.stringify({ok:false,error:message,...extra},null,2));process.exit(1);}
function option(args,...names){for(const name of names){const i=args.indexOf(name);if(i>=0)return args[i+1]??null;}return null;}
function pretty(value){if(value&&typeof value==='object'&&value.ref)return value.ref;if(Array.isArray(value))return`[${value.map(pretty).join('，')}]`;if(value&&typeof value==='object')return`{${Object.entries(value).map(([k,v])=>`${k}: ${pretty(v)}`).join('，')}}`;if(typeof value==='string')return`“${value}”`;if(value===null)return'空值';return String(value);}
function renderValue(value){return pretty(unwrapValue(value));}
function renderExpression(expr){if(!expr?.op)return String(expr??'');if(expr.op==='all')return expr.items.map(renderExpression).join('，并且');if(expr.op==='any')return expr.items.map(renderExpression).join('，或者');if(expr.op==='not')return`不满足（${renderExpression(expr.item)}）`;const labels={eq:'等于',ne:'不等于',lt:'小于',le:'小于等于',gt:'大于',ge:'大于等于',in:'属于',not_in:'不属于'};return`${renderValue(expr.left)}${labels[expr.op]??expr.op}${renderValue(expr.right)}`;}
function renderStep(ref,index,depth=0){
  const node=index.get(ref),pad='  '.repeat(depth);if(!node)return`${pad}${ref}`;
  if(node.kind==='action'&&node.operation==='assign')return`${pad}将 ${renderValue(node.target)} 设置为 ${renderValue(node.value)}`;
  if(node.kind==='decision'){
    const lines=[`${pad}如果 ${renderExpression(node.when)}：`];for(const x of node.then??[])lines.push(renderStep(x,index,depth+1));if((node.else??[]).length){lines.push(`${pad}否则：`);for(const x of node.else)lines.push(renderStep(x,index,depth+1));}return lines.join('\n');
  }
  if(node.kind==='foreach'){
    const lines=[`${pad}遍历 ${renderValue(node.collection)}，当前项记为 ${node.item}${node.when?`，仅处理满足「${renderExpression(node.when)}」的项`:''}：`];for(const x of node.do??[])lines.push(renderStep(x,index,depth+1));return lines.join('\n');
  }
  return`${pad}${node.name??node.id}`;
}
function renderHuman(document){
  const root=rootOf(document),index=buildNodeIndex(document),chunks=[`# ${root.name??root.id} — 人类可读逻辑`,''];
  for(const behavior of root.behaviors??[]){
    chunks.push(`## ${behavior.name??behavior.id}`,'',`标识：\`${behavior.id}\``);
    if((behavior.preconditions??[]).length){chunks.push('','### 前置条件');for(const ref of behavior.preconditions){const rule=index.get(ref);chunks.push(`- ${rule?.expression?renderExpression(rule.expression):ref}。`);}}
    if((behavior.flow??[]).length){chunks.push('','### 处理过程');let n=1;for(const ref of behavior.flow){const text=renderStep(ref,index),lines=text.split('\n');chunks.push(`${n}. ${lines[0]}`,...lines.slice(1).map(x=>`   ${x}`));n++;}}
    chunks.push('');
  }
  for(const scenario of root.scenarios??[]){chunks.push(`## 场景：${scenario.name??scenario.id}`,'');for(const a of scenario.given??[])chunks.push(`- 已知：${renderValue(a.target)} = ${renderValue(a.value)}`);chunks.push(`- 当：${(scenario.when??[]).join('、')}`);for(const a of scenario.then??[]){if(a.target&&a.value)chunks.push(`- 则：${renderValue(a.target)} = ${renderValue(a.value)}`);else if(a.expression)chunks.push(`- 则满足：${renderExpression(a.expression)}`);}chunks.push('');}
  return chunks.join('\n');
}
function collectStepEffects(ref,index,out=new Set(),seen=new Set()){
  if(seen.has(ref))return out;seen.add(ref);const node=index.get(ref);if(!node)return out;
  for(const effect of node.effects??[])out.add(effect);
  if(node.kind==='decision'){for(const child of node.then??[])collectStepEffects(child,index,out,seen);for(const child of node.else??[])collectStepEffects(child,index,out,seen);}
  if(node.kind==='foreach')for(const child of node.do??[])collectStepEffects(child,index,out,seen);
  return out;
}
function scenarioEffects(scenario,index){
  const effects=new Set();
  for(const behaviorRef of scenario.when??[]){const behavior=index.get(behaviorRef);if(behavior?.kind!=='behavior')continue;for(const stepRef of behavior.flow??[])collectStepEffects(stepRef,index,effects,new Set());}
  return[...effects];
}
function testVectors(document){
  const root=rootOf(document),index=buildNodeIndex(document),symbols=buildSymbolTable(document),vectors=[];
  for(const node of index.values()){
    if(node.kind==='rule'&&['in','not_in'].includes(node.expression?.op)){
      const subject=valueRef(node.expression.left),declared=unwrapValue(node.expression.right);
      if(subject&&Array.isArray(declared)){
        const expectedDeclared=node.expression.op==='in';for(const value of declared)vectors.push({id:`test.${node.id}.declared.${value}`,source_semantic_id:node.id,kind:expectedDeclared?'rule_positive':'rule_negative',given:{[subject]:value},when:null,expect:{rule_result:expectedDeclared}});
        const type=symbols[subject]?.type,universe=symbols[type]?.enum_values??[];for(const value of universe.filter(x=>!declared.includes(x))){const expected=node.expression.op==='not_in';vectors.push({id:`test.${node.id}.complement.${value}`,source_semantic_id:node.id,kind:expected?'rule_positive':'rule_negative',given:{[subject]:value},when:null,expect:{rule_result:expected}});}
      }
    }else if(node.kind==='rule'&&node.expression?.op){vectors.push({id:`test.${node.id}.expression`,source_semantic_id:node.id,kind:'rule_expression_intent',given:{expression:node.expression},when:null,expect:{evaluate_expression:true}});}
    if(node.kind==='scenario'){
      const map=(items)=>Object.fromEntries((items??[]).filter(x=>x.target&&x.value).map(a=>[valueRef(a.target),unwrapValue(a.value)]).filter(([key])=>key));
      vectors.push({id:`test.${node.id}.example`,source_semantic_id:node.id,kind:'scenario',given:map(node.given),when:{behaviors:node.when??[]},expect:map(node.then),expected_effects:scenarioEffects(node,index)});
    }
    if(node.kind==='transition')vectors.push({id:`test.${node.id}.allowed`,source_semantic_id:node.id,kind:'state_transition',given:{state:node.from},when:{trigger:node.trigger},expect:{state:node.to}});
    if(node.kind==='forbidden_transition')vectors.push({id:`test.${node.id}.forbidden`,source_semantic_id:node.id,kind:'forbidden_state_transition',given:{state:node.from},when:{target_state:node.to},expect:{allowed:false}});
    if(['invariant','precondition','postcondition','constraint'].includes(node.kind)&&node.expression)vectors.push({id:`test.${node.id}.property`,source_semantic_id:node.id,kind:'property_intent',given:{},when:null,expect:{property:node.expression}});
  }
  return{source_clm:root.id,test_vector_version:'0.2',vectors,warnings:vectors.length?[]:['当前模型没有生成测试向量']};
}
function verifyManifest(directory){
  const manifest=readJson(path.join(directory,'manifest.json')),errors=[];
  for(const artifact of manifest.artifacts??[]){const file=path.join(directory,artifact.path);if(!fs.existsSync(file)){errors.push({code:'GENERATED_FILE_MISSING',path:artifact.path});continue;}const contentHash=crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');if(contentHash!==artifact.content_hash)errors.push({code:'GENERATED_FILE_DRIFT',path:artifact.path});}
  return{valid:!errors.length,errors};
}
function usage(){console.log(`logic_cli.mjs <command>\n\ncommands:\n  symbols\n  hash\n  render\n  test-vectors\n  verify-manifest`);}

const [command,...args]=process.argv.slice(2);
try{
  if(command==='symbols'){const output=option(args,'-o','--output');if(!output)fail('symbols 需要 -o/--output');writeJson(output,{symbols:buildSymbolTable(readJson(args[0]))});}
  else if(command==='hash')console.log(semanticHash(readJson(args[0])));
  else if(command==='render'){const text=renderHuman(readJson(args[0])),output=option(args,'-o','--output');if(output){fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,text,'utf8');}else console.log(text);}
  else if(command==='test-vectors'){const result=testVectors(readJson(args[0])),output=option(args,'-o','--output');if(output)writeJson(output,result);else console.log(JSON.stringify(result,null,2));}
  else if(command==='verify-manifest'){const result=verifyManifest(args[0]);console.log(JSON.stringify(result,null,2));process.exit(result.valid?0:1);}
  else{usage();process.exit(command?1:0);}
}catch(error){fail(error.message,{stack:error.stack});}
