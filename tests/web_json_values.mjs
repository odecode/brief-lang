//===----------------------------------------------------------------------===//
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//===----------------------------------------------------------------------===//
import fs from 'node:fs';
import assert from 'node:assert/strict';
const s=fs.readFileSync(new URL('../src/glue/web_heap.js', import.meta.url),'utf8');
const {createWebHeap}=await import('data:text/javascript;base64,'+Buffer.from(s+'\nexport {createWebHeap};').toString('base64'));
let memory; const heap=createWebHeap(()=>memory);
const {instance}=await WebAssembly.instantiate(fs.readFileSync(process.argv[2]),{env:{...heap,__web_flush_state:()=>{}}});
memory=instance.exports.memory; const a=instance.exports; a.__web_boot(); const state=a.__briev_state_ptr();
for(const str of ['1','0.125e+2','-1.25e-2','{}','{"v":1}','[1]','{"a":true}','{"v":1,"type":"authenticated","token":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","server_epoch":"0123456789abcdef0123456789abcdef","account_id":7,"username":"fixture"}']) {
 const bytes=new TextEncoder().encode(str), p=heap.malloc(BigInt(bytes.length+9)); const d=new DataView(memory.buffer);d.setBigUint64(p,BigInt(bytes.length),true);new Uint8Array(memory.buffer,p+8,bytes.length).set(bytes); a.probe(state,p);
 const v=new DataView(memory.buffer),r=Number(v.getBigUint64(state,true)),len=Number(v.getBigUint64(r,true));assert.equal(new TextDecoder().decode(new Uint8Array(memory.buffer,r+8,len)), 'ok', str);
}

console.log('WASM JSON integers, keywords, arrays and login response pass');
