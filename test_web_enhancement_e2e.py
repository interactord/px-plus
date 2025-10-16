#!/usr/bin/env python3
"""
웹강화 E2E 테스트 스크립트

SSL 설정 로깅 확인 및 Fallback 체인 동작 검증
"""

import requests
import json
import time
from datetime import datetime

# 테스트 데이터
test_data = {
    "terms": [
        {
            "term": "Partido Popular",
            "type": "organization",
            "primary_domain": "politics",
            "context": "Major Spanish political party",
            "tags": ["#PP", "#Spain", "#politics"]
        },
        {
            "term": "Real Madrid",
            "type": "organization",
            "primary_domain": "sports",
            "context": "Spanish football club",
            "tags": ["#football", "#LaLiga", "#Spain"]
        },
        {
            "term": "Toyota",
            "type": "company",
            "primary_domain": "automotive",
            "context": "Japanese car manufacturer",
            "tags": ["#automotive", "#Japan"]
        }
    ],
    "target_languages": ["ko", "en", "ja"],
    "use_cache": False,
    "batch_size": 3,
    "concurrent_batches": 1
}

def test_web_enhancement():
    """웹강화 E2E 테스트"""

    print("=" * 80)
    print("웹강화 E2E 테스트 시작")
    print("=" * 80)
    print()

    # 1. Health Check
    print("📍 Step 1: Health Check")
    print("-" * 80)
    try:
        health_response = requests.get("http://localhost:8000/api/v1/web-enhancement/health", timeout=10)
        print(f"Status: {health_response.status_code}")
        print(f"Response: {json.dumps(health_response.json(), indent=2, ensure_ascii=False)}")
        print()
    except Exception as e:
        print(f"❌ Health Check 실패: {e}")
        print()

    # 2. 웹강화 API 호출
    print("📍 Step 2: 웹강화 API 호출")
    print("-" * 80)
    print(f"테스트 데이터: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
    print()

    start_time = time.time()

    try:
        response = requests.post(
            "http://localhost:8000/api/v1/web-enhancement/enhance",
            json=test_data,
            timeout=180
        )

        elapsed_time = time.time() - start_time

        print(f"Status Code: {response.status_code}")
        print(f"처리 시간: {elapsed_time:.2f}초")
        print()

        if response.status_code == 200:
            result = response.json()

            print("✅ 웹강화 성공!")
            print("-" * 80)
            print(f"전체 응답: {json.dumps(result, indent=2, ensure_ascii=False)}")
            print()

            # Summary 분석
            if "summary" in result:
                summary = result["summary"]
                print("📊 요약 정보:")
                print(f"  - 총 용어: {summary.get('total_terms', 0)}")
                print(f"  - 성공: {summary.get('success_count', 0)}")
                print(f"  - 실패: {summary.get('failed_count', 0)}")
                print(f"  - 캐시 히트: {summary.get('cache_hits', 0)}")
                print(f"  - Fallback 사용: {summary.get('fallback_count', 0)}")
                print(f"  - 처리 시간: {summary.get('processing_time', 0):.2f}초")
                print()

            # Enhanced Terms 분석
            if "enhanced_terms" in result:
                enhanced = result["enhanced_terms"]
                print(f"🎯 강화된 용어 ({len(enhanced)}개):")
                print("-" * 80)

                for idx, term in enumerate(enhanced, 1):
                    print(f"\n[{idx}] {term.get('term', 'N/A')}")
                    print(f"  타입: {term.get('type', 'N/A')}")
                    print(f"  도메인: {term.get('primary_domain', 'N/A')}")

                    if "translations" in term:
                        translations = term["translations"]
                        print(f"  번역:")
                        for lang, trans in translations.items():
                            print(f"    - {lang}: {trans}")

                    if "metadata" in term:
                        metadata = term["metadata"]
                        print(f"  메타데이터:")
                        print(f"    - 처리 시간: {metadata.get('processing_time', 'N/A')}")
                        print(f"    - Fallback 사용: {metadata.get('fallback_used', 'N/A')}")
                        print(f"    - 캐시 사용: {metadata.get('from_cache', 'N/A')}")

            print()
            print("=" * 80)
            print("✅ 테스트 완료!")
            print("=" * 80)

        else:
            print(f"❌ API 호출 실패: {response.status_code}")
            print(f"응답: {response.text}")

    except requests.exceptions.Timeout:
        print("❌ 타임아웃 발생 (180초 초과)")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_web_enhancement()
