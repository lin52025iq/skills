#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

function walk(dir,out=[]){for(const name of fs.readdirSync(dir)){const p=path.join(dir,name),s=fs.statSync(p);if(s.isDirectory())walk(p,out);else if(name.endsWith('.ts'))out.push(p);}return out;}

const [rootArg]=process.argv.slice(2);if(!rootArg){console.error('usage: node validate_generated_typescript.mjs generated-ts');process.exit(2)}const root=path.resolve(rootArg);
if(!fs.existsSync(root)){console.error(JSON.stringify({valid:false,error:'生成目录不存在'},null,2));process.exit(2)}
const errors=[],warnings=[],files=walk(root);
for(const file of files){const rel=path.relative(root,file),text=fs.readFileSync(file,'utf8');
  if(/generated skeleton/i.test(text))errors.push({code:'TS_GENERATED_SKELETON_REMAINS',path:rel,message:'生成代码仍包含 skeleton 标记'});
  if(/expect\(true\)\.toBe\(true\)/.test(text))errors.push({code:'TS_FAKE_ASSERTION',path:rel,message:'禁止使用 expect(true).toBe(true) 假装测试完成'});
  if(/input\[["']domain\./.test(text))errors.push({code:'TS_UNRESOLVED_RUNTIME_BINDING',path:rel,message:'生成代码仍包含未解析 Semantic Ref 动态访问'});
  if(/undefined as never/.test(text))warnings.push({code:'TS_FIXTURE_FALLBACK',path:rel,message:'存在无法安全构造的 fixture fallback；对应测试应优先转为 it.todo'});
  if(/throw new Error\(["'`]generated/.test(text))errors.push({code:'TS_PLACEHOLDER_THROW',path:rel,message:'生成 Use Case 仍包含占位 throw'});
}
const tests=files.filter(f=>f.endsWith('.test.ts')).map(f=>fs.readFileSync(f,'utf8')).join('\n');
if(tests&&!/\.toBe\(/.test(tests)&&!/it\.todo\(/.test(tests))warnings.push({code:'TS_NO_EXECUTABLE_ASSERTION',message:'测试文件既没有真实断言也没有显式 todo'});
const result={valid:errors.length===0,errors,warnings,stats:{typescript_files:files.length}};console.log(JSON.stringify(result,null,2));process.exit(result.valid?0:1);
