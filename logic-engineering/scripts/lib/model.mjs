import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

export const COLLECTIONS=['domain','behaviors','rules','decisions','actions','states','effects','constraints','scenarios','primitives','evidence'];
export const KIND_TO_COLLECTION={
  entity:'domain',value_type:'domain',enum:'domain',relationship:'domain',
  behavior:'behaviors',rule:'rules',decision:'decisions',action:'actions',foreach:'actions',
  state_machine:'states',transition:'states',effect:'effects',read:'effects',write:'effects',persist:'effects',external_call:'effects',emit:'effects',schedule:'effects',cache_read:'effects',cache_write:'effects',
  constraint:'constraints',precondition:'constraints',postcondition:'constraints',invariant:'constraints',uniqueness:'constraints',cardinality:'constraints',ordering:'constraints',temporal:'constraints',concurrency:'constraints',atomicity:'constraints',idempotency:'constraints',retry:'constraints',forbidden_transition:'constraints',
  scenario:'scenarios',primitive:'primitives',evidence:'evidence'
};
export function readJson(file){return JSON.parse(fs.readFileSync(file,'utf8'));}
export function writeJson(file,value){fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,JSON.stringify(value,null,2)+'\n','utf8');}
export function rootOf(doc){return doc?.clm&&typeof doc.clm==='object'?doc.clm:doc;}
export function* iterNodes(doc){const root=rootOf(doc);for(const c of COLLECTIONS){for(const n of root?.[c]??[]){if(n&&typeof n==='object')yield [c,n];}}}
export function buildNodeIndex(doc){const m=new Map();for(const [,n] of iterNodes(doc)){if(typeof n.id==='string')m.set(n.id,n);}return m;}
export function findNode(doc,id){for(const [c,n] of iterNodes(doc)){if(n.id===id)return [c,n];}throw new Error(`找不到目标语义节点: ${id}`);}
export function validatePlacement(node,collection){const expected=KIND_TO_COLLECTION[node?.kind];return expected&&expected!==collection?`节点 ${node.id} kind=${node.kind} 应位于 ${expected}，实际位于 ${collection}`:null;}
export function buildSymbolTable(doc){const table={};for(const [collection,node] of iterNodes(doc)){if(!node.id)continue;const e={id:node.id,kind:node.kind,collection,type:node.type??null,nullable:node.nullable??null,cardinality:node.cardinality??null,owner:node.owner??null};if(node.kind==='enum'){e.type=node.id;e.enum_values=[...(node.values??[])];}if(node.kind==='value_type'){e.type=node.id;e.base_type=node.base_type??null;}table[node.id]=e;if(node.kind==='entity'){for(const f of node.fields??[]){if(f?.id)table[f.id]={id:f.id,kind:'field',collection:'domain',type:f.type??null,nullable:f.nullable??false,cardinality:f.cardinality??'one',owner:node.id};}}}return table;}
export function resolveType(symbols,id){return symbols[id]?.type??null;}
export function enumContains(symbols,type,value){return (symbols[type]?.enum_values??[]).includes(value);}
export function compatibleTypes(a,b){if(a==null||b==null||a===b)return true;return ['integer','number'].includes(a)&&['integer','number'].includes(b);}
export function entityFieldSymbol(symbols,entityType,fieldPath){const first=Array.isArray(fieldPath)?fieldPath[0]:String(fieldPath).split('.')[0];if(!first)return null;return symbols[`${entityType}.${first}`]??null;}
export function resolveScopedRef(ref,scope,symbols){
  if(typeof ref!=='string'||!scope?.alias||!scope?.entityType)return null;
  if(ref===scope.alias)return {kind:'item',type:scope.entityType,entityType:scope.entityType,path:[]};
  if(!ref.startsWith(`${scope.alias}.`))return null;
  const tail=ref.slice(scope.alias.length+1).split('.').filter(Boolean);
  if(!tail.length)return null;
  const field=entityFieldSymbol(symbols,scope.entityType,tail);
  if(!field)return null;
  return {kind:'item_field',type:field.type,entityType:scope.entityType,path:tail,cardinality:field.cardinality??'one',nullable:field.nullable??false};
}
export function collectionElementScope(collectionValue,itemAlias,symbols){
  const ref=collectionValue?.ref;
  if(typeof ref!=='string')return {valid:false,reason:'foreach.collection 必须引用集合字段'};
  const symbol=symbols[ref];
  if(!symbol)return {valid:false,reason:`foreach.collection 引用未知 symbol: ${ref}`};
  if(symbol.cardinality!=='many')return {valid:false,reason:`foreach.collection 必须 cardinality=many: ${ref}`};
  if(typeof symbol.type!=='string'||!symbols[symbol.type]||symbols[symbol.type].kind!=='entity')return {valid:false,reason:`foreach.collection 元素类型必须是 entity: ${symbol.type??'<missing>'}`};
  if(typeof itemAlias!=='string'||!itemAlias.trim())return {valid:false,reason:'foreach.item 必须是非空别名'};
  return {valid:true,alias:itemAlias,entityType:symbol.type,collectionRef:ref};
}
export function canonicalSemanticPayload(doc){const clone=structuredClone(rootOf(doc));delete clone.evidence;delete clone.notes;const scrub=v=>{if(Array.isArray(v))return v.map(scrub);if(v&&typeof v==='object'){const o={};for(const k of Object.keys(v).sort()){if(['confidence','evidence_refs','notes'].includes(k))continue;o[k]=scrub(v[k]);}return o;}return v;};return scrub(clone);}
export function semanticHash(doc){return crypto.createHash('sha256').update(JSON.stringify(canonicalSemanticPayload(doc))).digest('hex');}
export function unwrapValue(v){
  if(!v||typeof v!=='object')return v;
  if('literal'in v)return v.literal;
  if(v.enum&&typeof v.enum==='object')return v.enum.value;
  if(v.null)return null;
  if(Array.isArray(v.set))return v.set.map(unwrapValue);
  if(Array.isArray(v.list))return v.list.map(unwrapValue);
  if(v.object&&typeof v.object==='object'){
    const fields={};
    for(const [ref,value] of Object.entries(v.object.fields??{}))fields[String(ref).split('.').at(-1)]=unwrapValue(value);
    return fields;
  }
  if(typeof v.ref==='string')return {ref:v.ref};
  return v;
}
export function valueRef(v){return v&&typeof v==='object'&&typeof v.ref==='string'?v.ref:null;}
export function valueType(v,symbols,scope=null){
  if(!v||typeof v!=='object')return null;
  if(v.ref){const scoped=resolveScopedRef(v.ref,scope,symbols);return scoped?.type??resolveType(symbols,v.ref);}
  if(v.enum)return v.enum.type??null;
  if(v.object)return v.object.type??null;
  if(Array.isArray(v.list))return v.list.length?valueType(v.list[0],symbols,scope):null;
  if('literal'in v){if(typeof v.literal==='boolean')return'boolean';if(Number.isInteger(v.literal))return'integer';if(typeof v.literal==='number')return'number';if(typeof v.literal==='string')return'string';}
  return null;
}
