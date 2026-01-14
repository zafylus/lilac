from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from urllib.parse import urljoin
import json, os
from pathlib import Path

#Base Url  
LIST_URL = "https://www.pknu.ac.kr/main/399"
STATE_FILE = "state.json"
# 스크린샷 저장폴더
SCREENSHOT_DIR = Path(__file__).with_name("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def searchAndScreenshot(n: int, name: str, date: str):
    tables = page.locator("table")
    print("총 테이블 개수:", tables.count())

    target = tables.nth(n)

    target.scroll_into_view_if_needed()
    page.wait_for_timeout(200)
    path = SCREENSHOT_DIR / f"{name}_{date}.png"
    target.screenshot(path=str(path))
    print(f"{name} 식단 스크린샷 완료: {path}")
    

# Playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel="chrome")
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
    
    # 1-1) 게시물 번호, 날짜 저장
    brdNum = page.locator("td.bdlNum").first.inner_text()
    print(brdNum, type(brdNum))
    brdDate = page.locator("td.bdlDate").first.inner_text()
    print(brdDate, type(brdDate))

    state = load_state()
    print("이전 상태:", state)
    last_post_no = state.get('last_post_no')
    last_post_date = state.get("last_post_date")
    postFlag = last_post_no == brdNum and last_post_date == brdDate
    # 게시글 번호와 날짜 저장
    if (postFlag):
        print('아직 게시글이 안 올라왔습니다.')
        browser.close()
        raise SystemExit("[INFO] 프로그램을 종료합니다.")
    
    state["last_post_no"] = brdNum
    state["last_post_date"] = brdDate

    save_state(state)
    print("저장 완료:", state)
    
    # 2) 상세 페이지로 이동
    page.wait_for_selector("td.bdlTitle a")
    target_link = page.locator("td.bdlTitle a").first
    href = target_link.get_attribute("href")
    print("href:", href)
    page.goto(urljoin(LIST_URL, href), wait_until="domcontentloaded", timeout=45000)
    
    # 라일락 스크린샷
    searchAndScreenshot(2, '라일락', brdDate)
    # 다래락 스크린샷
    searchAndScreenshot(3, '다래락', brdDate)
    
    
    browser.close()
