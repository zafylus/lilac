import json, os
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from urllib.parse import urljoin
from pathlib import Path
from sqlite_setup import init_database, insert_menus

#Base Url  
LIST_URL = "https://www.pknu.ac.kr/main/399"
STATE_FILE = "state.json"
JSON_DIR = Path(__file__).with_name("jsons")
JSON_DIR.mkdir(exist_ok=True)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def searchTable(n: int, name: str):
    """n번째 테이블 찾기"""
    tables = page.locator("table")
    print(f"총 테이블 개수: {tables.count()}")
    
    target = tables.nth(n)
    target.scroll_into_view_if_needed()
    page.wait_for_timeout(200)
    print(f'{name} 테이블 찾음')
    
    return target

def extract_table_data(target):
    """테이블에서 날짜, 메뉴 추출"""
    rows = target.locator("tr").all()
    
    # Row 0: 요일 (구분, Monday, Tuesday, ...)
    headers = [cell.inner_text().strip() for cell in rows[0].locator("th, td").all()]
    
    # Row 1: 날짜 (11월 10일, 11월 11일, ...)
    dates = [cell.inner_text().strip() for cell in rows[1].locator("th, td").all()]
    
    # Row 2: 메뉴 (중식 가격 정보, 메뉴1, 메뉴2, ...)
    menus = [cell.inner_text().strip() for cell in rows[2].locator("th, td").all()]
    
    return {
        'headers': headers,
        'dates': dates,
        'menus': menus
    }

def format_daily_menus(raw_data, cafeteria_name, post_number, post_date):
    """
    SQL 삽입용 하루씩 데이터 포맷으로 변환
    결과: [
        {'cafeteria': '라일락', 'date': '11월 10일', 'meals': '잡곡밥, 소고기국, ...', 'post_number': '722286', 'post_date': '2025.01.06'},
        {'cafeteria': '라일락', 'date': '11월 11일', 'meals': '잡곡밥, 시락국, ...', 'post_number': '722286', 'post_date': '2025.01.06'},
        ...
    ]
    """
    dates = raw_data['dates'][:]  # 첫 번째 "구분" 제외
    menus = raw_data['menus'][1:]  # 첫 번째 "가격 정보" 제외
    # print('===dates===')
    # print(dates)
    # print('===menus===')
    # print(menus)
    daily_data = []
    
    for i, date in enumerate(dates):
        if i >= len(menus):
            break
            
        # 메뉴 텍스트를 줄바꿈으로 분리하여 쉼표로 연결
        menu_text = menus[i]
        menu_items = [item.strip() for item in menu_text.split('\n') if item.strip()]
        meals_str = ', '.join(menu_items)
        
        daily_data.append({
            'cafeteria': cafeteria_name,
            'date': date,
            'meals': meals_str,
            'post_number': post_number,  # 원본 링크용
            'crawled_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 크롤링 시각
        })
    
    return daily_data

# Playwright 실행
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, channel="chrome")
    ctx = browser.new_context(
        locale="ko-KR",
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
        ),
        viewport={"width": 1280, "height": 1200}
    )
    page = ctx.new_page()

    # 1) 목록 페이지 진입
    page.goto(LIST_URL, wait_until="domcontentloaded", timeout=45000)
    
    # 2) 게시물 번호, 날짜 저장
    brdNum = page.locator("td.bdlNum").first.inner_text()
    brdDate = page.locator("td.bdlDate").first.inner_text()
    print(f"게시물 번호: {brdNum}, 날짜: {brdDate}")

    state = load_state()
    state["last_post_no"] = brdNum
    state["last_post_date"] = brdDate
    save_state(state)
    
    # 3) 상세 페이지로 이동
    page.wait_for_selector("td.bdlTitle a")
    target_link = page.locator("td.bdlTitle a").first
    href = target_link.get_attribute("href")
    page.goto(urljoin(LIST_URL, href), wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(1000)
    
    print("\n" + "="*60)
    print("라일락 식당 데이터 추출")
    print("="*60)
    
    # 4) 라일락 테이블 추출 및 하루씩 정리
    lilac_table = searchTable(2, '라일락')
    lilac_raw = extract_table_data(lilac_table)
    lilac_daily = format_daily_menus(lilac_raw, '라일락', brdNum, brdDate)
    
    print("\n[하루씩 정리된 데이터 - SQL INSERT 준비 완료]")
    for idx, item in enumerate(lilac_daily, 1):
        print(f"\n{idx}. 식당: {item['cafeteria']}")
        print(f"   날짜: {item['date']}")
        print(f"   메뉴: {item['meals'][:80]}...")
    
    # print("\n" + "="*60)
    # print("다래락 식당 데이터 추출")
    # print("="*60)
    
    # # 5) 다래락 테이블 추출 및 하루씩 정리
    # darae_table = searchTable(3, '다래락')
    # darae_raw = extract_table_data(darae_table)
    # darae_daily = format_daily_menus(darae_raw, '다래락', brdNum, brdDate)
    
    # print("\n[하루씩 정리된 데이터 - SQL INSERT 준비 완료]")
    # for idx, item in enumerate(darae_daily, 1):
    #     print(f"\n{idx}. 식당: {item['cafeteria']}")
    #     print(f"   날짜: {item['date']}")
    #     print(f"   메뉴: {item['meals'][:80]}...")
    
    # print("\n" + "="*60)
    # print("최종 데이터 구조 (모든 식당, 모든 날짜)")
    # print("="*60)
    
    # # 6) 모든 데이터를 하나의 리스트로 합치기
    # all_menus = lilac_daily + darae_daily
    
    # print(f"\n총 {len(all_menus)}개 row가 DB에 저장됩니다:")
    # print(json.dumps(all_menus, ensure_ascii=False, indent=2))
    
    # 이제 all_menus를 반복문 돌려서 SQL INSERT 하면 됨!
    # for menu in all_menus:
    #     cursor.execute(
    #         "INSERT INTO menus (cafeteria, date, meals, post_number, post_date) VALUES (?, ?, ?, ?, ?)",
    #         (menu['cafeteria'], menu['date'], menu['meals'], menu['post_number'], menu['post_date'])
    #     )
    # init_database()  # 처음 한 번만 실행 (테이블 생성)
    insert_menus(lilac_daily)  # 크롤링한 데이터 저장
    browser.close()
    
    print("\n✅ 데이터 정리 완료! all_menus 변수에 모든 데이터가 하루씩 담겨있음")