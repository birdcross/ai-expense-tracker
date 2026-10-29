"""Verify real Firestore writes/reads without touching expense or chat records."""
from pathlib import Path
from uuid import uuid4
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / '.env')

from app.store import store, now


def main():
    if store.db is None:
        raise SystemExit('Firestore is not enabled. Set STORAGE_MODE=firestore.')
    key = uuid4().hex
    expected = {
        'checked_at': now(),
        'purpose': 'sseumlog Firestore connection verification',
        'entry_shape': {'date': '2026-10-29', 'value': 0, 'receipt_id': None},
        'conversation_shape': {'messages': [{'role': 'user', 'content': 'connection check'}]},
    }
    store.put('_connection_checks', expected, key)
    actual = store.get('_connection_checks', key)
    if actual != dict(expected, id=key):
        raise RuntimeError('Firestore read-after-write verification failed')
    # Check both application collections can be read. Never print private records.
    for collection in ('data', 'conversations'):
        next(store.db.collection(collection).limit(1).stream(), None)
    print('Firestore write/read OK; project=' + store.db.project)
    print('Verification document: _connection_checks/' + key)


if __name__ == '__main__':
    main()
