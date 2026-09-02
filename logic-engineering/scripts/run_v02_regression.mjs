#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {readJson} from './lib/model.mjs';
const DIR=path.dirname(new URL(import.meta.url).pathname),ROOT=path.resolve(DIR,'..'),FIX=path.join(ROOT,'evals','fixtures'),SCHEMAS=path.join(ROOT,'schemas');
function run(script,args,label){const p=spawnSync(process.execPath,[path.join(DIR,script),...args],{encoding:'utf8'});return{label,ok:p.status===0,returncode:p.status,stdout:(p.stdout??'').slice(-1500),stderr:(p.stderr??'').slice(-1500)}}
function assertCheck(label,ok){return{label,ok,returncode:ok?0:1,stdout:'',stderr:''}}
const model=path.join(FIX,'order-cancel.v0.2.valid.json'),decisionModel=path.join(FIX,'order-routing.decision.v0.2.json'),foreachModel=path.join(FIX,'order-items.foreach.v0.2.json'),profile=path.join(FIX,'ts-sqlite.target-profile.json'),change=path.join(FIX,'order-cancel.add-paid.change-set.json'),tmp=fs.mkdtempSync(path.join(os.tmpdir(),'logic-v02-reg-')),checks=[];

checks.push(run('schema_validate.mjs',[model,path.join(SCHEMAS,'clm-v0.2.schema.json')],'CLM Schema'));
checks.push(run('validate_clm.mjs',[model],'CLM Semantic'));
checks.push(run('logic_cli.mjs',['render',model,'-o',path.join(tmp,'human.md')],'中文逻辑投影'));
checks.push(run('logic_cli.mjs',['test-vectors',model,'-o',path.join(tmp,'tests.json')],'测试向量生成'));
checks.push(run('logic_cli.mjs',['symbols',model,'-o',path.join(tmp,'symbols.json')],'Symbol Table'));
checks.push(run('logic_cli.mjs',['hash',model],'Semantic Hash'));
checks.push(run('compile_iir.mjs',[model,profile,'-o',path.join(tmp,'iir.json')],'IIR v0.2 编译'));
checks.push(run('schema_validate.mjs',[path.join(tmp,'iir.json'),path.join(SCHEMAS,'iir-v0.2.schema.json')],'IIR Schema'));
checks.push(run('validate_iir.mjs',[path.join(tmp,'iir.json')],'IIR Semantic'));
checks.push(run('compile_target_tests.mjs',[path.join(tmp,'tests.json'),path.join(tmp,'iir.json'),'-o',path.join(tmp,'target-tests.json')],'Target Test Plan v0.2'));
checks.push(run('generate_typescript_v02.mjs',[path.join(tmp,'iir.json'),path.join(tmp,'target-tests.json'),'-o',path.join(tmp,'generated-ts')],'TypeScript + SQLite v0.2 生成'));
checks.push(run('logic_cli.mjs',['verify-manifest',path.join(tmp,'generated-ts')],'Manifest 漂移校验'));
checks.push(run('validate_generated_typescript.mjs',[path.join(tmp,'generated-ts')],'TypeScript 生成质量'));
checks.push(run('apply_change_set.mjs',[model,change,'-o',path.join(tmp,'changed.json'),'--diff-output',path.join(tmp,'change-diff.json')],'Change Set 原子应用'));
checks.push(run('schema_validate.mjs',[path.join(tmp,'changed.json'),path.join(SCHEMAS,'clm-v0.2.schema.json')],'变更后 CLM Schema'));
checks.push(run('validate_clm.mjs',[path.join(tmp,'changed.json')],'变更后 CLM Semantic'));
checks.push(run('run_pipeline.mjs',[model,'--change-set',change,'--target-profile',profile,'--generate-ts','--output-dir',path.join(tmp,'pipeline')],'端到端 Node 流水线'));
let scenario=false,domainTypes=false,planExecutable=false;
try{scenario=(readJson(path.join(tmp,'tests.json')).vectors??[]).some(v=>v.kind==='scenario'&&v.given&&v.expect);const iir=readJson(path.join(tmp,'iir.json')).iir;domainTypes=Array.isArray(iir?.domain_types?.enums)&&Array.isArray(iir?.runtime_bindings);const plan=readJson(path.join(tmp,'target-tests.json')).target_test_plan;planExecutable=(plan?.summary?.executable??0)>=1}catch{}
checks.push(assertCheck('Typed Scenario 标准测试向量',scenario));
checks.push(assertCheck('IIR Runtime Bindings',domainTypes));
checks.push(assertCheck('Target Test Plan 可执行 case',planExecutable));

const decisionDir=path.join(tmp,'decision');fs.mkdirSync(decisionDir,{recursive:true});
checks.push(run('schema_validate.mjs',[decisionModel,path.join(SCHEMAS,'clm-v0.2.schema.json')],'Decision CLM Schema'));
checks.push(run('validate_clm.mjs',[decisionModel],'Decision CLM Semantic'));
checks.push(run('logic_cli.mjs',['test-vectors',decisionModel,'-o',path.join(decisionDir,'tests.json')],'Decision 测试向量'));
checks.push(run('compile_iir.mjs',[decisionModel,profile,'-o',path.join(decisionDir,'iir.json')],'Decision IIR 编译'));
checks.push(run('schema_validate.mjs',[path.join(decisionDir,'iir.json'),path.join(SCHEMAS,'iir-v0.2.schema.json')],'Decision IIR Schema'));
checks.push(run('validate_iir.mjs',[path.join(decisionDir,'iir.json')],'Decision IIR Semantic'));
checks.push(run('compile_target_tests.mjs',[path.join(decisionDir,'tests.json'),path.join(decisionDir,'iir.json'),'-o',path.join(decisionDir,'target-tests.json')],'Decision Target Test Plan'));
checks.push(run('generate_typescript_v02.mjs',[path.join(decisionDir,'iir.json'),path.join(decisionDir,'target-tests.json'),'-o',path.join(decisionDir,'generated-ts')],'Decision TypeScript 生成'));
checks.push(run('validate_generated_typescript.mjs',[path.join(decisionDir,'generated-ts')],'Decision TypeScript 质量'));
let decisionExpanded=false,ifElse=false,decisionTests=false;
try{
  const iir=readJson(path.join(decisionDir,'iir.json')).iir,step=iir.use_cases?.[0]?.steps?.[0];decisionExpanded=step?.kind==='decision'&&step.then_steps?.[0]?.semantic_ref==='action.order.route.fast'&&step.else_steps?.[0]?.semantic_ref==='action.order.route.standard';
  const source=fs.readFileSync(path.join(decisionDir,'generated-ts','usecases','generated.ts'),'utf8');ifElse=source.includes('if (')&&source.includes('} else {')&&source.includes(' = "FAST";')&&source.includes(' = "STANDARD";');
  const plan=readJson(path.join(decisionDir,'target-tests.json')).target_test_plan;decisionTests=plan.summary?.executable===2;
}catch{}
checks.push(assertCheck('IIR Decision 展开 then/else',decisionExpanded));
checks.push(assertCheck('TypeScript Decision 生成 if/else',ifElse));
checks.push(assertCheck('Decision 两个 Scenario 可执行',decisionTests));

const foreachDir=path.join(tmp,'foreach');fs.mkdirSync(foreachDir,{recursive:true});
checks.push(run('schema_validate.mjs',[foreachModel,path.join(SCHEMAS,'clm-v0.2.schema.json')],'Foreach CLM Schema'));
checks.push(run('validate_clm.mjs',[foreachModel],'Foreach CLM Semantic'));
checks.push(run('logic_cli.mjs',['test-vectors',foreachModel,'-o',path.join(foreachDir,'tests.json')],'Foreach 测试向量'));
checks.push(run('compile_iir.mjs',[foreachModel,profile,'-o',path.join(foreachDir,'iir.json')],'Foreach IIR 编译'));
checks.push(run('schema_validate.mjs',[path.join(foreachDir,'iir.json'),path.join(SCHEMAS,'iir-v0.2.schema.json')],'Foreach IIR Schema'));
checks.push(run('validate_iir.mjs',[path.join(foreachDir,'iir.json')],'Foreach IIR Semantic'));
checks.push(run('compile_target_tests.mjs',[path.join(foreachDir,'tests.json'),path.join(foreachDir,'iir.json'),'-o',path.join(foreachDir,'target-tests.json')],'Foreach Target Test Plan'));
checks.push(run('generate_typescript_v02.mjs',[path.join(foreachDir,'iir.json'),path.join(foreachDir,'target-tests.json'),'-o',path.join(foreachDir,'generated-ts')],'Foreach TypeScript 生成'));
checks.push(run('validate_generated_typescript.mjs',[path.join(foreachDir,'generated-ts')],'Foreach TypeScript 质量'));
let foreachIir=false,foreachTs=false,arrayType=false,collectionVector=false,collectionExecutable=false,deepAssertion=false;
try{
  const iir=readJson(path.join(foreachDir,'iir.json')).iir,step=iir.use_cases?.[0]?.steps?.[0];foreachIir=step?.kind==='foreach'&&step.collection_ref==='domain.order.items'&&step.item_alias==='item'&&step.item_type==='domain.order_item'&&step.do_steps?.[0]?.scope?.alias==='item';
  const domain=fs.readFileSync(path.join(foreachDir,'generated-ts','domain','generated.ts'),'utf8'),source=fs.readFileSync(path.join(foreachDir,'generated-ts','usecases','generated.ts'),'utf8'),testsSource=fs.readFileSync(path.join(foreachDir,'generated-ts','tests','generated.test.ts'),'utf8');arrayType=domain.includes('items: OrderItem[];');foreachTs=source.includes('for (const item of input.order.items)')&&source.includes('if (!(item.reserved === true)) continue;')&&source.includes('item.released = true;');
  const vectors=readJson(path.join(foreachDir,'tests.json')).vectors??[],vector=vectors.find(v=>v.source_semantic_id==='scenario.order.release_reserved_items');collectionVector=Array.isArray(vector?.given?.['domain.order.items'])&&vector.given['domain.order.items'].length===2&&vector.expect?.['domain.order.items']?.[0]?.released===true;
  const plan=readJson(path.join(foreachDir,'target-tests.json')).target_test_plan;collectionExecutable=plan.summary?.executable===1;
  deepAssertion=testsSource.includes('expect(order.items).toEqual(')&&testsSource.includes('"released":true');
}catch{}
checks.push(assertCheck('IIR Foreach 保留 typed item scope',foreachIir));
checks.push(assertCheck('TypeScript 多值字段生成数组类型',arrayType));
checks.push(assertCheck('TypeScript Foreach 生成局部循环逻辑',foreachTs));
checks.push(assertCheck('结构化集合 Scenario 生成数组 Test Vector',collectionVector));
checks.push(assertCheck('Foreach Scenario 可执行',collectionExecutable));
checks.push(assertCheck('集合预期使用 Vitest 深比较',deepAssertion));

const ok=checks.every(x=>x.ok);console.log(JSON.stringify({ok,checks},null,2));fs.rmSync(tmp,{recursive:true,force:true});process.exit(ok?0:1);
