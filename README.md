# lilac

부경대학교 라일락 식당 식단 자동 수집 및 조회 서비스

## 개요

학교 홈페이지에서 매번 식단을 확인하는 번거로움을 해결하기 위해, 새로운 식단 게시물을 자동으로 감지하고 수집하여 안드로이드 앱에서 쉽게 조회할 수 있게 합니다.

## 기술 스택

- **크롤러**: Python + Playwright
- **API 서버**: FastAPI
- **데이터베이스**: Supabase
- **스케줄러**: GitHub Actions
- **앱**: Android (Kotlin + Jetpack Compose)

## 실행 방법

```bash
# 가상환경 활성화
source .venv/bin/activate

# API 서버 실행
uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# 크롤러 실행
cd crawl && python table.py
```

## 프로젝트 구조

```
lilac/
├── main.py              # FastAPI 서버
├── crawl/
│   ├── table.py         # 크롤러 (Playwright)
│   ├── sqlite_setup.py  # DB 관리
│   └── pknu_menus.db    # SQLite 데이터베이스
├── model/
│   └── models.py        # Pydantic 모델
└── docs/
    ├── PRD.md           # 제품 요구사항
    └── TRD.md           # 기술 요구사항
```
