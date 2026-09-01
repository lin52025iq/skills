#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

function existsCommand(cmd,args=['--version']){const p=spawnSync(cmd,args,{encoding:'utf8',shell:false});return !p.error&&p.status===0;}
function resolveTool(root,name){const ext=process.platform==='win32'?'.cmd':'';const local=path.join(root,'node_modules','.bin',`${name}${ext}`);if(fs.existsSync(local))return local;return existsCommand(name)?name:null;}
function run(cmd,args,cwd){const p=spawnSync(cmd,args,{cwd,encoding:'utf8',shell:false});return {ok:p.status===0,status:p.status,stdout:p.stdout??'',stderr:p.stderr??''};}

const [rootArg]=process.argv.slice(2);if(!rootArg){console.error('usage: node verify_typescript.mjs generated-ts');process.exit(2);}const root=path.resolve(rootArg);
const required=['package.json','tsconfig.json','domain/generated.ts','rules/generated.ts','usecases/generated.ts','tests/generated.test.ts','manifest.json'];const missing=required.filter(x=>!fs.existsSync(path.join(root,x)));if(missing.length){console.error(JSON.stringify({ok:false,code:'GENERATED_TS_MISSING_FILES',missing},null,2));process.exit(1);}
const tsc=resolveTool(root,'tsc'),vitest=resolveTool(root,'vitest');if(!tsc||!vitest){console.error(JSON.stringify({ok:false,code:'TOOL_UNAVAILABLE',message:'执行 TypeScript Gate 需要 tsc 与 vitest；可使用生成目录 package.json 安装 devDependencies 后重试。',tsc:!!tsc,vitest:!!vitest},null,2));process.exit(2);}
const typecheck=run(tsc,['--noEmit','-p','tsconfig.json'],root);if(!typecheck.ok){console.error(JSON.stringify({ok:false,stage:'tsc',...typecheck},null,2));process.exit(1);}const tests=run(vitest,['run'],root);if(!tests.ok){console.error(JSON.stringify({ok:false,stage:'vitest',...tests},null,2));process.exit(1);}console.log(JSON.stringify({ok:true,typecheck:'passed',tests:'passed'},null,2));
