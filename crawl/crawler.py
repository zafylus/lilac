"""
부경대 식단 게시판 크롤러 (Playwright)
"""
from datetime import datetime
from playwright.sync_api import sync_playwright, Page
from urllib.parse import urljoin


LIST_URL = "https://www.pknu.ac.kr/main/399"


def get_latest_post_info(page: Page) -> tuple[str, str]:
    """
    목록 페이지에서 최신 게시물 번호와 날짜 추출
    Returns: (post_no, post_date)  예: ("211", "2025.01.13")
    """
    post_no = page.locator("td.bdlNum").first.inner_text()
    post_date = page.locator("td.bdlDate").first.inner_text()
    return post_no, post_date


def go_to_detail_page(page: Page):
    """상세 페이지로 이동"""
    page.wait_for_selector("td.bdlTitle a")
    target_link = page.locator("td.bdlTitle a").first
    href = target_link.get_attribute("href")
    page.goto(urljoin(LIST_URL, href), wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(1000)


def find_table(page: Page, index: int, name: str):
    """n번째 테이블 찾기"""
    tables = page.locator("table")
    print(f"총 테이블 개수: {tables.count()}")

    target = tables.nth(index)
    target.scroll_into_view_if_needed()
    page.wait_for_timeout(200)
    print(f'{name} 테이블 찾음')

    return target


def extract_table_data(table) -> dict:
    """테이블에서 요일, 날짜, 메뉴 추출"""
    rows = table.locator("tr").all()

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


def format_daily_menus(raw_data: dict, cafeteria_name: str, post_number: str) -> list[dict]:
    """
    테이블 데이터를 하루씩 분리하여 리스트로 변환

    Returns: [
        {'cafeteria': '라일락', 'date': '11월 10일', 'meals': '...', 'post_number': '211'},
        ...
    ]
    """
    dates = raw_data['dates'][:]
    menus = raw_data['menus'][1:]  # 첫 번째 "가격 정보" 제외

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
            'post_number': post_number
        })

    return daily_data


def crawl_menus(headless: bool = True) -> tuple[list[dict], str, str]:
    """
    메뉴 크롤링 실행

    Returns: (menus_data, post_no, post_date)
        - menus_data: [{'cafeteria': '라일락', 'date': '11월 10일', 'meals': '...', 'post_number': '211'}, ...]
        - post_no: 게시물 번호 (예: "211")
        - post_date: 게시물 날짜 (예: "2025.01.13")
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(
            locale="ko-KR",
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
            ),
            viewport={"width": 1280, "height": 1200}
        )
        page = ctx.new_page()

        try:
            # 1) 목록 페이지 진입
            page.goto(LIST_URL, wait_until="domcontentloaded", timeout=45000)

            # 2) 최신 게시물 번호, 날짜 추출
            post_no, post_date = get_latest_post_info(page)
            print(f"게시물 번호: {post_no}, 날짜: {post_date}")

            # 3) 상세 페이지로 이동
            go_to_detail_page(page)

            # 4) 라일락 테이블 추출
            print("\n" + "=" * 60)
            print("라일락 식당 데이터 추출")
            print("=" * 60)

            lilac_table = find_table(page, 2, '라일락')
            lilac_raw = extract_table_data(lilac_table)
            lilac_daily = format_daily_menus(lilac_raw, '라일락', post_no)

            # 결과 출력
            print("\n[크롤링 완료]")
            for idx, item in enumerate(lilac_daily, 1):
                print(f"{idx}. {item['date']}: {item['meals'][:50]}...")

            return lilac_daily, post_no, post_date

        finally:
            browser.close()


def check_for_new_post(last_post_no: str, last_post_date: str, headless: bool = True) -> tuple[bool, str, str]:
    """
    새 게시물이 있는지 확인 (크롤링 없이 목록만 확인)

    Returns: (is_new, current_post_no, current_post_date)
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(
            locale="ko-KR",
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
            ),
            viewport={"width": 1280, "height": 1200}
        )
        page = ctx.new_page()

        try:
            page.goto(LIST_URL, wait_until="domcontentloaded", timeout=45000)
            current_no, current_date = get_latest_post_info(page)

            is_new = (current_no != last_post_no) or (current_date != last_post_date)
            return is_new, current_no, current_date

        finally:
            browser.close()
