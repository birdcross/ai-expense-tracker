const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
const categories = ['식비','카페·간식','생활용품','의류·신발','교통','문화·여가','건강','기타'];
const icons = ['🍚','☕','🧴','👟','🚇','🎟','💊','🛍'];
const colors = ['#467c64','#82a892','#b6cbb0','#d6bb87','#90adb8','#b7a3bd','#d7a59d','#a0aaa4'];
const money = v => new Intl.NumberFormat('ko-KR').format(v) + '원';
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const localDate = () => new Intl.DateTimeFormat('sv-SE').format(new Date());
let apiBase = (localStorage.getItem('sseumlog-api') || window.APP_CONFIG?.API_BASE_URL || location.origin).replace(/\/$/,'');
let token = sessionStorage.getItem('sseumlog-token') || '';
let rows = [], stats = null, currentConversation = null, kind = 'receipt', editing = null, draft = [], expectedTotal = null, analyzed = false, photoURL = null, busyChat = false;
let toastTimer;
function toast(message) { $('#toast').textContent = message; $('#toast').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#toast').hidden = true, 5500); }
async function request(path, options = {}) {
  const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), 90000);
  try {
    const headers = {'X-App-Token':token, ...options.headers};
    if (options.body && !(options.body instanceof FormData)) headers['Content-Type'] = 'application/json';
    const response = await fetch(apiBase + '/api' + path, {...options, headers, signal:controller.signal});
    if (response.status === 413) throw new Error('사진은 4MB 이하로 올려주세요. 사진 크기를 줄인 뒤 다시 시도해주세요.');
    if (!response.ok) { const data = await response.json().catch(() => ({})); throw new Error(typeof data.detail === 'string' ? data.detail : `입력 또는 서버 응답을 확인해주세요. (${response.status})`); }
    return response.status === 204 ? null : await response.json();
  } catch(e) { if (e.name === 'AbortError') throw new Error('서버 응답이 지연되고 있어요. 무료 서버의 첫 접속은 시간이 걸릴 수 있습니다. 잠시 후 다시 시도해주세요.'); if (e instanceof TypeError) throw new Error('서버에 연결하지 못했습니다. 연결 설정과 서버 상태를 확인해주세요.'); throw e; }
  finally { clearTimeout(timer); }
}
async function refresh() {
  [rows, stats] = await Promise.all([request('/data'), request('/data/summary')]);
  renderDashboard(); renderRecords(); renderSummary();
}
function navigate(view) {
  window.scrollTo(0,0);
  $$('.view').forEach(el => el.hidden = el.id !== 'view-' + view);
  $$('.nav').forEach(el => el.classList.toggle('active',el.dataset.view === view));
  $('#breadcrumb').textContent = {dashboard:'MY MONEY / OVERVIEW',records:'MY MONEY / JOURNAL',chat:'MY MONEY / AI PARTNER',history:'MY MONEY / ARCHIVE'}[view];
  if (view === 'history') loadHistory().catch(e=>toast(e.message));
}
function renderDashboard() {
  $('#stat-month').textContent = money(stats.this_month);
  $('#stat-average').textContent = money(stats.average);
  $('#stat-count').textContent = `전체 ${stats.count}건 · 총 ${money(stats.total)}`;
  $('#stat-trend').textContent = stats.change_percent === null ? '비교 데이터 부족' : `${stats.change_percent > 0 ? '+' : ''}${stats.change_percent}%`;
  $('#stat-comparison').textContent = `최근 ${money(stats.recent_7_days)} / 이전 ${money(stats.previous_7_days)}`;
  $('#period').textContent = stats.start ? `${stats.start} — ${stats.end} · ${stats.count}건의 기록` : '첫 지출을 기록해보세요';
  $('#daily-average').textContent = `전체 기간 일평균 ${money(stats.daily_average)}`;
  $('#category-list').innerHTML = Object.entries(stats.categories).map(([name,value]) => `<div class="category"><div class="category-line"><span>${esc(name)} <small>${Math.round(value/(stats.total||1)*100)}%</small></span><strong>${money(value)}</strong></div><div class="track"><i style="width:${value/(stats.total||1)*100}%;background:${colors[categories.indexOf(name)] || colors[7]}"></i></div></div>`).join('') || '<div class="empty">기록이 쌓이면<br>소비 비중을 보여드려요.</div>';
  $('#recent-records').innerHTML = recordHTML(rows.slice(0,5),false);
  renderChart();
}
function renderChart() {
  const byDay = Object.fromEntries(stats.daily.map(d=>[d.date,d.value]));
  const points = Array.from({length:30},(_,i)=>{const d=new Date(); d.setDate(d.getDate()-29+i); const key=new Intl.DateTimeFormat('sv-SE').format(d); return {date:key,value:byDay[key] || 0};});
  const max=Math.max(10000,...points.map(p=>p.value));
  const xy=points.map((p,i)=>[45+i*535/29,145-p.value/max*125]);
  const line=xy.map(p=>p.join(',')).join(' ');
  const grids=[0,.5,1].map(r=>`<line x1="45" y1="${145-r*125}" x2="580" y2="${145-r*125}" stroke="var(--line)" stroke-dasharray="4 4"/><text x="0" y="${149-r*125}">${Math.round(max*r/1000)}천</text>`).join('');
  $('#chart').innerHTML=`<svg viewBox="0 0 600 185" role="img" aria-label="최근 30일 일별 지출 그래프"><defs><linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#6da588" stop-opacity=".25"/><stop offset="100%" stop-color="#6da588" stop-opacity="0"/></linearGradient></defs>${grids}<polygon points="45,145 ${line} 580,145" fill="url(#fill)"/><polyline points="${line}" fill="none" stroke="#528c70" stroke-width="2.5" stroke-linejoin="round"/>${xy.map((p,i)=>`<circle cx="${p[0]}" cy="${p[1]}" r="3" fill="#528c70"><title>${points[i].date}: ${money(points[i].value)}</title></circle>`).join('')}${[0,7,14,21,29].map(i=>`<text x="${xy[i][0]}" y="175" text-anchor="middle">${points[i].date.slice(5).replace('-','/')}</text>`).join('')}</svg>`;
}
function recordHTML(data, tools=true) {
  return data.map(r=>`<div class="record"><div class="record-icon">${icons[categories.indexOf(r.category)] || '🛍'}</div><div class="record-info"><div class="record-name">${esc(r.name)}</div><div class="record-meta">${esc(r.date)} · ${esc(r.category)}${r.merchant?' · '+esc(r.merchant):''}${r.source==='sample'?' · 시연 데이터':''}${r.memo?' · '+esc(r.memo):''}</div></div><div class="record-price">${money(r.value)}</div>${tools?`<div class="record-tools"><button data-edit="${esc(r.id)}">수정</button><button data-delete="${esc(r.id)}">삭제</button></div>`:''}</div>`).join('') || '<div class="empty"><strong>아직 기록이 없어요.</strong>사진을 올리거나 직접 첫 지출을 기록해보세요.<br>연결 설정에서 시연 데이터 120건을 추가할 수도 있어요.</div>';
}
function renderRecords() {
  const q=$('#search').value.toLowerCase(), category=$('#filter-category').value;
  const filtered=rows.filter(r=>(!category||r.category===category)&&[r.name,r.memo,r.merchant].join(' ').toLowerCase().includes(q));
  $('#record-list').innerHTML=recordHTML(filtered); $('#record-count').textContent=`${filtered.length}건 · ${money(filtered.reduce((a,r)=>a+r.value,0))}`;
}
function renderSummary() {
  $('#chat-summary').innerHTML=[['기록 기간',stats.start?`${stats.start}<br>~ ${stats.end}`:'없음'],['기록 수',stats.count+'건'],['전체 지출',money(stats.total)],['이번 달',money(stats.this_month)],['최근 추세',stats.trend]].map(([k,v])=>`<div class="summary-row"><span>${k}</span><strong>${v}</strong></div>`).join('');
}
function categoryOptions(selected='기타'){return categories.map(c=>`<option ${c===selected?'selected':''}>${c}</option>`).join('');}
function readDraft(){ draft=$$('.draft-item').map(el=>({name:el.querySelector('[name=name]').value,category:el.querySelector('[name=category]').value,value:el.querySelector('[name=value]').value,memo:el.querySelector('[name=memo]').value})); }
function drawDraft(){
  $('#draft-items').innerHTML=draft.map((d,i)=>`<div class="draft-item"><div class="form-row"><label>상품·항목명<input name="name" required maxlength="100" value="${esc(d.name)}" placeholder="예: 운동화"></label><label>카테고리<select name="category">${categoryOptions(d.category)}</select></label><label>금액 (원)<input name="value" type="number" min="0" max="1000000000" step="1" required value="${esc(d.value??'')}" placeholder="직접 입력"></label><button class="remove-item" type="button" data-remove="${i}" aria-label="항목 삭제">×</button></div><input name="memo" maxlength="500" value="${esc(d.memo||'')}" placeholder="메모 (선택)" aria-label="메모"></div>`).join('');
  $('#add-item').hidden=kind==='product'||!!editing; updateTotal();
}
function updateTotal(){
  readDraft(); const total=draft.reduce((a,d)=>a+Number(d.value||0),0); $('#draft-total').textContent=money(total);
  $('#total-check').textContent=expectedTotal===null?'인식된 상품명과 실제 결제금액을 확인한 뒤 저장해주세요.':`영수증 결제 총액 ${money(expectedTotal)} · ${total===expectedTotal?'항목 합계와 일치합니다.':'항목 합계와 다릅니다. 할인·수량을 확인하고 수정해주세요.'}`;
}
function setKind(next){kind=next; analyzed=false; expectedTotal=null; $('#photo').value=''; $('#photo-preview').hidden=true; if(photoURL) URL.revokeObjectURL(photoURL); photoURL=null; $('#analyze-button').disabled=true; $$('.tabs button').forEach(b=>b.classList.toggle('active',b.dataset.kind===kind)); $('#upload-area').hidden=kind==='manual'; $('#upload-label').textContent=kind==='receipt'?'영수증 사진을 올려주세요':'상품 하나가 보이는 사진을 올려주세요'; $('#analysis-message').hidden=true; draft=[{name:'',category:'기타',value:'',memo:''}]; drawDraft(); }
function openEntry(row=null){
  editing=row; $('#entry-title').textContent=row?'지출 기록 수정':'어떤 소비를 했나요?'; $('#upload-section').hidden=!!row; $('#entry-date').value=row?.date||localDate(); $('#entry-merchant').value=row?.merchant||''; setKind(row?'manual':'receipt');
  if(row){draft=[{...row}];drawDraft();} $('#entry-dialog').showModal();
}
function notifyAnalysis(message){$('#analysis-message').textContent=message;$('#analysis-message').hidden=false;}
async function analyze(){
  const file=$('#photo').files[0]; if(!file)return;
  const button=$('#analyze-button');button.disabled=true;button.textContent='사진 분석 중…';
  try{
    const data=new FormData();data.append('file',file);data.append('kind',kind);
    const result=await request('/analyze',{method:'POST',body:data});
    draft=result.items; expectedTotal=result.total; analyzed=true;
    $('#entry-date').value=result.date||localDate();$('#entry-merchant').value=result.merchant||'';drawDraft();
    notifyAnalysis(result.warnings.length?result.warnings.join('\n'):'분석이 완료됐어요. 상품명·분류·금액을 확인해주세요.');
  }catch(e){notifyAnalysis(e.message+'\n아래에서 직접 입력해 저장할 수 있어요.');}
  finally{button.disabled=false;button.textContent='다시 분석하기 ✧';}
}
async function saveEntry(e){
  e.preventDefault();readDraft(); if(!draft.length){toast('최소 한 개의 항목을 추가해주세요.');return;}
  const total=draft.reduce((a,d)=>a+Number(d.value),0);
  if(expectedTotal!==null&&total!==expectedTotal){toast('영수증 총액과 항목 합계가 다릅니다. 항목 금액을 수정해주세요.');return;}
  const group=kind==='receipt'&&analyzed?crypto.randomUUID():null;
  const entries=draft.map(d=>({date:$('#entry-date').value,name:d.name,value:Number(d.value),category:d.category,memo:d.memo,merchant:$('#entry-merchant').value,source:editing?.source||(analyzed?kind:'manual'),receipt_id:editing?.receipt_id||group}));
  const button=$('#save-entry');button.disabled=true;
  try{if(editing)await request('/data/'+editing.id,{method:'PUT',body:JSON.stringify(entries[0])});else await request('/data/batch',{method:'POST',body:JSON.stringify({entries})});$('#entry-dialog').close();await refresh();toast(editing?'수정했어요.':`${entries.length}건의 지출을 저장했어요.`);}
  catch(err){toast(err.message);}finally{button.disabled=false;}
}
function drawMessages(messages=[]){
  $('#messages').innerHTML=messages.length?messages.map(m=>`<div class="message ${m.role==='user'?'user':'assistant'}">${esc(m.content)}</div>`).join(''):'<div class="welcome"><span>✧</span><h3>내 소비, 같이 돌아볼까요?</h3><p>기록 속 숫자를 이해하기 쉽게 풀어드려요.<br>아래 질문을 눌러 대화를 시작해보세요.</p></div>';
  $('#messages').scrollTop=$('#messages').scrollHeight;
}
async function sendChat(e){
  e.preventDefault();if(busyChat)return;const input=$('#chat-input'), draftMessage=input.value, message=draftMessage.trim();if(!message)return;
  busyChat=true;$('#send-chat').disabled=true;$('.suggestions').hidden=true;
  input.value='';input.focus();
  const previous=currentConversation?.messages||[];drawMessages([...previous,{role:'user',content:message}]);
  const loading=document.createElement('div');loading.className='message assistant loading';loading.textContent='지출 기록을 살펴보고 있어요…';$('#messages').append(loading);$('#messages').scrollTop=$('#messages').scrollHeight;
  try{const result=await request('/chat',{method:'POST',body:JSON.stringify({message,conversation_id:currentConversation?.id||null})});if(!result.messages?.at(-1)?.content?.trim())throw new Error('AI가 빈 답변을 반환했습니다. 잠시 후 다시 전송해주세요.');currentConversation=result;drawMessages(currentConversation.messages);}
  catch(err){drawMessages([...previous,{role:'user',content:message},{role:'assistant',content:'답변을 받지 못했어요. '+err.message}]);if(input.value==='')input.value=draftMessage;toast(err.message);}finally{busyChat=false;$('#send-chat').disabled=false;}
}
async function loadHistory(){const history=await request('/conversations');$('#history-list').innerHTML=history.map(c=>`<article class="history-card"><div class="small-label">SAVED CONVERSATION</div><h3>${esc(c.title)}</h3><p>${esc(new Date(c.updated_at).toLocaleString('ko-KR'))}</p><button class="primary" data-load="${esc(c.id)}">대화 이어보기 →</button><button data-delete-chat="${esc(c.id)}">삭제</button></article>`).join('')||'<div class="empty"><strong>아직 저장된 대화가 없어요.</strong>AI 소비 상담에서 첫 질문을 보내보세요.</div>';}
function downloadCSV(){
  const quote=v=>'"'+String(v??'').replace(/^[=+@\-\t\r]/,"'$&").replace(/"/g,'""')+'"';
  const data=[['날짜','상품명','분류','금액','가게명','메모'],...rows.map(r=>[r.date,r.name,r.category,r.value,r.merchant,r.memo])].map(row=>row.map(quote).join(',')).join('\r\n');
  const url=URL.createObjectURL(new Blob(['\ufeff'+data],{type:'text/csv;charset=utf-8;'}));const a=document.createElement('a');a.href=url;a.download=`씀로그_${localDate()}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function connect(){
  $('#connection-banner').hidden=false;$('#connection-banner').textContent='서버에 연결하고 있어요. 무료 서버의 첫 접속은 최대 1분 이상 걸릴 수 있어요.';
  try{const status=await request('/status');$('#mode-badge').textContent=status.mode==='demo'?'● 시연 모드':'● AI 연결됨';$('#connection-banner').hidden=status.mode!=='demo';$('#connection-banner').textContent='시연 모드 · 로컬 파일에 저장됩니다. 사진 인식은 비활성화되어 있으며, 채팅은 통계 기반 시연 응답입니다. 연결 설정에서 가상 데이터 120건을 추가할 수 있어요.';await refresh();}
  catch(e){$('#mode-badge').textContent='연결 확인 필요';$('#connection-banner').textContent=e.message+' 우측 연결 설정에서 API 주소를 확인해주세요.';toast(e.message);}
}
$$('.nav').forEach(b=>b.onclick=()=>navigate(b.dataset.view));$$('.add-button').forEach(b=>b.onclick=()=>openEntry());
$$('[data-close]').forEach(b=>b.onclick=()=>$('#'+b.dataset.close).close());
$$('.tabs button').forEach(b=>b.onclick=()=>setKind(b.dataset.kind));
$('#add-item').onclick=()=>{readDraft();draft.push({name:'',category:'기타',value:'',memo:''});drawDraft();};
$('#draft-items').oninput=updateTotal;
$('#draft-items').onclick=e=>{const b=e.target.closest('[data-remove]');if(b){readDraft();draft.splice(Number(b.dataset.remove),1);drawDraft();}};
$('#entry-form').onsubmit=saveEntry;$('#analyze-button').onclick=analyze;
$('#photo').onchange=()=>{const file=$('#photo').files[0];if(!file)return;if(file.size>4*1024*1024){toast('4MB 이하의 사진을 선택해주세요.');$('#photo').value='';return;} if(photoURL)URL.revokeObjectURL(photoURL);photoURL=URL.createObjectURL(file);$('#photo-preview').src=photoURL;$('#photo-preview').hidden=false;$('#analyze-button').disabled=false;$('#analysis-message').hidden=true;analyzed=false;expectedTotal=null;};
$('#search').oninput=renderRecords;$('#filter-category').innerHTML+='<option>'+categories.join('</option><option>')+'</option>';$('#filter-category').onchange=renderRecords;
document.addEventListener('click',async e=>{const b=e.target.closest('[data-edit],[data-delete],[data-load],[data-delete-chat]');if(!b)return;try{
  if(b.dataset.edit)openEntry(rows.find(r=>r.id===b.dataset.edit));
  if(b.dataset.delete&&confirm('이 지출 기록을 삭제할까요?')){await request('/data/'+b.dataset.delete,{method:'DELETE'});await refresh();toast('삭제했어요.');}
  if(b.dataset.load){if(busyChat){toast('답변 완료 후 대화를 불러와주세요.');return;}currentConversation=await request('/conversations/'+b.dataset.load);drawMessages(currentConversation.messages);navigate('chat');}
  if(b.dataset.deleteChat&&confirm('이 대화를 삭제할까요?')){await request('/conversations/'+b.dataset.deleteChat,{method:'DELETE'});if(currentConversation?.id===b.dataset.deleteChat){currentConversation=null;drawMessages();}await loadHistory();}
}catch(err){toast(err.message);}});
$('#go-chat').onclick=()=>navigate('chat');$('#all-records').onclick=()=>navigate('records');$('#export').onclick=downloadCSV;
$('#chat-form').onsubmit=sendChat;$$('.suggestions button').forEach(b=>b.onclick=()=>{$('#chat-input').value=b.textContent;$('#chat-form').requestSubmit();});
$('#new-chat').onclick=()=>{if(busyChat)return;currentConversation=null;drawMessages();$('.suggestions').hidden=false;$('#chat-input').value='';};
$('#theme').onclick=()=>{document.body.classList.toggle('dark');localStorage.setItem('sseumlog-dark',document.body.classList.contains('dark'));};if(localStorage.getItem('sseumlog-dark')==='true')document.body.classList.add('dark');
$('#settings').onclick=()=>{$('#api-url').value=apiBase;$('#access-token').value=token;$('#swagger').href=apiBase+'/docs';$('#settings-dialog').showModal();};
$('#mobile-settings').onclick=()=>$('#settings').click();
$('#settings-form').onsubmit=async e=>{e.preventDefault();const url=new URL($('#api-url').value);if(!['https:','http:'].includes(url.protocol)){toast('HTTP 또는 HTTPS 주소를 입력해주세요.');return;}apiBase=url.origin;token=$('#access-token').value;localStorage.setItem('sseumlog-api',apiBase);sessionStorage.setItem('sseumlog-token',token);currentConversation=null;drawMessages();$('#settings-dialog').close();await connect();};
$('#seed').onclick=async()=>{const b=$('#seed');b.disabled=true;try{await request('/demo/seed',{method:'POST'});await refresh();toast('가상 데이터 120건을 추가했어요.');}catch(e){toast(e.message);}finally{b.disabled=false;}};
drawMessages();connect();
