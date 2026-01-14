"""
Supabase 연동 클라이언트
"""
import os
from datetime import datetime
from supabase import create_client, Client


def get_client() -> Client:
    """Supabase 클라이언트 생성"""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL과 SUPABASE_KEY 환경변수를 설정하세요.")

    return create_client(url, key)


# ============================================
# crawl_state 테이블 (상태 관리)
# ============================================

def get_last_state(client: Client) -> dict | None:
    """
    마지막 크롤링 상태 조회
    Returns: {'last_post_no': '211', 'last_post_date': '2025-01-13'} or None
    """
    response = client.table("crawl_state").select("*").eq("id", 1).execute()

    if response.data:
        return response.data[0]
    return None


def update_state(client: Client, post_no: str, post_date: str):
    """크롤링 상태 업데이트 (upsert)"""
    client.table("crawl_state").upsert({
        "id": 1,
        "last_post_no": post_no,
        "last_post_date": post_date,
        "updated_at": datetime.now().isoformat()
    }).execute()


# ============================================
# menus 테이블 (식단 데이터)
# ============================================

def upsert_menus(client: Client, menus: list[dict]):
    """
    메뉴 데이터 upsert (post_no + day_of_week 기준)

    menus: [
        {
            'post_no': '211',
            'post_date': '2025-01-13',
            'week_start': '2025-01-13',
            'week_end': '2025-01-17',
            'day_of_week': '월',
            'menu_text': '...'
        },
        ...
    ]
    """
    if not menus:
        return

    response = client.table("menus").upsert(
        menus,
        on_conflict="post_no,day_of_week"
    ).execute()

    return response


def get_menus_by_week(client: Client, week_start: str) -> list[dict]:
    """특정 주의 메뉴 조회"""
    response = client.table("menus").select("*").eq("week_start", week_start).order("day_of_week").execute()
    return response.data


# ============================================
# crawl_logs 테이블 (크롤링 로그)
# ============================================

def log_crawl(client: Client, status: str, message: str, post_no: str = None, post_date: str = None, new_data: bool = False):
    """
    크롤링 로그 기록

    status: 'success' | 'skipped' | 'error'
    """
    client.table("crawl_logs").insert({
        "post_no": post_no,
        "post_date": post_date,
        "status": status,
        "message": message,
        "new_data": new_data
    }).execute()
