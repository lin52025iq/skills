#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {readJson} from './lib/model.mjs';

const DIR=path.dirname(new URL(import.meta.url).pathname),ROOT=path.resolve(DIR,'..'),FIX=path.join(ROOT,'evals','fixtures'),SCHEMAS=path.join(ROOT,'schemas');
function run(script,args,label,expected=0){const p=spawnSync(process.execPath,[path.join(DIR,script),...args],{encoding:'utf8'});return{label,ok:p.status===expected,returncode:p.status,stdout:(p.stdout??'').slice(-1200),stderr:(p.stderr??'').slice(-1200)}}
function check(label,ok){return{label,ok,returncode:ok?0:1,stdout:'',stderr:''}}

const model=path.join(FIX,'order-cancel.atomicity.v0.2.json'),partial=path.join(FIX,'order-cancel.atomicity.partial.v0.2.json'),profile=path.join(FIX,'ts-sqlite.target-profile.json'),tmp=fs.mkdtempSync(path.join(os.tmpdir(),'logic-tx-reg-')),checks=[];
const out=path.join(tmp,'positive');fs.mkdirSync(out,{recursive:true});
checks.push(run('schema_validate.mjs',[model,path.join(SCHEMAS,'clm-v0.2.schema.json')],'Atomicity CLM Schema'));
checks.push(run('validate_clm.mjs',[model],'Atomicity CLM Semantic'));
checks.push(run('logic_cli.mjs',['test-vectors',model,'-o',path.join(out,'tests.json')],'Atomicity Test Vector'));
checks.push(run('compile_iir.mjs',[model,profile,'-o',path.join(out,'iir.json')],'Atomicity IIR'));
checks.push(run('schema_validate.mjs',[path.join(out,'iir.json'),path.join(SCHEMAS,'iir-v0.2.schema.json')],'Atomicity IIR Schema'));
checks.push(run('validate_iir.mjs',[path.join(out,'iir.json')],'Atomicity IIR Semantic'));
checks.push(run('compile_target_tests.mjs',[path.join(out,'tests.json'),path.join(out,'iir.json'),'-o',path.join(out,'target-tests.json')],'Atomicity Target Tests'));
checks.push(run('generate_typescript_v02.mjs',[path.join(out,'iir.json'),path.join(out,'target-tests.json'),'-o',path.join(out,'generated-ts')],'Atomicity Base TS'));
checks.push(run('generate_typescript_transactions.mjs',[path.join(out,'iir.json'),path.join(out,'generated-ts')],'Atomicity Transaction Layer'));
checks.push(run('logic_cli.mjs',['verify-manifest',path.join(out,'generated-ts')],'Atomicity Manifest'));
checks.push(run('validate_generated_typescript.mjs',[path.join(out,'generated-ts')],'Atomicity TS Quality'));

let planOk=false,wrapperOk=false,runnerOk=false,manifestOk=false,tsconfigOk=false,entrypointOk=false,compositionOk=false;
try{
  const iir=readJson(path.join(out,'iir.json')).iir,uc=iir.use_cases?.[0],plan=iir.transaction_plans?.[0];
  planOk=plan?.behavior_ref==='behavior.order.cancel_atomic'&&plan?.boundary_valid===true&&plan?.start_index===0&&plan?.end_index===1&&uc?.transaction_plan_ids?.[0]===plan.id;
  const tx=fs.readFileSync(path.join(out,'generated-ts','transactions','generated.ts'),'utf8');
  wrapperOk=tx.includes('class TransactionalOrderCancelAtomicUseCase')&&tx.includes('this.transactions.transaction(async (executor) =>')&&tx.includes('const inner = this.createInner(executor)')&&tx.includes('await inner.execute(input)');
  runnerOk=tx.includes('class DefaultSqliteTransactionRunner')&&tx.includes('BEGIN IMMEDIATE')&&tx.includes('COMMIT')&&tx.includes('ROLLBACK')&&tx.includes('work(this.db)');
  const composition=fs.readFileSync(path.join(out,'generated-ts','composition','generated.ts'),'utf8');
  compositionOk=composition.includes('function createTransactionalOrderCancelAtomicUseCase')&&composition.includes('new OrderSqliteRepository(executor)')&&composition.includes('new OrderCancelAtomicUseCase(')&&composition.includes('new DefaultSqliteTransactionRunner(db)');
  const manifest=readJson(path.join(out,'generated-ts','manifest.json'));
  manifestOk=manifest.generator_layers?.includes('typescript-transaction-v0.4')&&manifest.artifacts?.some(x=>x.path==='transactions/generated.ts')&&manifest.artifacts?.some(x=>x.path==='composition/generated.ts')&&manifest.artifacts?.some(x=>x.path==='tests/generated.transaction.test.ts');
  entrypointOk=manifest.implementation_entrypoints?.some(x=>x.implementation_id===uc.id&&x.export_name==='createTransactionalOrderCancelAtomicUseCase'&&x.transaction_plan_id===plan.id&&x.artifact==='composition/generated.ts'&&x.fully_composed===true);
  const tsconfig=readJson(path.join(out,'generated-ts','tsconfig.json'));tsconfigOk=tsconfig.include?.includes('transactions/**/*.ts')&&tsconfig.include?.includes('composition/**/*.ts');
}catch{}
checks.push(check('IIR transaction plan 精确绑定行为',planOk));
checks.push(check('生成 transaction-scoped use case wrapper',wrapperOk));
checks.push(check('生成 BEGIN/COMMIT/ROLLBACK Transaction Runner',runnerOk));
checks.push(check('自动组合事务内 SQLite Repository',compositionOk));
checks.push(check('事务层写入 manifest',manifestOk));
checks.push(check('正式入口切换到 fully composed factory',entrypointOk));
checks.push(check('事务与 composition 纳入 tsconfig',tsconfigOk));

const neg=path.join(tmp,'negative');fs.mkdirSync(neg,{recursive:true});
checks.push(run('schema_validate.mjs',[partial,path.join(SCHEMAS,'clm-v0.2.schema.json')],'Partial Atomicity CLM Schema'));
checks.push(run('validate_clm.mjs',[partial],'Partial Atomicity CLM Semantic'));
checks.push(run('compile_iir.mjs',[partial,profile,'-o',path.join(neg,'iir.json')],'Partial Atomicity IIR'));
checks.push(run('validate_iir.mjs',[path.join(neg,'iir.json')],'Partial Atomicity 必须被 IIR Gate 拒绝',1));
let partialDetected=false;try{const p=spawnSync(process.execPath,[path.join(DIR,'validate_iir.mjs'),path.join(neg,'iir.json')],{encoding:'utf8'});const data=JSON.parse(p.stdout);partialDetected=data.errors?.some(x=>x.code==='IIR_TRANSACTION_SCOPE_UNSUPPORTED')}catch{}
checks.push(check('检测 full_behavior 覆盖不完整',partialDetected));

const ok=checks.every(x=>x.ok);console.log(JSON.stringify({ok,checks},null,2));fs.rmSync(tmp,{recursive:true,force:true});process.exit(ok?0:1);
