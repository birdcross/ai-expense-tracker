import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .routers import api, MODE

app = FastAPI(title='씀로그 API', version='1.0.0', description='영수증·상품 사진 기반 개인 지출 관리')
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in os.getenv('ALLOWED_ORIGINS', 'http://localhost:8017,http://127.0.0.1:8017').split(',') if x.strip()], allow_methods=['GET','POST','PUT','DELETE'], allow_headers=['Content-Type','X-App-Token'])
app.include_router(api)

@app.get('/health')
def health():
    return {'status':'ok', 'mode':MODE}

frontend = Path(__file__).resolve().parents[2] / 'frontend'
if frontend.exists():
    app.mount('/assets', StaticFiles(directory=frontend), name='assets')
    @app.get('/')
    def index():
        return FileResponse(frontend / 'index.html')
