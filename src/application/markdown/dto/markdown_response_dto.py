"""
마크다운 생성 응답 DTO

API 응답 데이터 구조를 정의합니다.
"""

from pydantic import BaseModel, Field


class MarkdownGenerationResponse(BaseModel):
    """
    마크다운 테이블 생성 응답 DTO

    Attributes:
        markdown_table: 생성된 마크다운 테이블 문자열
        term_count: 용어 개수
        column_count: 컬럼 개수 (term, term_type, tags + 선택된 언어 수)
    """

    markdown_table: str = Field(
        ...,
        description="생성된 마크다운 테이블 문자열",
        examples=["| term | term_type | tags | ko | en |\n|------|----------|------|----|----|"]
    )

    term_count: int = Field(
        ...,
        ge=0,
        description="용어 개수",
        examples=[50]
    )

    column_count: int = Field(
        ...,
        ge=4,  # 최소: term, term_type, tags + 1개 언어
        le=14,  # 최대: term, term_type, tags + 11개 언어
        description="컬럼 개수",
        examples=[5]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "markdown_table": "| term | term_type | tags | ko | en |\n|------|----------|------|----|----|----|\n| Naciones Unidas | company | #ONU #global | 유엔 | United Nations |",
                "term_count": 1,
                "column_count": 5
            }
        }
