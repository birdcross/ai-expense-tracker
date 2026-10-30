"""Opt-in live checks. Uses configured deployment token; deletes only its own records.

Run: python backend/tests/manual_deployment_check.py
The real AI provider is called (usage charges may apply).
"""
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
from uuid import uuid4
import httpx

ROOT = Path(__file__).resolve().parents[2]
BASE = 'https://ai-expense-tracker-tau-sepia.vercel.app'


def main():
    token = (ROOT / '.vercel/access-password.txt').read_text().strip()
    report = {'checked_at': datetime.now(timezone(timedelta(hours=9))).isoformat(), 'url': BASE, 'checks': []}
    expenses, conversations = [], []
    marker = 'final-check-' + uuid4().hex[:12]

    def passed(name):
        report['checks'].append({'name': name, 'passed': True})
        print('PASS: ' + name, flush=True)

    with httpx.Client(base_url=BASE, headers={'X-App-Token': token}, timeout=100) as client:
        def call(method, path, code=200, **kwargs):
            response = client.request(method, path, **kwargs)
            assert response.status_code == code, f'{method} {path}: expected {code}, got {response.status_code}'
            return response.json() if response.content else None

        baseline = call('GET', '/api/data')
        try:
            for path in ['/', '/health', '/docs', '/openapi.json', '/assets/app.js', '/assets/style.css', '/assets/config.js']:
                assert client.get(path).status_code == 200, path
            passed('public UI, static files, health and Swagger')
            for path in ['/api/status', '/api/data', '/api/data/summary', '/api/conversations']:
                assert client.get(path, headers={'X-App-Token': ''}).status_code == 401
                assert client.get(path, headers={'X-App-Token': 'invalid'}).status_code == 401
            for path in ['/.env', '/backend/.env', '/backend/service-account.json', '/.git/config', '/.vercel/access-password.txt']:
                assert client.get(path).status_code == 404
            passed('missing/wrong passwords denied; secret file URLs inaccessible')
            status = call('GET', '/api/status')
            assert status['mode'] == 'production' and status['storage'] == 'Firestore'
            passed('production mode and Firestore')
            summary = call('GET', '/api/data/summary')
            assert summary['count'] == len(baseline)
            assert summary['total'] == sum(row['value'] for row in baseline)
            assert sum(summary['categories'].values()) == summary['total']
            assert sum(row['value'] for row in summary['daily']) == summary['total']
            passed('dashboard counts, total, daily and category aggregates')
            entry = {'date': report['checked_at'][:10], 'name': marker, 'value': 1100, 'category': '기타', 'memo': 'Temporary verification record', 'source': 'manual'}
            row = call('POST', '/api/data', 201, json=entry)
            expenses.append(row['id'])
            updated = call('PUT', '/api/data/' + row['id'], json=entry | {'value': 2200, 'merchant': 'Verification'})
            assert updated['value'] == 2200 and updated['created_at'] == row['created_at']
            assert next(r for r in call('GET', '/api/data') if r['id'] == row['id'])['value'] == 2200
            passed('expense create, update and persisted read')
            rows = call('POST', '/api/data/batch', 201, json={'entries': [entry, entry | {'value': 3300}]})
            expenses.extend(row['id'] for row in rows)
            current = call('GET', '/api/data/summary')
            call('POST', '/api/data/batch', 422, json={'entries': [entry, entry | {'value': -1}]})
            assert call('GET', '/api/data/summary')['count'] == current['count']
            call('POST', '/api/data', 422, json=entry | {'date': 'invalid'})
            call('POST', '/api/data', 422, json=entry | {'category': 'invalid'})
            passed('batch save and atomic rejection of invalid input')
            call('POST', '/api/demo/seed', 403)
            call('GET', '/api/conversations/does-not-exist', 404)
            call('DELETE', '/api/data/does-not-exist', 404)
            passed('production seed protection and missing-record handling')
            call('POST', '/api/analyze', 415, data={'kind': 'receipt'}, files={'file': ('invalid.png', b'invalid', 'image/png')})
            call('POST', '/api/analyze', 422, data={'kind': 'invalid'}, files={'file': ('invalid.png', b'invalid', 'image/png')})
            call('POST', '/api/analyze', 413, data={'kind': 'receipt'}, files={'file': ('large.png', b'x' * (4 * 1024 * 1024 + 1), 'image/png')})
            passed('image format, kind and 4 MiB upload validation')
            for kind, filename in [('receipt', 'receipt.png'), ('product', 'product-no-price.png')]:
                with (ROOT / 'docs/vision-smoke' / filename).open('rb') as file:
                    result = call('POST', '/api/analyze', data={'kind': kind}, files={'file': (filename, file, 'image/png')})
                if kind == 'receipt':
                    assert result['total'] == 12200
                    assert sorted(item['value'] for item in result['items']) == [3200, 9000]
                else:
                    assert len(result['items']) == 1 and result['items'][0]['value'] is None
                    assert result['items'][0]['name'] != '확인 필요'
                passed('real Anthropic analysis: ' + kind)
            conversation = call('POST', '/api/conversations', 201, json={'title': marker, 'messages': [{'role': 'user', 'content': 'Temporary conversation'}]})
            conversations.append(conversation['id'])
            assert call('GET', '/api/conversations/' + conversation['id'])['messages'] == conversation['messages']
            assert all('messages' not in c for c in call('GET', '/api/conversations'))
            passed('conversation save/list/load')
            chat = call('POST', '/api/chat', json={'message': marker + ' 검증입니다. 현재 전체 기록 건수와 총액만 짧게 알려주세요.'})
            conversations.append(chat['id'])
            assert len(chat['messages']) == 2 and chat['messages'][-1]['content'].strip()
            continued = call('POST', '/api/chat', json={'message': '확인했습니다. 한 문장으로 답해주세요.', 'conversation_id': chat['id']})
            assert len(continued['messages']) == 4 and continued['messages'][-1]['content'].strip()
            assert call('GET', '/api/conversations/' + chat['id'])['messages'] == continued['messages']
            passed('real OpenAI chat, autosave and conversation continuation')
        finally:
            cleanup_errors = []
            for collection, keys in [('data', expenses), ('conversations', conversations)]:
                for key in keys:
                    try:
                        call('DELETE', '/api/' + collection + '/' + key, 204)
                    except Exception:
                        cleanup_errors.append(collection + '/' + key)
            report['cleanup_success'] = not cleanup_errors
            report['cleanup_errors'] = cleanup_errors
            output = ROOT / 'docs/verification'
            output.mkdir(parents=True, exist_ok=True)
            (output / 'deployment.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            assert not cleanup_errors, 'Temporary verification records could not be cleaned up'
        after = call('GET', '/api/data')
        assert not any(row['id'] in expenses for row in after)
        assert {row['id'] for row in baseline}.issubset({row['id'] for row in after})
        passed('temporary records removed and existing expense records preserved')
        report['all_passed'] = True
        (ROOT / 'docs/verification/deployment.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
