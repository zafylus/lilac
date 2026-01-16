#!/bin/bash

# GitHub Secrets 설정을 위한 Firebase 키 준비 스크립트

echo "🔑 Firebase 서비스 계정 키를 GitHub Secrets에 추가하기 위한 준비"
echo "================================================================"
echo ""

KEY_FILE="/Users/zafylus/Downloads/lilac-e7933-firebase-adminsdk-fbsvc-3721430dcb.json"

if [ ! -f "$KEY_FILE" ]; then
    echo "❌ 키 파일을 찾을 수 없습니다: $KEY_FILE"
    exit 1
fi

echo "✅ 키 파일 발견: $KEY_FILE"
echo ""
echo "📋 다음 내용을 복사하여 GitHub Secrets에 추가하세요:"
echo ""
echo "Secret 이름: FIREBASE_SERVICE_ACCOUNT_KEY"
echo ""
echo "Secret 값 (아래 JSON 전체를 복사):"
echo "================================================================"
cat "$KEY_FILE"
echo ""
echo "================================================================"
echo ""
echo "📝 GitHub Secrets 추가 방법:"
echo "1. GitHub 저장소 페이지로 이동"
echo "2. Settings → Secrets and variables → Actions"
echo "3. 'New repository secret' 클릭"
echo "4. Name: FIREBASE_SERVICE_ACCOUNT_KEY"
echo "5. Value: 위의 JSON 전체 내용을 복사하여 붙여넣기"
echo "6. 'Add secret' 클릭"
echo ""
echo "✅ 완료!"
