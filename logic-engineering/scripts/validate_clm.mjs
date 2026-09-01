#!/usr/bin/env node
import {readJson,rootOf,iterNodes,buildNodeIndex,buildSymbolTable,compatibleTypes,enumContains,validatePlacement,collectionElementScope,resolveScopedRef} from './lib/model.mjs';

function refsIn(value,out=[]){
  if(Array.isArray(value))for(const item of value)refsIn(item,out);
  else if(value&&typeof value==='object'){
    if(typeof value.ref==='string')out.push(value.ref);
    for(const item of Object.values(value))refsIn(item,out);
  }
  return out;
}
function literalType(v){if(typeof v==='boolean')return'boolean';if(Number.isInteger(v))return'integer';if(typeof v==='number')return'number';if(typeof v==='string')return'string';return null;}
function descriptor(type=null,cardinality='one'){return{type,cardinality};}

function buildForeachScopes(document,symbols,index,errors){
  const childScopes=new Map(),ownScopes=new Map();
  for(const [,node] of iterNodes(document)){
    if(node.kind!=='foreach')continue;
    const scope=collectionElementScope(node.collection,node.item,symbols);
    if(!scope.valid){errors.push({code:'INVALID_FOREACH_COLLECTION',semantic_id:node.id,path:'collection',message:scope.reason});continue;}
    ownScopes.set(node.id,scope);
    for(const childId of node.do??[]){
      if(!index.has(childId)){errors.push({code:'BROKEN_REFERENCE',semantic_id:node.id,path:'do',message:`foreach do 引用不存在: ${childId}`});continue;}
      const prior=childScopes.get(childId);
      if(prior&&(prior.alias!==scope.alias||prior.entityType!==scope.entityType))errors.push({code:'FOREACH_SCOPE_CONFLICT',semantic_id:childId,message:`同一节点被不同 foreach scope 引用：${prior.alias}:${prior.entityType} 与 ${scope.alias}:${scope.entityType}`});
      else childScopes.set(childId,scope);
    }
  }
  return{childScopes,ownScopes};
}

function validateObjectValue(objectValue,symbols,errors,owner,location,scope){
  const type=objectValue?.type,entity=symbols[type];
  if(!entity||entity.kind!=='entity'){
    errors.push({code:'INVALID_OBJECT_TYPE',semantic_id:owner,path:location,message:`typed object.type 必须引用 entity: ${type??'<missing>'}`});
    return descriptor(type,'one');
  }
  const fields=objectValue.fields??{};
  for(const [fieldRef,value] of Object.entries(fields)){
    const field=symbols[fieldRef];
    if(!field||field.kind!=='field'||field.owner!==type){errors.push({code:'INVALID_OBJECT_FIELD',semantic_id:owner,path:`${location}.fields.${fieldRef}`,message:`字段不属于 ${type}: ${fieldRef}`});continue;}
    const actual=validateTypedValue(value,symbols,errors,owner,`${location}.fields.${fieldRef}`,scope);
    if(field.cardinality==='many'){
      if(actual.cardinality!=='many')errors.push({code:'COLLECTION_FIELD_REQUIRES_LIST',semantic_id:owner,path:`${location}.fields.${fieldRef}`,message:`${fieldRef} 是 many 字段，值必须为 list`});
    }else if(actual.cardinality==='many')errors.push({code:'SCALAR_FIELD_REJECTS_LIST',semantic_id:owner,path:`${location}.fields.${fieldRef}`,message:`${fieldRef} 是标量字段，不能赋 list`});
    if(actual.type&&!compatibleTypes(field.type,actual.type))errors.push({code:'TYPE_MISMATCH',semantic_id:owner,path:`${location}.fields.${fieldRef}`,message:`${fieldRef} 期望 ${field.type}，实际 ${actual.type}`});
  }
  const required=Object.values(symbols).filter(x=>x.kind==='field'&&x.owner===type&&x.nullable!==true);
  for(const field of required)if(!Object.hasOwn(fields,field.id))errors.push({code:'OBJECT_REQUIRED_FIELD_MISSING',semantic_id:owner,path:location,message:`typed object 缺少非空字段: ${field.id}`});
  return descriptor(type,'one');
}

function validateTypedValue(value,symbols,errors,owner,location,scope=null){
  if(!value||typeof value!=='object'||Array.isArray(value)){errors.push({code:'INVALID_TYPED_VALUE',semantic_id:owner,path:location,message:'typed value 必须是对象'});return descriptor();}
  const kinds=['ref','literal','enum','null','set','list','object'].filter(k=>k in value);
  if(kinds.length!==1){errors.push({code:'INVALID_TYPED_VALUE',semantic_id:owner,path:location,message:'必须且只能包含 ref/literal/enum/null/set/list/object 之一'});return descriptor();}
  if(value.ref){
    const scoped=resolveScopedRef(value.ref,scope,symbols);if(scoped)return descriptor(scoped.type,scoped.cardinality??'one');
    const symbol=symbols[value.ref];if(!symbol)errors.push({code:'UNKNOWN_SYMBOL',semantic_id:owner,path:location,message:`未知 symbol: ${value.ref}`});
    return descriptor(symbol?.type??null,symbol?.cardinality??'one');
  }
  if(value.enum){
    const type=value.enum.type;if(!symbols[type]||symbols[type].kind!=='enum')errors.push({code:'INVALID_ENUM_TYPE',semantic_id:owner,path:location,message:`非法 enum 类型: ${type}`});
    else if(!enumContains(symbols,type,value.enum.value))errors.push({code:'INVALID_ENUM_VALUE',semantic_id:owner,path:location,message:`${value.enum.value} 不属于 ${type}`});
    return descriptor(type,'one');
  }
  if('literal'in value)return descriptor(literalType(value.literal),'one');
  if(value.null)return descriptor(null,'one');
  if(Array.isArray(value.set)){
    let elementType=null;
    value.set.forEach((item,i)=>{const d=validateTypedValue(item,symbols,errors,owner,`${location}.set[${i}]`,scope);if(elementType&&d.type&&!compatibleTypes(elementType,d.type))errors.push({code:'TYPE_MISMATCH',semantic_id:owner,path:location,message:`set 元素类型不一致: ${elementType} / ${d.type}`});elementType??=d.type;});
    return descriptor(elementType,'many');
  }
  if(Array.isArray(value.list)){
    let elementType=null;
    value.list.forEach((item,i)=>{const d=validateTypedValue(item,symbols,errors,owner,`${location}.list[${i}]`,scope);if(d.cardinality==='many')errors.push({code:'NESTED_LIST_UNSUPPORTED',semantic_id:owner,path:`${location}.list[${i}]`,message:'v0.2 暂不支持嵌套 list'});if(elementType&&d.type&&!compatibleTypes(elementType,d.type))errors.push({code:'TYPE_MISMATCH',semantic_id:owner,path:location,message:`list 元素类型不一致: ${elementType} / ${d.type}`});elementType??=d.type;});
    return descriptor(elementType,'many');
  }
  if(value.object)return validateObjectValue(value.object,symbols,errors,owner,`${location}.object`,scope);
  return descriptor();
}

function validateExpression(expr,symbols,errors,owner,location='expression',scope=null){
  if(!expr||typeof expr!=='object'||Array.isArray(expr)){errors.push({code:'INVALID_TYPED_EXPRESSION',semantic_id:owner,path:location,message:'表达式必须是对象'});return;}
  const op=expr.op;
  if(op==='all'||op==='any'){
    if(!Array.isArray(expr.items)||!expr.items.length){errors.push({code:'INVALID_TYPED_EXPRESSION',semantic_id:owner,path:location,message:`${op} 需要非空 items`});return;}
    expr.items.forEach((x,i)=>validateExpression(x,symbols,errors,owner,`${location}.items[${i}]`,scope));return;
  }
  if(op==='not'){validateExpression(expr.item,symbols,errors,owner,`${location}.item`,scope);return;}
  if(!['eq','ne','lt','le','gt','ge','in','not_in'].includes(op)){errors.push({code:'INVALID_TYPED_EXPRESSION',semantic_id:owner,path:location,message:`不支持 op: ${op}`});return;}
  const left=validateTypedValue(expr.left,symbols,errors,owner,`${location}.left`,scope);
  if(left.cardinality==='many')errors.push({code:'INVALID_EXPRESSION_CARDINALITY',semantic_id:owner,path:`${location}.left`,message:'比较左侧必须是标量'});
  if(op==='in'||op==='not_in'){
    if(!Array.isArray(expr.right?.set)){errors.push({code:'INVALID_TYPED_EXPRESSION',semantic_id:owner,path:`${location}.right`,message:'in/not_in 右侧必须是 typed set'});return;}
    expr.right.set.forEach((item,i)=>{const d=validateTypedValue(item,symbols,errors,owner,`${location}.right.set[${i}]`,scope);if(left.type&&d.type&&!compatibleTypes(left.type,d.type))errors.push({code:'TYPE_MISMATCH',semantic_id:owner,path:location,message:`集合成员类型 ${d.type} 与 ${left.type} 不兼容`});});return;
  }
  const right=validateTypedValue(expr.right,symbols,errors,owner,`${location}.right`,scope);
  if(right.cardinality==='many')errors.push({code:'INVALID_EXPRESSION_CARDINALITY',semantic_id:owner,path:`${location}.right`,message:'普通比较右侧必须是标量'});
  if(left.type&&right.type&&!compatibleTypes(left.type,right.type))errors.push({code:'TYPE_MISMATCH',semantic_id:owner,path:location,message:`比较类型 ${left.type} 与 ${right.type} 不兼容`});
}

function validateAtomicity(node,index,errors){
  const behavior=index.get(node.behavior_ref);
  if(!behavior||behavior.kind!=='behavior'){errors.push({code:'INVALID_ATOMICITY_BEHAVIOR',semantic_id:node.id,path:'behavior_ref',message:`atomicity.behavior_ref 必须引用 Behavior: ${node.behavior_ref??'<missing>'}`});return;}
  const members=node.members??[],flow=behavior.flow??[],positions=members.map(x=>flow.indexOf(x));
  if(positions.some(x=>x<0)){errors.push({code:'INVALID_ATOMICITY_MEMBER',semantic_id:node.id,path:'members',message:'atomicity.members 必须全部属于目标 Behavior 顶层 flow'});return;}
  const start=Math.min(...positions),end=Math.max(...positions),expected=flow.slice(start,end+1);
  if(expected.length!==members.length||expected.some((x,i)=>x!==members[i]))errors.push({code:'NON_CONTIGUOUS_ATOMICITY',semantic_id:node.id,path:'members',message:'atomicity.members 必须按 Behavior flow 顺序形成连续区间'});
}

function validateClm(document){
  const root=rootOf(document),errors=[],warnings=[],ids=new Set(),symbols=buildSymbolTable(document),index=buildNodeIndex(document);
  const {childScopes,ownScopes}=buildForeachScopes(document,symbols,index,errors);
  for(const [collection,node] of iterNodes(document)){
    const scope=childScopes.get(node.id)??ownScopes.get(node.id)??null;
    const placement=validatePlacement(node,collection);if(placement)errors.push({code:'NODE_COLLECTION_MISMATCH',semantic_id:node.id,message:placement});
    if(ids.has(node.id))errors.push({code:'DUPLICATE_SEMANTIC_ID',semantic_id:node.id,message:'语义 ID 重复'});ids.add(node.id);
    for(const ref of refsIn(node)){if(resolveScopedRef(ref,scope,symbols))continue;if(!symbols[ref]&&!index.has(ref)&&!ref.startsWith('error.')&&!ref.startsWith('event.')&&!ref.startsWith('evidence.'))errors.push({code:'BROKEN_REFERENCE',semantic_id:node.id,message:`引用不存在或超出 foreach scope: ${ref}`});}
    for(const key of ['expression','when','guard','condition'])if(node[key]?.op)validateExpression(node[key],symbols,errors,node.id,key,scope);
    if(node.kind==='action'&&node.operation==='assign'){
      const target=validateTypedValue(node.target,symbols,errors,node.id,'target',scope),value=validateTypedValue(node.value,symbols,errors,node.id,'value',scope);
      if(target.cardinality==='many'&&value.cardinality!=='many')errors.push({code:'COLLECTION_ASSIGNMENT_REQUIRES_LIST',semantic_id:node.id,message:'many 字段赋值必须使用 list'});
      if(target.cardinality!=='many'&&value.cardinality==='many')errors.push({code:'SCALAR_ASSIGNMENT_REJECTS_LIST',semantic_id:node.id,message:'标量字段不能赋集合'});
      if(target.type&&value.type&&!compatibleTypes(target.type,value.type))errors.push({code:'TYPE_MISMATCH',semantic_id:node.id,message:`赋值类型 ${target.type} 与 ${value.type} 不兼容`});
    }
    if(node.kind==='foreach'){
      const own=ownScopes.get(node.id);if(own&&node.when?.op)validateExpression(node.when,symbols,errors,node.id,'when',own);
      if(!(node.do??[]).length)warnings.push({code:'EMPTY_FOREACH_BODY',semantic_id:node.id,message:'foreach do 为空，不会产生行为'});
    }
    if(node.kind==='atomicity')validateAtomicity(node,index,errors);
    if(node.kind==='scenario'){
      for(const section of ['given','then'])for(let i=0;i<(node[section]??[]).length;i++){
        const a=node[section][i];if(!a?.target||!a?.value)continue;
        const target=validateTypedValue(a.target,symbols,errors,node.id,`${section}[${i}].target`),value=validateTypedValue(a.value,symbols,errors,node.id,`${section}[${i}].value`);
        if(target.cardinality==='many'&&!Array.isArray(a.value.list))errors.push({code:'COLLECTION_ASSIGNMENT_REQUIRES_LIST',semantic_id:node.id,path:`${section}[${i}].value`,message:'Scenario many 字段必须使用 typed list'});
        if(target.cardinality!=='many'&&value.cardinality==='many')errors.push({code:'SCALAR_ASSIGNMENT_REJECTS_LIST',semantic_id:node.id,path:`${section}[${i}].value`,message:'Scenario 标量字段不能赋集合'});
        if(target.type&&value.type&&!compatibleTypes(target.type,value.type))errors.push({code:'TYPE_MISMATCH',semantic_id:node.id,message:`Scenario ${section} 类型 ${target.type} 与 ${value.type} 不兼容`});
      }
      for(const ref of node.when??[]){const target=index.get(ref);if(!target)errors.push({code:'BROKEN_REFERENCE',semantic_id:node.id,message:`Scenario when 引用不存在: ${ref}`});else if(target.kind!=='behavior')errors.push({code:'SCENARIO_WHEN_NOT_BEHAVIOR',semantic_id:node.id,message:`Scenario when 当前只支持 Behavior: ${ref}`});}
    }
    if(node.origin==='observed'&&!(node.evidence_refs??[]).length)errors.push({code:'MISSING_EVIDENCE',semantic_id:node.id,message:'observed 节点必须绑定证据'});
  }
  const transitions=[...iterNodes(document)].map(x=>x[1]).filter(x=>x.kind==='transition'),forbidden=new Set([...iterNodes(document)].map(x=>x[1]).filter(x=>x.kind==='forbidden_transition').map(x=>`${x.from}->${x.to}`));
  for(const t of transitions)if(forbidden.has(`${t.from}->${t.to}`))errors.push({code:'FORBIDDEN_TRANSITION_CONFLICT',semantic_id:t.id,message:`${t.from} → ${t.to} 同时允许和禁止`});
  return{valid:!errors.length,errors,warnings,stats:{nodes:ids.size,symbols:Object.keys(symbols).length,foreach_scopes:ownScopes.size,version:root.version}};
}

const [file]=process.argv.slice(2);
if(!file){console.error('usage: node validate_clm.mjs model.json');process.exit(2);}
try{const result=validateClm(readJson(file));console.log(JSON.stringify(result,null,2));process.exit(result.valid?0:1);}catch(e){console.error(JSON.stringify({valid:false,error:e.message},null,2));process.exit(2);}
