import sqlite3
from pathlib import Path
from datetime import datetime

# DB 파일 경로
DB_FILE = Path(__file__).with_name("pknu_menus.db")

def init_database():
    """데이터베이스 초기화 및 테이블 생성"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 메뉴 테이블 생성
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS menus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cafeteria TEXT NOT NULL,
            date TEXT NOT NULL,
            meals TEXT NOT NULL,
            post_number TEXT,
            crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(cafeteria, date)
        )
    """)
    
    # 인덱스 생성 (조회 성능 향상)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_date 
        ON menus(date)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_cafeteria 
        ON menus(cafeteria)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_cafeteria_date 
        ON menus(cafeteria, date)
    """)
    
    conn.commit()
    conn.close()
    print(f"✅ 데이터베이스 초기화 완료: {DB_FILE}")


def insert_menus(menu_list):
    """
    메뉴 데이터 삽입
    menu_list: [
        {'cafeteria': '라일락', 'date': '11월 18일', 'meals': '...', 'post_number': '211'},
        ...
    ]
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    inserted = 0
    skipped = 0
    
    for menu in menu_list:
        try:
            cursor.execute("""
                INSERT INTO menus (cafeteria, date, meals, post_number)
                VALUES (?, ?, ?, ?)
            """, (
                menu['cafeteria'],
                menu['date'],
                menu['meals'],
                menu.get('post_number')
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            # UNIQUE 제약 위반 (이미 존재하는 데이터)
            skipped += 1
            print(f"   ⚠️  이미 존재: {menu['cafeteria']} - {menu['date']}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ 삽입 완료: {inserted}개")
    if skipped > 0:
        print(f"⚠️  중복 스킵: {skipped}개")
    
    return inserted, skipped


def get_menu_by_date(date, cafeteria=None):
    """특정 날짜의 식단 조회"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if cafeteria:
        cursor.execute("""
            SELECT * FROM menus 
            WHERE date = ? AND cafeteria = ?
        """, (date, cafeteria))
    else:
        cursor.execute("""
            SELECT * FROM menus 
            WHERE date = ?
        """, (date,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return rows


def get_all_menus():
    """전체 식단 조회"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, cafeteria, date, meals, post_number, crawled_at
        FROM menus 
        ORDER BY date DESC, cafeteria
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return rows


def delete_old_menus(days=30):
    """오래된 식단 삭제 (일정 기간 이전)"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM menus 
        WHERE crawled_at < datetime('now', '-' || ? || ' days')
    """, (days,))
    
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    
    print(f"✅ {days}일 이전 데이터 {deleted}개 삭제")
    return deleted


def get_db_stats():
    """데이터베이스 통계"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 전체 행 개수
    cursor.execute("SELECT COUNT(*) FROM menus")
    total = cursor.fetchone()[0]
    
    # 식당별 개수
    cursor.execute("""
        SELECT cafeteria, COUNT(*) 
        FROM menus 
        GROUP BY cafeteria
    """)
    cafeteria_stats = cursor.fetchall()
    
    # 가장 최근 데이터
    cursor.execute("""
        SELECT date, crawled_at 
        FROM menus 
        ORDER BY crawled_at DESC 
        LIMIT 1
    """)
    latest = cursor.fetchone()
    
    conn.close()
    
    print(f"\n📊 데이터베이스 통계")
    print(f"총 데이터: {total}개")
    print(f"식당별:")
    for cafe, count in cafeteria_stats:
        print(f"  - {cafe}: {count}개")
    if latest:
        print(f"최근 업데이트: {latest[0]} (크롤링: {latest[1]})")


def get_today_menus():
    """
    오늘 날짜의 식단 조회
    오늘 날짜 메뉴가 없으면 가장 최근 메뉴를 반환
    
    Returns:
        dict: {
            'is_today': bool,  # 오늘 날짜 메뉴인지 여부
            'date': str,  # 메뉴 날짜
            'message': str,  # 사용자에게 보여줄 메시지
            'menus': list[dict]  # 메뉴 리스트
        }
        None: 메뉴가 전혀 없는 경우
    """
    from datetime import datetime
    
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 오늘 날짜 구하기 (예: "12월 5일")
    today = datetime.now()
    today_str = f"{today.month}월 {today.day}일"
    
    # 1. 먼저 오늘 날짜 메뉴가 있는지 확인
    cursor.execute("""
        SELECT id, cafeteria, date, meals, post_number, crawled_at
        FROM menus
        WHERE date = ?
        ORDER BY cafeteria
    """, (today_str,))
    
    today_rows = cursor.fetchall()
    
    if today_rows:
        # 오늘 메뉴가 있는 경우
        menus = []
        for row in today_rows:
            menu_dict = dict(row)
            menu_dict['meals'] = [m.strip() for m in menu_dict['meals'].split(',')]
            menus.append(menu_dict)
        
        conn.close()
        return {
            'id': today_rows[0]['id'],
            'is_today': True,
            'date': today_str,
            'message': f'오늘({today_str}) 식단입니다.',
            'menus': menus
        }
    
    # 2. 오늘 메뉴가 없으면 가장 최근 메뉴 찾기
    cursor.execute("""
        SELECT DISTINCT date
        FROM menus
        ORDER BY crawled_at DESC
        LIMIT 1
    """)
    
    latest_date_row = cursor.fetchone()
    
    if not latest_date_row:
        conn.close()
        return None
    
    latest_date = latest_date_row[0]
    
    # 가장 최근 날짜의 메뉴 조회
    cursor.execute("""
        SELECT id, cafeteria, date, meals, post_number, crawled_at
        FROM menus
        WHERE date = ?
        ORDER BY cafeteria
    """, (latest_date,))
    
    rows = cursor.fetchall()
    conn.close()
    
    # 결과를 딕셔너리 리스트로 변환
    menus = []
    for row in rows:
        menu_dict = dict(row)
        menu_dict['meals'] = [m.strip() for m in menu_dict['meals'].split(',')]
        menus.append(menu_dict)
    
    return {
        'id': latest_rows[0]['id'],
        'is_today': False,
        'date': latest_date,
        'message': f'오늘({today_str})은 식단이 없습니다. 가장 최근 식단({latest_date})을 보여드립니다.',
        'menus': menus
    }


