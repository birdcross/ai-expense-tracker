from datetime import date as Date
from typing import Literal
from pydantic import BaseModel, Field, field_validator

CATEGORIES = ['식비', '카페·간식', '생활용품', '의류·신발', '교통', '문화·여가', '건강', '기타']

class Entry(BaseModel):
    date: Date
    value: int = Field(ge=0, le=1_000_000_000)
    memo: str = Field(default='', max_length=500)
    name: str = Field(min_length=1, max_length=100)
    category: str = '기타'
    merchant: str = Field(default='', max_length=100)
    source: Literal['manual', 'receipt', 'product', 'sample'] = 'manual'
    receipt_id: str | None = Field(default=None, max_length=64)

    @field_validator('name')
    @classmethod
    def nonempty(cls, v):
        if not v.strip():
            raise ValueError('항목명을 입력해주세요.')
        return v.strip()

    @field_validator('category')
    @classmethod
    def category_valid(cls, v):
        if v not in CATEGORIES:
            raise ValueError('지원하지 않는 카테고리입니다.')
        return v

class Batch(BaseModel):
    entries: list[Entry] = Field(min_length=1, max_length=100)

class Message(BaseModel):
    role: Literal['user', 'assistant']
    content: str = Field(min_length=1, max_length=6000)

class Conversation(BaseModel):
    title: str = Field(default='새 지출 상담', min_length=1, max_length=100)
    messages: list[Message] = Field(min_length=1, max_length=100)

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = Field(default=None, max_length=64)

class AnalysisItem(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    category: str
    value: int | None = Field(default=None, ge=0, le=1_000_000_000)
    memo: str = Field(default='', max_length=500)

class Analysis(BaseModel):
    date: Date | None = None
    merchant: str = Field(default='', max_length=100)
    items: list[AnalysisItem] = Field(min_length=1, max_length=60)
    total: int | None = Field(default=None, ge=0)
    warnings: list[str] = Field(default_factory=list)
