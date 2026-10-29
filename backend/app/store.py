"""Storage boundary: Firestore or atomic local JSON, selected independently of AI."""
import json
import os
import threading
import uuid
from pathlib import Path
from datetime import datetime, timezone

def now():
    return datetime.now(timezone.utc).isoformat()

class Store:
    def __init__(self):
        self.lock = threading.RLock()
        self.path = Path(os.getenv('LOCAL_DATA_PATH', str(Path(__file__).parent.parent / 'local-data.json')))
        self.db = None
        storage_mode = os.getenv('STORAGE_MODE', 'local')
        if storage_mode not in ('local', 'firestore'):
            raise RuntimeError('STORAGE_MODE must be local or firestore')
        if storage_mode == 'firestore':
            import firebase_admin
            from firebase_admin import credentials, firestore
            raw = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')
            cred = credentials.Certificate(json.loads(raw)) if raw else credentials.ApplicationDefault()
            project_id = os.getenv('FIREBASE_PROJECT_ID', '').strip()
            credential_project = getattr(cred, 'project_id', None)
            if project_id and credential_project and credential_project != project_id:
                raise RuntimeError('Firebase credential project does not match FIREBASE_PROJECT_ID')
            try:
                firebase_app = firebase_admin.get_app('sseumlog')
            except ValueError:
                firebase_app = firebase_admin.initialize_app(
                    cred, {'projectId': project_id} if project_id else None,
                    name='sseumlog',
                )
            if project_id and firebase_app.project_id != project_id:
                raise RuntimeError('Firebase credential project does not match FIREBASE_PROJECT_ID')
            self.db = firestore.client(app=firebase_app)

    def _read(self):
        return json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {'data': {}, 'conversations': {}}

    def _write(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        tmp.replace(self.path)

    def all(self, collection):
        if self.db:
            return [dict(doc.to_dict(), id=doc.id) for doc in self.db.collection(collection).stream()]
        with self.lock:
            return [dict(v, id=k) for k, v in self._read()[collection].items()]

    def get(self, collection, key):
        if self.db:
            doc = self.db.collection(collection).document(key).get()
            return dict(doc.to_dict(), id=key) if doc.exists else None
        with self.lock:
            value = self._read()[collection].get(key)
            return dict(value, id=key) if value else None

    def put(self, collection, value, key=None):
        return self.put_many(collection, [value], [key or uuid.uuid4().hex])[0]

    def put_many(self, collection, values, keys=None):
        keys = keys or [uuid.uuid4().hex for _ in values]
        if self.db:
            batch = self.db.batch()
            for key, value in zip(keys, values):
                batch.set(self.db.collection(collection).document(key), value)
            batch.commit()
        else:
            with self.lock:
                data = self._read()
                for key, value in zip(keys, values):
                    data[collection][key] = value
                self._write(data)
        return [dict(v, id=k) for k, v in zip(keys, values)]

    def delete(self, collection, key):
        if self.db:
            self.db.collection(collection).document(key).delete()
        else:
            with self.lock:
                data = self._read()
                data[collection].pop(key, None)
                self._write(data)

store = Store()
