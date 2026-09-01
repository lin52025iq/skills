#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {readJson} from './lib/model.mjs';
const DIR=path.dirname(new URL(import.meta.url).pathname),ROOT=path.resolve(DIR,'..'),FIX=path.join(ROOT,'evals','fixtures'),SCHEMAS=path.join(ROOT,'schemas');
function run(script,args,label){const p=spawnSync(process.execPath,[path.join(DIR,script),...args],{encoding:'utf8'});return {label,ok:p.status===0,returncode:p.status,stdout:(p.stdout??'').slice(-1500),stderr:(p.stderr??'').slice(-1500)}}
const model=path.join(FIX,'order-cancel.v0.2.valid.json'),profile=path.join(FIX,'ts-sqlite.target-profile.json'),change=path.join(FIX,'order-cancel.add-paid.change-set.json'),tmp=fs.mkdtempSync(path.join(os.tmpdir(),'logic-v02-reg-')),checks=[];
checks.push(run('schema_validate.mjs',[model,path.join(SCHEMAS,'clm-v0.2.schema.json')],'CLM Schema'));
checks.push(run('logic_cli.mjs',['validate-clm',model],'CLM Semantic'));
checks.push(run('logic_cli.mjs',['render',model,'-o',path.join(tmp,'human.md')],'中文逻辑投影'));
checks.push(run('logic_cli.mjs',['test-vectors',model,'-o',path.join(tmp,'tests.json')],'测试向量生成'));
checks.push(run('logic_cli.mjs',['symbols',model,'-o',path.join(tmp,'symbols.json')],'Symbol Table'));
checks.push(run('logic_cli.mjs',['hash',model],'Semantic Hash'));
checks.push(run('compile_iir.mjs',[model,profile,'-o',path.join(tmp,'iir.json')],'IIR v0.2 编译'));
checks.push(run('schema_validate.mjs',[path.join(tmp,'iir.json'),path.join(SCHEMAS,'iir-v0.2.schema.json')],'IIR Schema'));
checks.push(run('logic_cli.mjs',['validate-iir',path.join(tmp,'iir.json')],'IIR Semantic'));
checks.push(run('logic_cli.mjs',['target-tests',path.join(tmp,'tests.json'),path.join(tmp,'iir.json'),'-o',path.join(tmp,'target-tests.json')],'Target Test Plan'));
checks.push(run('generate_typescript.mjs',[path.join(tmp,'iir.json'),path.join(tmp,'target-tests.json'),'-o',path.join(tmp,'generated-ts')],'TypeScript + SQLite 生成'));
checks.push(run('logic_cli.mjs',['verify-manifest',path.join(tmp,'generated-ts')],'Manifest 漂移校验'));
checks.push(run('apply_change_set.mjs',[model,change,'-o',path.join(tmp,'changed.json'),'--diff-output',path.join(tmp,'change-diff.json')],'Change Set 原子应用'));
checks.push(run('schema_validate.mjs',[path.join(tmp,'changed.json'),path.join(SCHEMAS,'clm-v0.2.schema.json')],'变更后 CLM Schema'));
checks.push(run('logic_cli.mjs',['validate-clm',path.join(tmp,'changed.json')],'变更后 CLM Semantic'));
checks.push(run('run_pipeline.mjs',[model,'--change-set',change,'--target-profile',profile,'--generate-ts','--output-dir',path.join(tmp,'pipeline')],'端到端 Node 流水线'));
let scenario=false,domainTypes=false;try{scenario=(readJson(path.join(tmp,'tests.json')).vectors??[]).some(v=>v.kind==='scenario'&&v.given&&v.expect);const iir=readJson(path.join(tmp,'iir.json')).iir;domainTypes=Array.isArray(iir?.domain_types?.enums)&&Array.isArray(iir?.runtime_bindings)}catch{}
checks.push({label:'Typed Scenario 标准测试向量',ok:scenario,returncode:scenario?0:1,stdout:'',stderr:''});
checks.push({label:'IIR Runtime Bindings',ok:domainTypes,returncode:domainTypes?0:1,stdout:'',stderr:''});
const ok=checks.every(x=>x.ok);console.log(JSON.stringify({ok,checks},null,2));fs.rmSync(tmp,{recursive:true,force:true});process.exit(ok?0:1);
