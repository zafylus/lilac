"""
메인 실행 스크립트: 크롤링 → Supabase 업로드 → FCM 알림
"""
import sys
from crawler import crawl_menus
from supabase_client import (
    get_client,
    get_last_state,
    update_state,
    upsert_menus,
    log_crawl
)
from utils import transform_to_supabase_format
from fcm_notifier import get_fcm_notifier


def main(headless: bool = True, force: bool = False):
    """
    메인 실행 함수

    Args:
        headless: 브라우저 headless 모드 (기본: True)
        force: 강제 실행 (상태 비교 없이 크롤링)
    """
    print("=" * 60)
    print("부경대 식단 크롤러 시작")
    print("=" * 60)

    # 1. Supabase 클라이언트 생성
    try:
        client = get_client()
        print("✅ Supabase 연결 성공")
    except ValueError as e:
        print(f"❌ Supabase 연결 실패: {e}")
        return

    # 2. 마지막 크롤링 상태 조회
    last_state = get_last_state(client)
    if last_state:
        print(f"📋 마지막 크롤링: post_no={last_state['last_post_no']}, post_date={last_state['last_post_date']}")
    else:
        print("📋 이전 크롤링 기록 없음 (첫 실행)")

    # 3. 크롤링 실행
    try:
        menus_data, post_no, post_date = crawl_menus(headless=headless)
        print(f"\n📥 크롤링 완료: {len(menus_data)}개 메뉴")
    except Exception as e:
        print(f"❌ 크롤링 실패: {e}")
        log_crawl(client, "error", str(e))
        return

    # 4. 새 게시물인지 확인
    if not force and last_state:
        if post_no == last_state['last_post_no'] and post_date == last_state['last_post_date']:
            print("\n⏭️  새 게시물 없음 - 스킵")
            log_crawl(client, "skipped", "No new post", post_no, post_date)
            return

    # 5. 데이터 변환 (Supabase 스키마에 맞게)
    try:
        supabase_data = transform_to_supabase_format(menus_data, post_date)
        print(f"\n🔄 데이터 변환 완료: {len(supabase_data)}개")
    except Exception as e:
        print(f"❌ 데이터 변환 실패: {e}")
        log_crawl(client, "error", f"Transform failed: {e}", post_no, post_date)
        return

    # 6. Supabase에 업로드
    try:
        upsert_menus(client, supabase_data)
        print("✅ Supabase 업로드 성공")
    except Exception as e:
        print(f"❌ Supabase 업로드 실패: {e}")
        log_crawl(client, "error", f"Upload failed: {e}", post_no, post_date)
        return

    # 7. 상태 업데이트
    update_state(client, post_no, post_date)
    print("✅ 상태 업데이트 완료")

    # 8. 성공 로그 기록
    log_crawl(client, "success", f"Uploaded {len(supabase_data)} menus", post_no, post_date, new_data=True)

    # 9. FCM 푸시 알림 전송
    try:
        print("\n📲 FCM 알림 전송 중...")
        fcm_notifier = get_fcm_notifier()
        
        if fcm_notifier.initialized:
            success = fcm_notifier.send_new_menu_notification(
                post_no=post_no,
                post_date=post_date,
                menu_count=len(supabase_data)
            )
            
            if success:
                print("✅ FCM 알림 전송 성공")
            else:
                print("⚠️  FCM 알림 전송 실패 (크롤링은 정상 완료)")
        else:
            print("⚠️  FCM 초기화 실패 - 알림 전송 스킵")
    except Exception as e:
        # FCM 알림 실패는 치명적이지 않으므로 로그만 남기고 계속 진행
        print(f"⚠️  FCM 알림 전송 중 오류 발생: {e}")

    print("\n" + "=" * 60)
    print("✅ 크롤링 완료!")
    print("=" * 60)


if __name__ == "__main__":
    # 명령줄 인자 처리
    headless = "--no-headless" not in sys.argv
    force = "--force" in sys.argv

    if not headless:
        print("🖥️  브라우저 표시 모드")
    if force:
        print("⚡ 강제 실행 모드")

    main(headless=headless, force=force)
