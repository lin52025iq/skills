#!/usr/bin/env node
import Ajv2020 from 'ajv/dist/2020.js';
import {readJson} from './lib/model.mjs';

const [documentFile,schemaFile]=process.argv.slice(2);
if(!documentFile||!schemaFile){console.error('usage: node schema_validate.mjs document.json schema.json');process.exit(2)}
try{
  const document=readJson(documentFile),schema=readJson(schemaFile),ajv=new Ajv2020({allErrors:true,strict:false}),validate=ajv.compile(schema),ok=validate(document);
  const result={valid:!!ok,errors:(validate.errors??[]).map(e=>({code:'SCHEMA_VALIDATION_ERROR',path:e.instancePath||'/',message:e.message,params:e.params}))};
  console.log(JSON.stringify(result,null,2));
  process.exit(ok?0:1);
}catch(e){console.error(JSON.stringify({valid:false,error:e.message},null,2));process.exit(2)}
