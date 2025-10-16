#!/usr/bin/env python3
"""
Fallback 체인 테스트 스크립트

GPT-4o 실패 시 Gemini Fallback 동작 검증
"""

import os
import sys

# .env 파일에서 원래 OPENAI_API_KEY 백업
original_openai_key = os.getenv("OPENAI_API_KEY")

print("=" * 80)
print("Fallback 체인 테스트")
print("=" * 80)
print()

print("📍 원래 OPENAI_API_KEY 확인:")
if original_openai_key:
    masked_key = original_openai_key[:10] + "..." + original_openai_key[-4:]
    print(f"  {masked_key}")
else:
    print("  ❌ 설정되지 않음")

print()
print("💡 Fallback 체인 테스트 방법:")
print("-" * 80)
print("1. .env 파일에서 OPENAI_API_KEY를 임시로 잘못된 값으로 변경")
print("2. 서버 재시작 (./run.sh dev --force-kill)")
print("3. 웹강화 API 호출")
print("4. 서버 로그에서 Fallback 동작 확인:")
print("   - Primary (GPT-4o) 실패")
print("   - Fallback 1 (Gemini + Web) 성공 확인")
print("   - SSL 설정 로그 확인")
print()
print("예상 로그 패턴:")
print("-" * 80)
print("  🔓 GeminiSDKAdapter: SSL 인증서 검증 비활성화 (model=gemini-2.0-flash-exp, grounding=True)")
print("  ✅ SSL 설정 완료: verify_ssl=False, PYTHONHTTPSVERIFY=0, ssl._create_unverified_context 적용")
print("  ⚠️  Primary 전략 실패: ... (401 Unauthorized 또는 API 키 오류)")
print("  🔄 Fallback 1 (Gemini + Web) 시도 중...")
print("  ✅ Fallback 1 성공!")
print()
print("5. 테스트 완료 후 .env 파일의 OPENAI_API_KEY 복원")
print()
print("=" * 80)
print()

print("현재 Fallback 체인 구조:")
print("-" * 80)
print("1. Primary: GPT-4o + Web Search")
print("2. Fallback 1: Gemini 2.0 Flash + Google Search Grounding (SSL 설정 적용)")
print("3. Fallback 2: Gemini 2.0 Flash (Simple Translation, SSL 설정 적용)")
print("4. Fallback 3: GPT-4o-mini")
print()
print("=" * 80)
