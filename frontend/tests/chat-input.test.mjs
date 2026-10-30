import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';

const source=await readFile(new URL('../app.js',import.meta.url),'utf8');
const handler=source.slice(source.indexOf('async function sendChat('),source.indexOf('async function loadHistory('));

function setup(){
  let resolve,reject,calls=0;
  const response=new Promise((yes,no)=>{resolve=yes;reject=no;});
  const input={value:'이번 달 지출은?',focus(){}};
  const button={disabled:false};
  const elements={'#chat-input':input,'#send-chat':button,'.suggestions':{hidden:false},'#messages':{append(){},scrollTop:0,scrollHeight:100}};
  const context=vm.createContext({busyChat:false,currentConversation:null,$:selector=>elements[selector],document:{createElement:()=>({})},drawMessages(){},toast(){},request:()=>{calls++;return response;}});
  vm.runInContext(handler,context);
  return {input,button,context,resolve,reject,calls:()=>calls,send:()=>context.sendChat({preventDefault(){}})};
}

test('clears sent text immediately and prevents duplicate sends while waiting',async()=>{
  const s=setup(),pending=s.send();
  assert.equal(s.input.value,'');
  assert.equal(s.button.disabled,true);
  await s.send();
  assert.equal(s.calls(),1);
  s.resolve({id:'chat',messages:[]});await pending;
  assert.equal(s.button.disabled,false);
});

test('a successful answer preserves the next question typed while waiting',async()=>{
  const s=setup(),pending=s.send();s.input.value='다음 질문';
  s.resolve({id:'chat',messages:[]});await pending;
  assert.equal(s.input.value,'다음 질문');
});

test('failed sends restore the sent draft when no new draft was entered',async()=>{
  const s=setup(),original=s.input.value,pending=s.send();
  s.reject(new Error('Connection failed'));await pending;
  assert.equal(s.input.value,original);
  assert.equal(s.button.disabled,false);
});

test('failed sends do not overwrite a new draft',async()=>{
  const s=setup(),pending=s.send();s.input.value='보존할 새 질문';
  s.reject(new Error('Connection failed'));await pending;
  assert.equal(s.input.value,'보존할 새 질문');
});
