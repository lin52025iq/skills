import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

export const COLLECTIONS=['domain','behaviors','rules','decisions','actions','states','effects','constraints','scenarios','primitives','evidence'];
export const KIND_TO_COLLECTION={
  entity:'domain',value_type:'domain',enum:'domain',relationship:'domain',
  behavior:'behaviors',rule:'rules',decision:'decisions',action:'actions',foreach:'actions',
  state_machine:'states',transition:'states',effect:'effects',read:'effects',write:'effects',persist:'effects',external_call:'effects',emit:'effects',schedule:'effects',cache_read:'effects',cache_write:'effects',
  constraint:'constraints',precondition:'constraints',postcondition:'constraints',invariant:'constraints',uniqueness:'constraints',cardinality:'constraints',ordering:'constraints',temporal:'constraints',concurrency:'constraints',atomicity:'constraints',idempotency:'constraints',forbidden_transition:'constraints',
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
export function canonicalSemanticPayload(doc){const clone=structuredClone(rootOf(doc));delete clone.evidence;delete clone.notes;const scrub=v=>{if(Array.isArray(v))return v.map(scrub);if(v&&typeof v==='object'){const o={};for(const k of Object.keys(v).sort()){if(['confidence','evidence_refs','notes'].includes(k))continue;o[k]=scrub(v[k]);}return o;}return v;};return scrub(clone);}
export function semanticHash(doc){return crypto.createHash('sha256').update(JSON.stringify(canonicalSemanticPayload(doc))).digest('hex');}
export function unwrapValue(v){if(!v||typeof v!=='object')return v;if('literal'in v)return v.literal;if(v.enum&&typeof v.enum==='object')return v.enum.value;if(v.null)return null;if(Array.isArray(v.set))return v.set.map(unwrapValue);if(typeof v.ref==='string')return {ref:v.ref};return v;}
export function valueRef(v){return v&&typeof v==='object'&&typeof v.ref==='string'?v.ref:null;}
export function valueType(v,symbols){if(!v||typeof v!=='object')return null;if(v.ref)return resolveType(symbols,v.ref);if(v.enum)return v.enum.type??null;if('literal'in v){if(typeof v.literal==='boolean')return'boolean';if(Number.isInteger(v.literal))return'integer';if(typeof v.literal==='number')return'number';if(typeof v.literal==='string')return'string';}return null;}
