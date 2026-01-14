from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from pydantic import BaseModel
from supabase import create_client, Client
from datetime import datetime, date
import traceback
import os

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

# Supabase 설정
from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("❌ .env 파일에 SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY가 없습니다.")

# Supabase 클라이언트 생성 (service_role 키 사용 - RLS 우회)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

print(f"✅ Supabase 연결 완료: {SUPABASE_URL}")

# Pydantic 모델 (응답 형식)
class MenuResponse(BaseModel):
    id: int
    post_no: str
    post_date: date
    week_start: date
    week_end: date
    day_of_week: str
    menu_text: str
    created_at: datetime


# DB 연결 헬퍼 (Supabase 클라이언트 반환)
def get_db() -> Client:
    """Supabase 클라이언트 반환"""
    return supabase


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
    """오늘 날짜의 식단 조회"""
    try:
        today = datetime.now().date()
        
        # Supabase에서 오늘 날짜의 메뉴 조회
        response = supabase.table("menus").select("*").eq("post_date", str(today)).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail=f"오늘({today}) 식단이 없습니다.")
        
        return {
            "date": str(today),
            "count": len(response.data),
            "menus": response.data
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 오늘 식단 조회 실패: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")


@app.get("/menus")
def get_all_menus(limit: int = Query(default=100, ge=1, le=500)):
    """전체 메뉴 조회 (최신순)"""
    try:
        response = supabase.table("menus").select("*").order("post_date", desc=True).limit(limit).execute()
        
        return {
            "count": len(response.data),
            "menus": response.data
        }
    except Exception as e:
        print(f"❌ 전체 메뉴 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")


@app.get("/menus/date/{target_date}")
def get_menus_by_date(target_date: str):
    """특정 날짜의 식단 조회 (YYYY-MM-DD 형식)"""
    try:
        # 날짜 형식 검증
        datetime.strptime(target_date, "%Y-%m-%d")
        
        response = supabase.table("menus").select("*").eq("post_date", target_date).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail=f"{target_date} 식단이 없습니다.")
        
        return {
            "date": target_date,
            "count": len(response.data),
            "menus": response.data
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="날짜 형식이 잘못되었습니다. YYYY-MM-DD 형식으로 입력하세요.")
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 날짜별 메뉴 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")


@app.get("/menus/week/{week_start}")
def get_menus_by_week(week_start: str):
    """주간 식단 조회 (주 시작일 기준, YYYY-MM-DD 형식)"""
    try:
        # 날짜 형식 검증
        datetime.strptime(week_start, "%Y-%m-%d")
        
        response = supabase.table("menus").select("*").eq("week_start", week_start).order("day_of_week").execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail=f"{week_start} 주의 식단이 없습니다.")
        
        return {
            "week_start": week_start,
            "count": len(response.data),
            "menus": response.data
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="날짜 형식이 잘못되었습니다. YYYY-MM-DD 형식으로 입력하세요.")
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 주간 메뉴 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")


@app.get("/stats")
def get_stats():
    """통계 정보 조회"""
    try:
        # 전체 메뉴 개수
        menus_response = supabase.table("menus").select("id", count="exact").execute()
        
        # 크롤링 상태
        state_response = supabase.table("crawl_state").select("*").eq("id", 1).execute()
        
        # 최근 크롤링 로그
        logs_response = supabase.table("crawl_logs").select("*").order("crawled_at", desc=True).limit(5).execute()
        
        return {
            "total_menus": menus_response.count if menus_response.count else 0,
            "crawl_state": state_response.data[0] if state_response.data else None,
            "recent_logs": logs_response.data
        }
    except Exception as e:
        print(f"❌ 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")
