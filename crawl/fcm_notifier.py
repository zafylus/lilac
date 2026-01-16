"""
FCM(Firebase Cloud Messaging) 알림 전송 모듈
크롤링 완료 시 안드로이드 앱으로 푸시 알림 전송
"""
import json
import os
from typing import Optional, Dict, Any
import firebase_admin
from firebase_admin import credentials, messaging


class FCMNotifier:
    """FCM 푸시 알림 전송 클래스"""
    
    def __init__(self, service_account_key_path: Optional[str] = None):
        """
        FCM 초기화
        
        Args:
            service_account_key_path: Firebase Admin SDK JSON 키 파일 경로
                                     None이면 환경변수에서 JSON 문자열 로드
        """
        self.initialized = False
        
        try:
            # Firebase Admin SDK 초기화 (중복 초기화 방지)
            if not firebase_admin._apps:
                if service_account_key_path and os.path.exists(service_account_key_path):
                    # 파일 경로에서 로드
                    cred = credentials.Certificate(service_account_key_path)
                    firebase_admin.initialize_app(cred)
                    print(f"✅ Firebase Admin SDK 초기화 완료 (파일: {service_account_key_path})")
                else:
                    # 환경변수에서 JSON 문자열 로드
                    firebase_key_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")
                    if not firebase_key_json:
                        raise ValueError("FIREBASE_SERVICE_ACCOUNT_KEY 환경변수가 설정되지 않았습니다.")
                    
                    # JSON 문자열을 딕셔너리로 파싱
                    service_account_info = json.loads(firebase_key_json)
                    cred = credentials.Certificate(service_account_info)
                    firebase_admin.initialize_app(cred)
                    print("✅ Firebase Admin SDK 초기화 완료 (환경변수)")
                
                self.initialized = True
            else:
                print("ℹ️  Firebase Admin SDK 이미 초기화됨")
                self.initialized = True
                
        except Exception as e:
            print(f"❌ Firebase Admin SDK 초기화 실패: {e}")
            self.initialized = False
    
    
    def send_topic_notification(
        self,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        특정 토픽을 구독한 모든 기기에 알림 전송
        
        Args:
            topic: FCM 토픽 이름 (예: 'menu_updates')
            title: 알림 제목
            body: 알림 내용
            data: 추가 데이터 (선택)
        
        Returns:
            성공 여부
        """
        if not self.initialized:
            print("❌ FCM이 초기화되지 않았습니다.")
            return False
        
        try:
            # 메시지 구성
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                topic=topic,
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        icon='ic_notification',
                        color='#7C4DFF',  # 라일락 색상
                        sound='default',
                    ),
                ),
            )
            
            # 전송
            response = messaging.send(message)
            print(f"✅ FCM 알림 전송 성공 (토픽: {topic})")
            print(f"   응답: {response}")
            return True
            
        except Exception as e:
            print(f"❌ FCM 알림 전송 실패: {e}")
            return False
    
    
    def send_new_menu_notification(
        self,
        post_no: str,
        post_date: str,
        menu_count: int
    ) -> bool:
        """
        새 식단 업로드 알림 전송 (편의 메서드)
        
        Args:
            post_no: 게시물 번호
            post_date: 게시 날짜
            menu_count: 메뉴 개수
        
        Returns:
            성공 여부
        """
        title = "🍽️ 새로운 식단이 업데이트되었습니다!"
        body = f"{post_date} 주간 식단 ({menu_count}개)"
        
        data = {
            "type": "new_menu",
            "post_no": post_no,
            "post_date": post_date,
            "menu_count": str(menu_count),
        }
        
        return self.send_topic_notification(
            topic="menu_updates",
            title=title,
            body=body,
            data=data
        )


# 전역 인스턴스 (싱글톤 패턴)
_fcm_notifier: Optional[FCMNotifier] = None


def get_fcm_notifier(service_account_key_path: Optional[str] = None) -> FCMNotifier:
    """
    FCMNotifier 싱글톤 인스턴스 반환
    
    Args:
        service_account_key_path: Firebase Admin SDK JSON 키 파일 경로
    
    Returns:
        FCMNotifier 인스턴스
    """
    global _fcm_notifier
    if _fcm_notifier is None:
        _fcm_notifier = FCMNotifier(service_account_key_path)
    return _fcm_notifier


if __name__ == "__main__":
    # 테스트 코드
    print("FCM 알림 테스트")
    
    # 로컬 테스트용 (Downloads 폴더의 키 파일 사용)
    key_path = "/Users/zafylus/Downloads/lilac-e7933-firebase-adminsdk-fbsvc-3721430dcb.json"
    
    notifier = FCMNotifier(service_account_key_path=key_path)
    
    if notifier.initialized:
        # 테스트 알림 전송
        success = notifier.send_new_menu_notification(
            post_no="TEST_001",
            post_date="2026-01-20",
            menu_count=5
        )
        
        if success:
            print("✅ 테스트 알림 전송 성공!")
        else:
            print("❌ 테스트 알림 전송 실패")
    else:
        print("❌ FCM 초기화 실패")
