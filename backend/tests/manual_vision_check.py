"""Opt-in paid vision smoke test: python backend/tests/manual_vision_check.py.

Requires Pillow in the executing environment. Uses only synthetic images and
calls the running server; never saves synthetic purchases into the database.
"""
import json
from pathlib import Path
from time import monotonic

import httpx
from dotenv import dotenv_values
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs' / 'vision-smoke'
OUT.mkdir(parents=True, exist_ok=True)
FONT = 'C:/Windows/Fonts/malgun.ttf'


def receipt():
    image = Image.new('RGB', (1000, 1100), '#f6f2e8')
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(FONT, 35)
    lines = [
        '테스트 카페', '테스트용 가상 영수증', '2026-10-29',
        '--------------------------------',
        '상품              수량       금액(원)',
        '아메리카노         2           9,000',
        '쿠키               1           3,200',
        '--------------------------------',
        '최종 결제금액                  12,200',
        '결제수단: 카드',
        '실제 구매 내역이 아닙니다.',
    ]
    for i, line in enumerate(lines):
        draw.text((65, 65 + i * 80), line, font=font, fill='#161616')
    path = OUT / 'receipt.png'
    image.save(path)
    return path


def product():
    image = Image.new('RGB', (900, 900), '#eeeeee')
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((200, 150, 700, 750), radius=20, fill='#d8ecd1', outline='#396047', width=5)
    font = ImageFont.truetype(FONT, 60)
    draw.text((285, 300), '녹차 티백', font=font, fill='#203b25')
    draw.text((315, 420), '20개입', font=font, fill='#203b25')
    draw.text((140, 800), '테스트용 상품 이미지 · 가격 정보 없음', font=ImageFont.truetype(FONT, 30), fill='#222222')
    path = OUT / 'product-no-price.png'
    image.save(path)
    return path


def main():
    cfg = dotenv_values(ROOT / 'backend' / '.env')
    results = []
    with httpx.Client(base_url='http://127.0.0.1:8017', headers={'X-App-Token': cfg.get('APP_ACCESS_TOKEN') or ''}, timeout=110) as client:
        before = client.get('/api/data/summary').raise_for_status().json()['count']
        for kind, path in [('receipt', receipt()), ('product', product())]:
            start = monotonic()
            with path.open('rb') as image_file:
                response = client.post('/api/analyze', data={'kind': kind}, files={'file': (path.name, image_file, 'image/png')})
            payload = response.json()
            result = {'kind': kind, 'status': response.status_code, 'seconds': round(monotonic() - start, 2), 'response': payload}
            results.append(result)
            print(json.dumps(result, ensure_ascii=True), flush=True)
        after = client.get('/api/data/summary').raise_for_status().json()['count']
    report = {'results': results, 'records_before': before, 'records_after': after}
    (OUT / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    assert before == after, 'Smoke test changed expense records'
    assert all(r['status'] == 200 for r in results), 'Vision endpoint failed; see result.json'
    receipt_result, product_result = [r['response'] for r in results]
    assert receipt_result['date'] == '2026-10-29'
    assert receipt_result['total'] == 12200
    assert sorted(i['value'] for i in receipt_result['items']) == [3200, 9000]
    assert len(product_result['items']) == 1
    assert product_result['items'][0]['value'] is None, 'Invented a price without a price tag'
    print('PASS: receipt totals, line amounts, product unknown-price handling; no purchases saved.')


if __name__ == '__main__':
    main()
