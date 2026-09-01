#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {readJson,writeJson} from './lib/model.mjs';
const DIR=path.dirname(new URL(import.meta.url).pathname);
function arg(name,args){const i=args.indexOf(name);return i>=0?args[i+1]:null}
function has(name,args){return args.includes(name)}
function run(script,args,label){const p=spawnSync(process.execPath,[path.join(DIR,script),...args],{encoding:'utf8'});if(p.status!==0){console.error(JSON.stringify({ok:false,stage:label,stdout:p.stdout,stderr:p.stderr},null,2));process.exit(p.status??1)}if(p.stdout?.trim())console.log(`[${label}]\n${p.stdout.trim()}`)}
const [model,...args]=process.argv.slice(2);if(!model){console.error('usage: node run_pipeline.mjs model.json [--patch p.json | --change-set c.json] [--target-profile profile.json] [--generate-ts] [--output-dir dir]');process.exit(2)}const out=arg('--output-dir',args)??'.logic-engineering-output',patch=arg('--patch',args),change=arg('--change-set',args),profile=arg('--target-profile',args);if(patch&&change){console.error('--patch 与 --change-set 不能同时使用');process.exit(2)}fs.mkdirSync(out,{recursive:true});let working=model;
run('logic_cli.mjs',['validate-clm',working],'校验原始 CLM');
let changed=[];
if(change){const updated=path.join(out,'updated.clm.json'),diff=path.join(out,'semantic-diff.json');run('apply_change_set.mjs',[working,change,'-o',updated,'--diff-output',diff],'应用语义变更集');working=updated;const d=readJson(diff);changed=d.changed_semantic_ids??[];run('logic_cli.mjs',['validate-clm',working],'校验更新后的 CLM');}
else if(patch){const payload=readJson(patch),p=payload.semantic_patch??payload,target=p.target_semantic_id;if(!target){console.error('Patch 缺少 target_semantic_id');process.exit(2)}const updated=path.join(out,'updated.clm.json');const doc=readJson(working);/* 单 Patch 通过临时 change set 走同一原子引擎 */const cs={change_set_id:`change.${p.patch_id??'single'}`,intent:p.intent??'单点修改',behavior_change_level:p.behavior_change_level??'O4_BUSINESS_CHANGE',base_model_version:(doc.clm??doc).version,operations:[{operation_id:p.patch_id,operation:p.operation,target_semantic_id:p.target_semantic_id,collection:p.collection,field_path:p.field_path,before:p.before,after:p.after,value:p.value}],verification_required:p.verification_required??[]};const tmp=path.join(out,'.single-change-set.json');writeJson(tmp,cs);run('apply_change_set.mjs',[working,tmp,'-o',updated,'--diff-output',path.join(out,'semantic-diff.json')],'应用语义补丁');fs.rmSync(tmp,{force:true});working=updated;changed=[target];run('logic_cli.mjs',['validate-clm',working],'校验更新后的 CLM');}
if(changed.length)run('analyze_impact.mjs',[working,...changed,'--output',path.join(out,'impact-analysis.json')],'分析语义影响');
run('logic_cli.mjs',['symbols',working,'-o',path.join(out,'symbol-table.json')],'生成 Symbol Table');
run('logic_cli.mjs',['render',working,'-o',path.join(out,'human-logic.md')],'生成中文逻辑投影');
run('logic_cli.mjs',['test-vectors',working,'-o',path.join(out,'test-vectors.json')],'生成测试向量');
let generated=null;
if(profile){run('logic_cli.mjs',['compile-iir',working,profile,'-o',path.join(out,'implementation.iir.json')],'编译 IIR v0.2');run('logic_cli.mjs',['validate-iir',path.join(out,'implementation.iir.json')],'校验 IIR v0.2');run('logic_cli.mjs',['target-tests',path.join(out,'test-vectors.json'),path.join(out,'implementation.iir.json'),'-o',path.join(out,'target-test-plan.json')],'编译目标测试计划');if(has('--generate-ts',args)){generated=path.join(out,'generated-ts');run('logic_cli.mjs',['generate-ts',path.join(out,'implementation.iir.json'),path.join(out,'target-test-plan.json'),'-o',generated],'生成 TypeScript + SQLite');run('logic_cli.mjs',['verify-manifest',generated],'校验生成产物完整性')}}else if(has('--generate-ts',args)){console.error('--generate-ts 需要 --target-profile');process.exit(2)}
console.log(JSON.stringify({ok:true,clm:working,output_dir:out,generated_typescript:generated},null,2));
