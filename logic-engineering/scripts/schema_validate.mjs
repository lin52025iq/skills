#!/usr/bin/env node
import {readJson} from './lib/model.mjs';

const [documentFile,schemaFile]=process.argv.slice(2);
if(!documentFile||!schemaFile){
  console.error('usage: node schema_validate.mjs document.json schema.json');
  process.exit(2);
}

function typeMatches(value,type){
  if(type==='null') return value===null;
  if(type==='array') return Array.isArray(value);
  if(type==='object') return value!==null && typeof value==='object' && !Array.isArray(value);
  if(type==='integer') return Number.isInteger(value);
  if(type==='number') return typeof value==='number' && Number.isFinite(value);
  if(type==='string') return typeof value==='string';
  if(type==='boolean') return typeof value==='boolean';
  return true;
}

function deepEqual(a,b){return JSON.stringify(a)===JSON.stringify(b);}

function resolvePointer(root,ref){
  if(!ref.startsWith('#/')) throw new Error(`仅支持内部 $ref: ${ref}`);
  let cur=root;
  for(const raw of ref.slice(2).split('/')){
    const part=raw.replace(/~1/g,'/').replace(/~0/g,'~');
    if(cur==null || !(part in cur)) throw new Error(`无法解析 $ref: ${ref}`);
    cur=cur[part];
  }
  return cur;
}

function validateNode(value,schema,root,path,errors,{probe=false}={}){
  if(schema===true || schema==null) return;
  if(schema===false){errors.push({code:'SCHEMA_VALIDATION_ERROR',path,message:'schema=false'});return;}
  if(typeof schema!=='object') return;

  if(schema.$ref){
    validateNode(value,resolvePointer(root,schema.$ref),root,path,errors,{probe});
    return;
  }

  if(Array.isArray(schema.allOf)){
    for(const sub of schema.allOf) validateNode(value,sub,root,path,errors,{probe});
  }

  if(Array.isArray(schema.oneOf)){
    let matched=0;
    for(const sub of schema.oneOf){
      const local=[];
      validateNode(value,sub,root,path,local,{probe:true});
      if(local.length===0) matched++;
    }
    if(matched!==1){
      errors.push({code:'SCHEMA_VALIDATION_ERROR',path,message:`oneOf 必须且只能匹配一个分支，实际匹配 ${matched} 个`});
      return;
    }
  }

  if(schema.if){
    const conditionErrors=[];
    validateNode(value,schema.if,root,path,conditionErrors,{probe:true});
    if(conditionErrors.length===0 && schema.then) validateNode(value,schema.then,root,path,errors,{probe});
    if(conditionErrors.length>0 && schema.else) validateNode(value,schema.else,root,path,errors,{probe});
  }

  if(schema.const!==undefined && !deepEqual(value,schema.const)){
    errors.push({code:'SCHEMA_VALIDATION_ERROR',path,message:`值必须等于 ${JSON.stringify(schema.const)}`});
    return;
  }

  if(Array.isArray(schema.enum) && !schema.enum.some(x=>deepEqual(x,value))){
    errors.push({code:'SCHEMA_VALIDATION_ERROR',path,message:`值不在允许枚举中: ${JSON.stringify(schema.enum)}`});
    return;
  }

  if(schema.type!==undefined){
    const types=Array.isArray(schema.type)?schema.type:[schema.type];
    if(!types.some(t=>typeMatches(value,t))){
      errors.push({code:'SCHEMA_VALIDATION_ERROR',path,message:`类型不匹配，期望 ${types.join('|')}`});
      return;
    }
  }

  if(typeof value==='string'){
    if(Number.isInteger(schema.minLength) && value.length<schema.minLength)
      errors.push({code:'SCHEMA_VALIDATION_ERROR',path,message:`字符串长度必须 >= ${schema.minLength}`});
    if(schema.pattern){
      const re=new RegExp(schema.pattern);
      if(!re.test(value)) errors.push({code:'SCHEMA_VALIDATION_ERROR',path,message:`字符串不匹配 pattern ${schema.pattern}`});
    }
  }

  if(Array.isArray(value)){
    if(Number.isInteger(schema.minItems) && value.length<schema.minItems)
      errors.push({code:'SCHEMA_VALIDATION_ERROR',path,message:`数组元素数量必须 >= ${schema.minItems}`});
    if(Number.isInteger(schema.maxItems) && value.length>schema.maxItems)
      errors.push({code:'SCHEMA_VALIDATION_ERROR',path,message:`数组元素数量必须 <= ${schema.maxItems}`});
    if(schema.uniqueItems){
      const seen=new Set();
      for(const item of value){
        const key=JSON.stringify(item);
        if(seen.has(key)){errors.push({code:'SCHEMA_VALIDATION_ERROR',path,message:'数组元素必须唯一'});break;}
        seen.add(key);
      }
    }
    if(schema.items){
      value.forEach((item,i)=>validateNode(item,schema.items,root,`${path}/${i}`,errors,{probe}));
    }
  }

  if(value!==null && typeof value==='object' && !Array.isArray(value)){
    const keys=Object.keys(value);
    if(Number.isInteger(schema.minProperties) && keys.length<schema.minProperties)
      errors.push({code:'SCHEMA_VALIDATION_ERROR',path,message:`对象属性数量必须 >= ${schema.minProperties}`});
    if(Number.isInteger(schema.maxProperties) && keys.length>schema.maxProperties)
      errors.push({code:'SCHEMA_VALIDATION_ERROR',path,message:`对象属性数量必须 <= ${schema.maxProperties}`});
    for(const req of schema.required??[]){
      if(!(req in value)) errors.push({code:'SCHEMA_VALIDATION_ERROR',path,message:`缺少必需字段: ${req}`});
    }
    const props=schema.properties??{};
    for(const [key,sub] of Object.entries(props)){
      if(key in value) validateNode(value[key],sub,root,`${path}/${escapePointer(key)}`,errors,{probe});
    }
    if(schema.additionalProperties===false){
      const allowed=new Set(Object.keys(props));
      for(const key of keys){
        if(!allowed.has(key)) errors.push({code:'SCHEMA_VALIDATION_ERROR',path:`${path}/${escapePointer(key)}`,message:`不允许额外字段: ${key}`});
      }
    }else if(schema.additionalProperties && typeof schema.additionalProperties==='object'){
      const allowed=new Set(Object.keys(props));
      for(const key of keys){
        if(!allowed.has(key)) validateNode(value[key],schema.additionalProperties,root,`${path}/${escapePointer(key)}`,errors,{probe});
      }
    }
  }
}

function escapePointer(value){return value.replace(/~/g,'~0').replace(/\//g,'~1');}

try{
  const document=readJson(documentFile);
  const schema=readJson(schemaFile);
  const errors=[];
  validateNode(document,schema,schema,'',errors);
  const result={valid:errors.length===0,errors};
  console.log(JSON.stringify(result,null,2));
  process.exit(result.valid?0:1);
}catch(e){
  console.error(JSON.stringify({valid:false,error:e.message},null,2));
  process.exit(2);
}
