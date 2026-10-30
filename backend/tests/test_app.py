import os
import sys
from pathlib import Path
from datetime import date, timedelta
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['APP_MODE'] = 'demo'
os.environ['STORAGE_MODE'] = 'local'
os.environ['VISION_PROVIDER'] = 'openai'
os.environ['APP_ACCESS_TOKEN'] = ''
from fastapi.testclient import TestClient
from app.main import app
from app.store import store
from app.services import summarize

@pytest.fixture
def client(tmp_path):
    store.path = tmp_path / 'records.json'
    return TestClient(app)

def entry(**kw):
    return dict(date=date.today().isoformat(), value=9000, name='김치찌개', category='식비', **kw)

def test_crud_validation_and_summary(client):
    assert client.post('/api/data', json=entry() | {'value':-1}).status_code == 422
    assert client.post('/api/data', json=entry() | {'category':'invalid'}).status_code == 422
    row=client.post('/api/data', json=entry()).json()
    assert client.get('/api/data/summary').json()['total'] == 9000
    assert client.put('/api/data/'+row['id'], json=entry() | {'value':10000}).status_code == 200
    assert client.get('/api/data').json()[0]['value'] == 10000
    assert client.delete('/api/data/'+row['id']).status_code == 204
    assert client.get('/api/data/summary').json()['count'] == 0
    assert client.delete('/api/data/missing').status_code == 404

def test_batch_is_atomic_and_receipt_total_not_duplicated(client):
    response=client.post('/api/data/batch', json={'entries':[entry(),entry() | {'name':'커피','value':3000}]})
    assert response.status_code == 201
    assert client.get('/api/data/summary').json()['total'] == 12000
    assert client.post('/api/data/batch', json={'entries':[entry(),entry() | {'value':-1}]}).status_code == 422
    assert len(client.get('/api/data').json()) == 2

def test_chat_auto_save_load_continue_delete(client):
    client.post('/api/data',json=entry())
    c=client.post('/api/chat',json={'message':'이번 달 식비는?'}).json()
    assert len(c['messages'])==2 and '9,000' in c['messages'][1]['content']
    assert 'messages' not in client.get('/api/conversations').json()[0]
    loaded=client.get('/api/conversations/'+c['id']).json()
    assert loaded['messages']==c['messages']
    continued=client.post('/api/chat',json={'message':'추세는?','conversation_id':c['id']}).json()
    assert len(continued['messages'])==4
    assert client.delete('/api/conversations/'+c['id']).status_code==204
    assert client.get('/api/conversations/'+c['id']).status_code==404

def test_seed_and_image_demo_rejection(client):
    assert client.post('/api/demo/seed').json()['count']==120
    assert client.get('/api/data/summary').json()['count']==120
    assert client.post('/api/demo/seed').status_code==409
    assert client.post('/api/analyze',data={'kind':'receipt'},files={'file':('r.png',b'fake','image/png')}).status_code==503

def test_access_control(client,monkeypatch):
    monkeypatch.setenv('APP_ACCESS_TOKEN','private')
    assert client.get('/api/data').status_code==401
    assert client.get('/api/data',headers={'X-App-Token':'private'}).status_code==200

def test_windows_aggregate_daily_and_trend():
    today=date.today()
    rows=[entry(),entry() | {'value':1000},entry() | {'date':(today-timedelta(days=7)).isoformat(),'value':5000}]
    result=summarize(rows)
    assert result['recent_7_days']==10000 and result['previous_7_days']==5000
    assert result['change_percent']==100 and result['trend']=='증가'
    assert len(result['daily'])==2 and result['daily'][-1]['value']==10000

def test_swagger_and_frontend(client):
    assert client.get('/docs').status_code==200
    assert client.get('/openapi.json').status_code==200
    assert client.get('/').status_code==200
    assert client.get('/assets/app.js').status_code==200

def test_vision_schema_and_receipt_mismatch(monkeypatch):
    import json
    from types import SimpleNamespace as NS
    from app import services
    payload={'items':[{'name':'커피','category':'식비','value':3000}],'total':2500}
    def create(**kwargs):
        assert kwargs['messages'][1]['content'][1]['type']=='image_url'
        return NS(choices=[NS(message=NS(content=json.dumps(payload)))])
    monkeypatch.setattr(services,'client',lambda:NS(chat=NS(completions=NS(create=create))))
    result=services.analyze_image('data:image/png;base64,aA==','receipt')
    assert result['items'][0]['value']==3000 and result['warnings']
    payload['items'].append({'name':'빵','category':'기타','value':None})
    with pytest.raises(ValueError):
        services.analyze_image('data:image/png;base64,aA==','product')

def test_image_file_validation(client,monkeypatch):
    from app import routers
    monkeypatch.setattr(routers,'MODE','production')
    assert client.post('/api/analyze',data={'kind':'product'},files={'file':('bad.jpg',b'not an image','image/jpeg')}).status_code==415
    assert client.post('/api/analyze',data={'kind':'wrong'},files={'file':('bad.jpg',b'abc','image/jpeg')}).status_code==422


def test_image_size_limit_before_provider_call(client, monkeypatch):
    from app import routers
    monkeypatch.setattr(routers, 'MODE', 'production')
    maximum = 4 * 1024 * 1024
    oversized = client.post('/api/analyze', data={'kind': 'receipt'}, files={'file': ('large.png', b'x' * (maximum + 1), 'image/png')})
    assert oversized.status_code == 413 and '4MB' in oversized.json()['detail']
    boundary = client.post('/api/analyze', data={'kind': 'receipt'}, files={'file': ('invalid.png', b'x' * maximum, 'image/png')})
    assert boundary.status_code == 415


def test_local_storage_with_real_ai_mode(tmp_path, monkeypatch):
    from app.store import Store
    monkeypatch.setenv('APP_MODE', 'production')
    monkeypatch.setenv('STORAGE_MODE', 'local')
    monkeypatch.setenv('LOCAL_DATA_PATH', str(tmp_path / 'local.json'))
    local = Store()
    assert local.db is None
    saved = local.put('data', entry())
    assert local.get('data', saved['id'])['value'] == 9000


def test_custom_openai_base_url(monkeypatch):
    from app import services
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    monkeypatch.setenv('OPENAI_BASE_URL', 'https://gateway.example/v1/')
    with services.client() as api_client:
        assert str(api_client.base_url) == 'https://gateway.example/v1/'


def test_anthropic_vision_native_protocol(monkeypatch):
    import json
    import httpx
    from app import services
    monkeypatch.setenv('VISION_PROVIDER', 'anthropic')
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-vision-key')
    monkeypatch.setenv('ANTHROPIC_BASE_URL', 'https://gateway.example/v1')
    monkeypatch.setenv('VISION_MODEL', 'claude-haiku-4')
    payload = {'items': [{'name': '커피', 'category': '카페·간식', 'value': 3000}], 'total': 3000}

    def post(url, **kwargs):
        assert url == 'https://gateway.example/v1/messages'
        assert kwargs['headers']['x-api-key'] == 'test-vision-key'
        body = kwargs['json']
        assert body['model'] == 'claude-haiku-4'
        assert body['messages'][0]['content'][0]['source'] == {'type': 'base64', 'media_type': 'image/png', 'data': 'aA=='}
        return httpx.Response(200, request=httpx.Request('POST', url), json={
            'stop_reason': 'end_turn', 'content': [{'type': 'text', 'text': '```json\n' + json.dumps(payload) + '\n```'}],
        })

    monkeypatch.setattr(services.httpx, 'post', post)
    result = services.analyze_image('data:image/png;base64,aA==', 'receipt')
    assert result['total'] == 3000 and len(result['items']) == 1
    payload['items'][0]['value'] = -1
    with pytest.raises(ValueError):
        services.analyze_image('data:image/png;base64,aA==', 'receipt')
