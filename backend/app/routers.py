import base64
import hmac
import os
import random
import threading
import time
from pathlib import Path
from datetime import date, timedelta
from uuid import uuid4
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / '.env')
from fastapi import APIRouter, Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .models import Batch, ChatRequest, Conversation, Entry
from .store import store, now
from .services import answer, summarize, analyze_image, korea_today

MODE = os.getenv('APP_MODE', 'demo')
if MODE not in ('demo', 'production'):
    raise RuntimeError('APP_MODE must be demo or production')
if MODE == 'production' and not os.getenv('OPENAI_API_KEY'):
    raise RuntimeError('Production requires OPENAI_API_KEY')


def authorized(x_app_token: str = Header(default='')):
    token = os.getenv('APP_ACCESS_TOKEN', '')
    if token and not hmac.compare_digest(token, x_app_token):
        raise HTTPException(401, '앱 접근 암호를 확인해주세요.')

api = APIRouter(prefix='/api', dependencies=[Depends(authorized)])
ai_lock = threading.Lock()
last_calls = []
def limit_ai():
    with ai_lock:
        stamp = time.monotonic()
        last_calls[:] = [t for t in last_calls if stamp-t < 60]
        if len(last_calls) >= 10:
            raise HTTPException(429, 'AI 요청은 분당 10회까지 가능합니다. 잠시 후 다시 시도해주세요.')
        last_calls.append(stamp)

def existing(collection, key):
    # Firestore document IDs must not contain path separators.
    if '/' in key or len(key) > 64:
        raise HTTPException(404, '기록을 찾을 수 없습니다.')
    row = store.get(collection, key)
    if not row:
        raise HTTPException(404, '기록을 찾을 수 없습니다.')
    return row

@api.get('/status')
def status():
    return {'mode':MODE, 'image_analysis':MODE == 'production', 'storage':'Firestore' if store.db else '로컬 JSON'}

@api.get('/data/summary')
def summary():
    return summarize(store.all('data'))

@api.get('/data')
def list_data():
    return sorted(store.all('data'), key=lambda x:(x['date'], x.get('created_at','')), reverse=True)

@api.post('/data', status_code=201)
def create_data(entry: Entry):
    return store.put('data', dict(entry.model_dump(mode='json'), created_at=now()))

@api.post('/data/batch', status_code=201)
def batch_data(batch: Batch):
    return store.put_many('data', [dict(e.model_dump(mode='json'), created_at=now()) for e in batch.entries])

@api.put('/data/{key}')
def update_data(key: str, entry: Entry):
    old = existing('data', key)
    return store.put('data', dict(entry.model_dump(mode='json'), created_at=old.get('created_at', now()), updated_at=now()), key)

@api.delete('/data/{key}', status_code=204)
def delete_data(key: str):
    existing('data', key)
    store.delete('data', key)

@api.post('/conversations', status_code=201)
def save_conversation(conversation: Conversation):
    return store.put('conversations', dict(conversation.model_dump(), updated_at=now()))

@api.get('/conversations')
def list_conversations():
    return sorted([{k:v for k,v in c.items() if k != 'messages'} for c in store.all('conversations')], key=lambda c:c['updated_at'], reverse=True)

@api.get('/conversations/{key}')
def get_conversation(key: str):
    return existing('conversations', key)

@api.delete('/conversations/{key}', status_code=204)
def delete_conversation(key: str):
    existing('conversations', key)
    store.delete('conversations', key)

@api.post('/chat')
def chat(request: ChatRequest):
    limit_ai()
    old = existing('conversations', request.conversation_id) if request.conversation_id else None
    messages = old['messages'][:] if old else []
    if len(messages) >= 98:
        raise HTTPException(400, '새 대화를 시작해주세요. 대화당 최대 100개 메시지입니다.')
    messages.append({'role':'user','content':request.message})
    try:
        result = answer(messages, summary())
    except Exception:
        raise HTTPException(502, 'AI 응답을 받지 못했습니다. 연결 및 API 설정을 확인하고 다시 시도해주세요.')
    messages.append({'role':'assistant','content':result})
    return store.put('conversations', {'title':old['title'] if old else request.message[:40], 'messages':messages, 'updated_at':now()}, request.conversation_id)

@api.post('/analyze')
async def analyze(file: UploadFile = File(...), kind: str = Form(...)):
    if MODE != 'production':
        raise HTTPException(503, '시연 모드는 사진 인식을 제공하지 않습니다. OpenAI 호환 API를 설정하고 운영 모드로 전환해주세요.')
    if kind not in ('receipt','product'):
        raise HTTPException(422, '영수증 또는 상품 사진을 선택해주세요.')
    raw = await file.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(413, '사진은 8MB 이하로 올려주세요.')
    mime = 'image/jpeg' if raw.startswith(b'\xff\xd8\xff') else 'image/png' if raw.startswith(b'\x89PNG\r\n\x1a\n') else 'image/webp' if raw[:4] == b'RIFF' and raw[8:12] == b'WEBP' else None
    if not mime:
        raise HTTPException(415, 'JPG, PNG, WEBP 사진을 올려주세요.')
    limit_ai()
    from starlette.concurrency import run_in_threadpool
    try:
        return await run_in_threadpool(analyze_image, f'data:{mime};base64,{base64.b64encode(raw).decode()}', kind)
    except Exception:
        raise HTTPException(502, '사진 분석에 실패했습니다. 더 선명한 사진으로 다시 시도하거나 직접 입력해주세요.')

@api.post('/demo/seed', status_code=201)
def seed():
    if MODE != 'demo':
        raise HTTPException(403, '운영 모드에서는 시연 데이터를 만들 수 없습니다.')
    if store.all('data'):
        raise HTTPException(409, '기록이 이미 있습니다. 빈 저장소에서만 시연 데이터를 추가할 수 있습니다.')
    rng = random.Random(42)
    choices = [('점심 식사','식비',9500), ('아메리카노','카페·간식',4500), ('생필품','생활용품',13000), ('대중교통','교통',3000), ('영화','문화·여가',15000), ('티셔츠','의류·신발',29000)]
    values=[]
    for i in range(120):
        name, cat, amount = rng.choice(choices)
        values.append(dict(date=(korea_today()-timedelta(days=i)).isoformat(), value=amount+rng.randrange(0,5)*500, name=name, category=cat, memo='실제 소비가 아닌 시연용 가상 데이터', merchant='시연 가맹점', source='sample', receipt_id=None, created_at=now()))
    store.put_many('data', values)
    return {'count':120}

