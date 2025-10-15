"""
마크다운 생성 요청 DTO

API 요청 데이터를 검증하고 변환합니다.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Any


class MarkdownGenerationRequest(BaseModel):
    """
    마크다운 테이블 생성 요청 DTO

    Attributes:
        terms_data: enhanced_terms 배열을 포함하는 JSON 데이터
        selected_languages: 선택된 언어 코드 리스트 (1-11개)
    """

    terms_data: Dict[str, Any] = Field(
        ...,
        description="용어 데이터 JSON (enhanced_terms 배열 포함)",
        examples=[{
            "enhanced_terms": [
                {
                    "original_term": "Naciones Unidas",
                    "term_type": "company",
                    "tags": ["#ONU", "#global"],
                    "translations": {
                        "ko": "유엔",
                        "en": "United Nations"
                    }
                }
            ]
        }]
    )

    selected_languages: List[str] = Field(
        ...,
        min_length=1,
        max_length=11,
        description="선택된 언어 코드 리스트",
        examples=[["ko", "en", "ja"]]
    )

    @field_validator("terms_data")
    @classmethod
    def validate_terms_data(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """
        terms_data 유효성 검증

        Args:
            v: terms_data 딕셔너리

        Returns:
            검증된 terms_data

        Raises:
            ValueError: enhanced_terms 배열이 없거나 비어있는 경우
        """
        if "enhanced_terms" not in v:
            raise ValueError("terms_data에 enhanced_terms 배열이 없습니다")

        if not isinstance(v["enhanced_terms"], list):
            raise ValueError("enhanced_terms는 배열이어야 합니다")

        if len(v["enhanced_terms"]) == 0:
            raise ValueError("enhanced_terms 배열이 비어있습니다")

        return v

    @field_validator("selected_languages")
    @classmethod
    def validate_languages(cls, v: List[str]) -> List[str]:
        """
        선택된 언어 코드 유효성 검증

        Args:
            v: 언어 코드 리스트

        Returns:
            검증된 언어 코드 리스트

        Raises:
            ValueError: 유효하지 않은 언어 코드 포함 시
        """
        VALID_LANGUAGES = {
            "ko", "en", "zh-CN", "zh-TW", "ja",
            "fr", "ru", "it", "vi", "ar", "es"
        }

        # 중복 제거
        unique_languages = list(dict.fromkeys(v))

        # 유효성 검증
        invalid = set(unique_languages) - VALID_LANGUAGES
        if invalid:
            raise ValueError(
                f"유효하지 않은 언어 코드: {', '.join(invalid)}"
            )

        return unique_languages

    class Config:
        json_schema_extra = {
            "example": {
                "terms_data": {
                    "enhanced_terms": [
                        {
                            "original_term": "Naciones Unidas",
                            "term_type": "company",
                            "tags": ["#ONU", "#global", "#politics"],
                            "translations": {
                                "ko": "유엔",
                                "en": "United Nations",
                                "ja": "国際連合"
                            }
                        }
                    ]
                },
                "selected_languages": ["ko", "en", "ja"]
            }
        }
