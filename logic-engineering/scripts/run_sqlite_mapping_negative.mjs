#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {readJson} from './lib/model.mjs';

const DIR=path.dirname(new URL(import.meta.url).pathname),ROOT=path.resolve(DIR,'..'),FIX=path.join(ROOT,'evals','fixtures'),SCHEMAS=path.join(ROOT,'schemas');
function run(script,args,expected=0){return spawnSync(process.execPath,[path.join(DIR,script),...args],{encoding:'utf8'}).status===expected;}

const model=path.join(FIX,'order-cancel.v0.2.valid.json');
const profile=path.join(FIX,'ts-sqlite.missing-column.target-profile.json');
const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'logic-sqlite-negative-'));
const iirFile=path.join(tmp,'iir.json');
let ok=true;
ok=run('schema_validate.mjs',[profile,path.join(SCHEMAS,'target-profile-v0.1.schema.json')])&&ok;
ok=run('compile_iir.mjs',[model,profile,'-o',iirFile])&&ok;
ok=run('validate_iir.mjs',[iirFile],1)&&ok;
let detected=false;
try{
  const unresolved=readJson(iirFile).iir?.unresolved??[];
  detected=unresolved.some(x=>x.severity==='blocking'&&x.semantic_ref==='domain.order.owner_id'&&String(x.reason).includes('缺少字段 column'));
}catch{}
ok=ok&&detected;
console.log(JSON.stringify({ok,missing_column_detected:detected},null,2));
fs.rmSync(tmp,{recursive:true,force:true});
process.exit(ok?0:1);
