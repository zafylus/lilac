from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from pydantic import BaseModel
import sqlite3
from pathlib import Path
from datetime import datetime
import traceback

# FastAPI 앱 생성
app = FastAPI(
    title="부경대 식단 API",
    description="부경대학교 식당 식단 정보를 제공하는 API",
    version="1.0.0"
)

# CORS 설정 (모바일 앱에서 접근 가능하도록)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB 파일 경로
DB_FILE = Path(__file__).parent / "crawl/pknu_menus.db"

print(f"📂 DB 파일 경로: {DB_FILE}")
print(f"📂 DB 파일 존재 여부: {DB_FILE.exists()}")

# Pydantic 모델 (응답 형식)


# DB 연결 헬퍼
def get_db():
    try:
        if not DB_FILE.exists():
            raise FileNotFoundError(f"DB 파일이 없습니다: {DB_FILE}")
        
        conn = sqlite3.connect(str(DB_FILE))
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"❌ DB 연결 실패: {e}")
        raise


# ============================================
# API 엔드포인트
# ============================================


@app.get("/")
def root():
    """API 루트"""
    return {
        "message": "부경대 식단 API",
        "version": "1.0.0",
        "endpoints": {
            "전체 식단": "/menus",
            "날짜별 조회": "/menus/date/{date}",
            "식당별 조회": "/menus/cafeteria/{cafeteria}",
            "오늘 식단": "/menus/today",
            "통계": "/stats"
        }
    }


@app.get("/menus/today")
def get_today_menus():
    result = get_today_menus() 
    return result

