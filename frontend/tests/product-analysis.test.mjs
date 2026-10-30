import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';

const source=await readFile(new URL('../app.js',import.meta.url),'utf8');
const handler=source.slice(source.indexOf('async function analyze(){'),source.indexOf('async function saveEntry('));

function setup(kind,result){
  const elements={'#photo':{files:[new Blob(['test'])]},'#analyze-button':{disabled:false,textContent:''},'#entry-date':{value:''},'#entry-merchant':{value:''}};
  const notifications=[];
  const context=vm.createContext({kind,draft:[],expectedTotal:null,analyzed:false,FormData,$:s=>elements[s],localDate:()=> '2026-10-30',drawDraft(){},notifyAnalysis:(text,tone)=>notifications.push({text,tone}),request:async()=>result});
  vm.runInContext(handler,context);
  return {context,notifications};
}

test('recognizes a product without a price and allows manual price entry',async()=>{
  const s=setup('product',{items:[{name:'비빔밥',category:'식비',value:null}],total:0,date:null,merchant:'',warnings:[]});
  await s.context.analyze();
  assert.equal(s.context.draft[0].name,'비빔밥');
  assert.equal(s.context.draft[0].value,null);
  assert.equal(s.context.expectedTotal,null);
  assert.equal(s.context.analyzed,true);
  assert.equal(s.notifications[0].tone,'success');
  assert.match(s.notifications[0].text,/금액.*직접 입력/);
});

test('receipt totals remain available for mismatch checking',async()=>{
  const s=setup('receipt',{items:[{name:'커피',category:'카페·간식',value:3000}],total:2500,date:null,merchant:'',warnings:['합계 불일치']});
  await s.context.analyze();
  assert.equal(s.context.expectedTotal,2500);
  assert.equal(s.notifications[0].tone,'warning');
});
