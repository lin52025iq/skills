#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {readJson} from './lib/model.mjs';

const DIR=path.dirname(new URL(import.meta.url).pathname),ROOT=path.resolve(DIR,'..'),FIX=path.join(ROOT,'evals','fixtures'),SCHEMAS=path.join(ROOT,'schemas');
function run(script,args,label){const p=spawnSync(process.execPath,[path.join(DIR,script),...args],{encoding:'utf8'});return{label,ok:p.status===0,returncode:p.status,stdout:(p.stdout??'').slice(-1500),stderr:(p.stderr??'').slice(-1500)}}
function assertCheck(label,ok){return{label,ok,returncode:ok?0:1,stdout:'',stderr:''}}

const model=path.join(FIX,'order-cancel.v0.2.valid.json'),profile=path.join(FIX,'ts-sqlite.target-profile.json'),tmp=fs.mkdtempSync(path.join(os.tmpdir(),'logic-sqlite-reg-')),checks=[];
checks.push(run('schema_validate.mjs',[profile,path.join(SCHEMAS,'target-profile-v0.1.schema.json')],'Target Profile Schema'));
checks.push(run('logic_cli.mjs',['test-vectors',model,'-o',path.join(tmp,'tests.json')],'生成测试向量'));
checks.push(run('compile_iir.mjs',[model,profile,'-o',path.join(tmp,'iir.json')],'编译 SQLite IIR'));
checks.push(run('schema_validate.mjs',[path.join(tmp,'iir.json'),path.join(SCHEMAS,'iir-v0.2.schema.json')],'SQLite IIR Schema'));
checks.push(run('validate_iir.mjs',[path.join(tmp,'iir.json')],'SQLite IIR Semantic'));
checks.push(run('compile_target_tests.mjs',[path.join(tmp,'tests.json'),path.join(tmp,'iir.json'),'-o',path.join(tmp,'target-tests.json')],'编译 Target Test Plan'));
checks.push(run('generate_typescript_v02.mjs',[path.join(tmp,'iir.json'),path.join(tmp,'target-tests.json'),'-o',path.join(tmp,'generated-ts')],'生成 SQLite Adapter'));
checks.push(run('validate_generated_typescript.mjs',[path.join(tmp,'generated-ts')],'生成质量 Gate'));

let mapping=false,adapter=false;
try{
  const iir=readJson(path.join(tmp,'iir.json')).iir,repo=iir.repository_contracts?.find(x=>x.entity_ref==='domain.order'),m=repo?.binding?.mapping;
  mapping=m?.table==='orders'&&m?.primary_key==='domain.order.id'&&m?.columns?.['domain.order.id']==='id'&&m?.columns?.['domain.order.status']==='status'&&m?.columns?.['domain.order.owner_id']==='owner_id';
  const source=fs.readFileSync(path.join(tmp,'generated-ts','adapters','sqlite.ts'),'utf8');
  adapter=source.includes('class OrderSqliteRepository')&&source.includes('INSERT INTO \\"orders\\"')&&source.includes('ON CONFLICT(\\"id\\") DO UPDATE SET')&&source.includes('entity.id')&&source.includes('entity.status')&&source.includes('entity.ownerId');
}catch{}
checks.push(assertCheck('IIR 保留显式 SQLite mapping',mapping));
checks.push(assertCheck('TypeScript 生成稳定 SQLite upsert',adapter));

const ok=checks.every(x=>x.ok);console.log(JSON.stringify({ok,checks},null,2));fs.rmSync(tmp,{recursive:true,force:true});process.exit(ok?0:1);
