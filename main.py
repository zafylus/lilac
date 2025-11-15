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

# 디버깅용 에러 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print(f"❌ 에러 발생: {exc}")
    print(traceback.format_exc())
    return {
        "error": str(exc),
        "traceback": traceback.format_exc()
    }

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
class Menu(BaseModel):
    id: int
    cafeteria: str
    date: str
    meals: str
    post_number: Optional[str]
    crawled_at: str

class MenuSimple(BaseModel):
    cafeteria: str
    date: str
    meals: List[str]  # 쉼표로 분리된 메뉴 리스트

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


@app.get("/menus")
def get_all_menus(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """
    전체 식단 조회 (페이지네이션)
    - limit: 가져올 개수 (최대 100)
    - offset: 시작 위치
    """
    try:
        print(f"📥 /menus 요청 - limit: {limit}, offset: {offset}")
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, cafeteria, date, meals, post_number, crawled_at
            FROM menus
            ORDER BY date DESC, cafeteria
            LIMIT ? OFFSET ?
        """, (limit, offset))
        
        rows = cursor.fetchall()
        print(f"✅ 조회된 행 개수: {len(rows)}")
        
        conn.close()
        
        result = []
        for row in rows:
            result.append({
                "id": row["id"],
                "cafeteria": row["cafeteria"],
                "date": row["date"],
                "meals": row["meals"],
                "post_number": row["post_number"],
                "crawled_at": row["crawled_at"]
            })
        
        return result
        
    except Exception as e:
        print(f"❌ /menus 에러: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/menus/date/{date}")
def get_menus_by_date(date: str, cafeteria: Optional[str] = None):
    """
    특정 날짜의 식단 조회
    - date: 날짜 (예: 11월 18일)
    - cafeteria: 식당명 (선택, 예: 라일락)
    """
    conn = get_db()
    cursor = conn.cursor()
    
    if cafeteria:
        cursor.execute("""
            SELECT id, cafeteria, date, meals, post_number, crawled_at
            FROM menus
            WHERE date = ? AND cafeteria = ?
        """, (date, cafeteria))
    else:
        cursor.execute("""
            SELECT id, cafeteria, date, meals, post_number, crawled_at
            FROM menus
            WHERE date = ?
            ORDER BY cafeteria
        """, (date,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        raise HTTPException(status_code=404, detail=f"{date} 식단 정보를 찾을 수 없습니다")
    
    # 메뉴를 리스트로 변환하여 반환
    result = []
    for row in rows:
        menu_dict = dict(row)
        menu_dict['meals'] = [m.strip() for m in menu_dict['meals'].split(',')]
        result.append(menu_dict)
    
    return result


@app.get("/menus/cafeteria/{cafeteria}")
def get_menus_by_cafeteria(
    cafeteria: str,
    limit: int = Query(default=10, ge=1, le=50)
):
    """
    특정 식당의 최근 식단 조회
    - cafeteria: 식당명 (예: 라일락, 다래락)
    - limit: 가져올 개수
    """
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, cafeteria, date, meals, post_number, crawled_at
        FROM menus
        WHERE cafeteria = ?
        ORDER BY date DESC
        LIMIT ?
    """, (cafeteria, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        raise HTTPException(status_code=404, detail=f"{cafeteria} 식당 정보를 찾을 수 없습니다")
    
    return [dict(row) for row in rows]


@app.get("/menus/today")
def get_today_menus():
    """
    오늘 날짜의 식단 조회
    (실제로는 DB에 저장된 가장 최근 날짜)
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # 가장 최근 날짜 찾기
    cursor.execute("""
        SELECT DISTINCT date
        FROM menus
        ORDER BY crawled_at DESC
        LIMIT 1
    """)
    
    latest_date_row = cursor.fetchone()
    
    if not latest_date_row:
        conn.close()
        raise HTTPException(status_code=404, detail="식단 정보가 없습니다")
    
    latest_date = latest_date_row[0]
    
    # 해당 날짜의 모든 식당 메뉴 조회
    cursor.execute("""
        SELECT id, cafeteria, date, meals, post_number, crawled_at
        FROM menus
        WHERE date = ?
        ORDER BY cafeteria
    """, (latest_date,))
    
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        menu_dict = dict(row)
        menu_dict['meals'] = [m.strip() for m in menu_dict['meals'].split(',')]
        result.append(menu_dict)
    
    return result


@app.get("/menus/search")
def search_menus(q: str = Query(..., min_length=2)):
    """
    메뉴 검색
    - q: 검색어 (예: 불고기, 김치찌개)
    """
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, cafeteria, date, meals, post_number, crawled_at
        FROM menus
        WHERE meals LIKE ?
        ORDER BY date DESC
        LIMIT 20
    """, (f"%{q}%",))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        raise HTTPException(status_code=404, detail=f"'{q}' 검색 결과가 없습니다")
    
    return [dict(row) for row in rows]


@app.get("/stats")
def get_stats():
    """데이터베이스 통계"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 전체 데이터 개수
    cursor.execute("SELECT COUNT(*) FROM menus")
    total = cursor.fetchone()[0]
    
    # 식당별 개수
    cursor.execute("""
        SELECT cafeteria, COUNT(*) as count
        FROM menus
        GROUP BY cafeteria
    """)
    cafeteria_stats = [{"cafeteria": row[0], "count": row[1]} for row in cursor.fetchall()]
    
    # 최근 업데이트
    cursor.execute("""
        SELECT date, crawled_at
        FROM menus
        ORDER BY crawled_at DESC
        LIMIT 1
    """)
    latest = cursor.fetchone()
    
    conn.close()
    
    return {
        "total_menus": total,
        "cafeterias": cafeteria_stats,
        "latest_update": {
            "date": latest[0] if latest else None,
            "crawled_at": latest[1] if latest else None
        }
    }


@app.get("/health")
def health_check():
    """헬스 체크"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# ============================================
# 실행
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)