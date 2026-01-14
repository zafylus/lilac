"""
날짜 파싱 및 데이터 변환 유틸리티
"""
from datetime import datetime, timedelta
import re


def parse_korean_date(date_str: str, year: int = None) -> datetime:
    """
    한국어 날짜 문자열을 datetime으로 변환
    예: "11월 10일" -> datetime(2025, 11, 10)
    """
    if year is None:
        year = datetime.now().year

    match = re.match(r'(\d+)월\s*(\d+)일', date_str)
    if not match:
        raise ValueError(f"날짜 파싱 실패: {date_str}")

    month = int(match.group(1))
    day = int(match.group(2))

    return datetime(year, month, day)


def get_day_of_week(dt: datetime) -> str:
    """datetime에서 한국어 요일 반환"""
    days = ['월', '화', '수', '목', '금', '토', '일']
    return days[dt.weekday()]


def get_week_range(dt: datetime) -> tuple[datetime, datetime]:
    """
    주어진 날짜가 속한 주의 월요일~금요일 반환
    """
    # 월요일 찾기 (weekday: 0=월, 1=화, ...)
    monday = dt - timedelta(days=dt.weekday())
    friday = monday + timedelta(days=4)
    return monday, friday


def parse_post_date(post_date_str: str) -> datetime:
    """
    게시물 날짜 문자열을 datetime으로 변환
    예: "2025.01.13" 또는 "2025-01-13" -> datetime(2025, 1, 13)
    """
    # 점(.) 또는 하이픈(-) 형식 모두 지원
    for fmt in ["%Y.%m.%d", "%Y-%m-%d"]:
        try:
            return datetime.strptime(post_date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"날짜 파싱 실패: {post_date_str}")


def format_date_for_db(dt: datetime) -> str:
    """datetime을 DB 저장용 문자열로 변환 (YYYY-MM-DD)"""
    return dt.strftime("%Y-%m-%d")


def transform_to_supabase_format(crawled_data: list[dict], post_date_str: str) -> list[dict]:
    """
    크롤링 데이터를 Supabase menus 테이블 형식으로 변환

    Input (crawled_data):
    [
        {'cafeteria': '라일락', 'date': '11월 10일', 'meals': '...', 'post_number': '211'},
        ...
    ]

    Output:
    [
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
    # 게시물 날짜에서 연도 추출
    post_dt = parse_post_date(post_date_str)
    year = post_dt.year

    result = []
    for item in crawled_data:
        # 날짜 파싱
        menu_date = parse_korean_date(item['date'], year)
        day_of_week = get_day_of_week(menu_date)
        week_start, week_end = get_week_range(menu_date)

        result.append({
            'post_no': item['post_number'],
            'post_date': format_date_for_db(post_dt),
            'week_start': format_date_for_db(week_start),
            'week_end': format_date_for_db(week_end),
            'day_of_week': day_of_week,
            'menu_date': format_date_for_db(menu_date),
            'menu_text': item['meals']
        })

    return result
