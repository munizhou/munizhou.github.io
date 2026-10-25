// Developer-only checks; running the website/editor still requires no Node.js.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../dist/assets/site.js'),'utf8');
const original='a'.repeat(24),changed='b'.repeat(24);
const settle=()=>new Promise(resolve=>setImmediate(resolve));
function preview({host='127.0.0.1',hidden=false,version=original,offline=false,meta=true}={}){
  const calls=[],navigations=[],intervals=[],events={};
  const url=new URL(`http://${host}:9999/research/magnetogenesis/?example=keep#shear-driven-weibel`);
  const state={version,offline};
  const document={visibilityState:hidden?'hidden':'visible',documentElement:{classList:{add(){}}},
    querySelector(selector){return selector.startsWith('meta[')&&meta?{content:original}:null},
    addEventListener(name,fn){events['document:'+name]=fn}};
  vm.runInNewContext(source,{
    document,window:{addEventListener(name,fn){events['window:'+name]=fn}},
    location:{protocol:url.protocol,hostname:url.hostname,href:url.href,replace(href){navigations.push(href)}},
    fetch:async(url,options)=>{calls.push({url,options});if(state.offline)throw Error('Server stopped');return {ok:true,json:async()=>({format:'tapas-local-preview-v1',revision:state.version})}},
    setInterval(fn,delay){intervals.push({fn,delay})},URL,Date
  });
  return {calls,navigations,intervals,events,document,state};
}
test('unchanged local preview stays open and requests fresh revision data',async()=>{
  const p=preview();await settle();assert.equal(p.calls.length,1);assert.equal(p.navigations.length,0);
  assert.equal(p.calls[0].options.cache,'no-store');assert.equal(p.intervals[0].delay,1500);
});
test('save refreshes the same project and bypasses cache without repeated navigation',async()=>{
  const p=preview();await settle();p.state.version=changed;await p.intervals[0].fn();
  const target=new URL(p.navigations[0]);assert.equal(target.pathname,'/research/magnetogenesis/');
  assert.equal(target.hash,'#shear-driven-weibel');assert.equal(target.searchParams.get('example'),'keep');
  assert.equal(target.searchParams.get('_preview'),changed);
  await p.events['window:focus']();assert.equal(p.navigations.length,1);
});
test('hidden tabs check again when the reader returns',async()=>{
  const p=preview({hidden:true,version:changed});await settle();assert.equal(p.calls.length,0);
  p.document.visibilityState='visible';await p.events['document:visibilitychange']();
  assert.equal(p.navigations.length,1);
});
test('stopped server does not disrupt reading and polling recovers',async()=>{
  const p=preview({offline:true});await settle();assert.equal(p.navigations.length,0);
  p.state.offline=false;p.state.version=changed;await p.intervals[0].fn();assert.equal(p.navigations.length,1);
});
test('hosted sites and pages without a revision never poll',async()=>{
  for(const options of [{host:'tapas.example.edu'},{meta:false}]){
    const p=preview(options);await settle();assert.equal(p.calls.length,0);assert.equal(p.intervals.length,0);
  }
});
