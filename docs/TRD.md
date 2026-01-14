## TRD (Technical Requirements Document)

### 1. 시스템 아키텍처

```
GitHub Actions (스케줄러)
    ↓
Python + Playwright (크롤링)
    ↓
텍스트 파싱
    ↓
Supabase (DB 저장)
    ↑
Android App (조회)
```

### 2. 기술 스택

| 구성요소 | 기술 |
|---|---|
| 스케줄러 | GitHub Actions |
| 크롤러 | Python + Playwright |
| 데이터베이스 | Supabase (PostgreSQL) |
| 앱 | Android (Kotlin + Jetpack Compose) |
| 광고 | Google AdMob |

### 3. 데이터 흐름

```
1. GitHub Actions 트리거 (평일 오전)
2. 목록 페이지 접근
3. 최신 게시물 번호/날짜 확인
4. Supabase에서 마지막 수집 상태 조회
5. 비교:
   - 동일 → 로그 남기고 종료
   - 다름 → 상세 페이지 → 텍스트 파싱 → DB 저장
6. 크롤링 로그 기록
7. 안드로이드 앱에서 Supabase 직접 조회
```

### 4. Supabase 스키마

**테이블 1: `menus`** (식단 데이터)
```sql
CREATE TABLE menus (
  id BIGSERIAL PRIMARY KEY,
  post_no VARCHAR(10) NOT NULL,
  post_date DATE NOT NULL,
  week_start DATE NOT NULL,
  week_end DATE NOT NULL,
  day_of_week VARCHAR(5) NOT NULL,  -- '월' | '화' | '수' | '목' | '금'
  menu_text TEXT NOT NULL,
  price VARCHAR(20),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  
  UNIQUE(post_no, day_of_week)
);
```

**테이블 2: `crawl_logs`** (크롤링 로그)
```sql
CREATE TABLE crawl_logs (
  id BIGSERIAL PRIMARY KEY,
  crawled_at TIMESTAMPTZ DEFAULT NOW(),
  post_no VARCHAR(10),
  post_date DATE,
  status VARCHAR(20) NOT NULL,  -- 'success' | 'skipped' | 'error'
  message TEXT,
  new_data BOOLEAN DEFAULT FALSE
);
```

**테이블 3: `crawl_state`** (상태 관리)
```sql
CREATE TABLE crawl_state (
  id INT PRIMARY KEY DEFAULT 1,
  last_post_no VARCHAR(10),
  last_post_date DATE,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 5. API 설계 (Supabase 직접 호출)

**이번 주 식단 조회**
```
GET /rest/v1/menus?week_start=eq.2025-01-13&order=day_of_week
```

### 6. 파싱 데이터 구조

```python
{
  "post_no": "211",
  "post_date": "2025-01-13",
  "week_start": "2025-01-13",
  "week_end": "2025-01-17",
  "menus": [
    {
      "day_of_week": "월",
      "menu_text": "돈까스, 샐러드, 미소국, 밥",
      "price": "5000원"
    },
    {
      "day_of_week": "화",
      "menu_text": "제육볶음, 계란찜, 된장국, 밥",
      "price": "5000원"
    },
    ...
  ]
}
```

### 7. 크롤러 로직

```python
def main():
    # 1. 목록 페이지에서 최신 게시물 정보 추출
    post_no, post_date = get_latest_post_info()
    
    # 2. Supabase에서 마지막 상태 조회
    last_state = supabase.table("crawl_state").select("*").single().execute()
    
    # 3. 비교
    if post_no == last_state.last_post_no and post_date == last_state.last_post_date:
        log_crawl("skipped", "No new post")
        return
    
    # 4. 새 게시물 → 상세 페이지 파싱 (라일락만)
    menus = parse_lilac_menu()
    
    # 5. DB 저장
    supabase.table("menus").upsert(menus).execute()
    
    # 6. 상태 업데이트
    supabase.table("crawl_state").upsert({
        "id": 1,
        "last_post_no": post_no,
        "last_post_date": post_date
    }).execute()
    
    # 7. 로그 기록
    log_crawl("success", f"New post {post_no}", new_data=True)
```

### 8. GitHub Actions 스케줄

```yaml
on:
  schedule:
    - cron: '0 0 * * 1-5'   # 09:00 KST
    - cron: '0 1 * * 1-5'   # 10:00 KST
    - cron: '0 2 * * 1-5'   # 11:00 KST
```

### 9. 파일 구조

**크롤러**
```
/
├── .github/
│   └── workflows/
│       └── crawl.yml
├── crawler/
│   ├── main.py
│   ├── parser.py
│   └── db.py
├── requirements.txt
└── README.md
```

**안드로이드 앱**
```
app/
├── data/
│   ├── SupabaseClient.kt
│   └── MenuRepository.kt
├── domain/
│   └── Menu.kt
├── ui/
│   ├── MenuPagerScreen.kt
│   └── MenuCard.kt
├── ads/
│   └── AdBanner.kt
└── MainActivity.kt
```

### 10. 안드로이드 앱 상세

**화면 구성**
```
┌─────────────────────────┐
│       라일락 식단        │  ← 앱 타이틀
├─────────────────────────┤
│                         │
│     ← 월요일 →          │  ← 요일 표시
│                         │
│   돈까스                 │
│   샐러드                 │  ← 메뉴 카드
│   미소국                 │
│   밥                     │
│                         │
│   5,000원               │  ← 가격
│                         │
│    ● ○ ○ ○ ○           │  ← 페이지 인디케이터
├─────────────────────────┤
│      [광고 배너]         │  ← AdMob 배너
└─────────────────────────┘
```

**핵심 컴포넌트**

| 컴포넌트 | 역할 |
|---|---|
| `MenuPagerScreen` | HorizontalPager로 좌우 스와이프 구현 |
| `MenuCard` | 요일별 메뉴 표시 카드 |
| `AdBanner` | AdMob 배너 광고 |
| `MenuRepository` | Supabase에서 데이터 조회 |

**사용 라이브러리**
- Jetpack Compose (UI)
- Accompanist Pager (스와이프)
- Supabase Kotlin SDK
- Google AdMob SDK

### 11. 환경 변수

**GitHub Secrets (크롤러)**
```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJhbGc...
```

**Android (local.properties)**
```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJhbGc...
ADMOB_APP_ID=ca-app-pub-xxx
ADMOB_BANNER_ID=ca-app-pub-xxx/xxx
```

### 12. 에러 처리

| 상황 | 처리 |
|---|---|
| 페이지 로딩 실패 | 재시도 1회 → 로그에 error 기록 |
| 파싱 실패 | 로그에 error 기록 |
| DB 저장 실패 | 로그에 error 기록 |
| 앱 데이터 로딩 실패 | "데이터를 불러올 수 없습니다" 표시 |

---

## 개발 순서

1. **Supabase 설정** - 테이블 생성, API 키 발급
2. **크롤러 수정** - 라일락만 파싱, Supabase 연동
3. **GitHub Actions 설정** - 스케줄 + Secrets
4. **안드로이드 앱 개발** - Supabase 연동 → 스와이프 UI → AdMob 연동
