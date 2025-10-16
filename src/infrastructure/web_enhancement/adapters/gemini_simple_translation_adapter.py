"""
GeminiSimpleTranslationAdapter

Gemini 2.0 Flash 기반 일반 번역 어댑터 (웹 검색 없음)
폴백용 - 웹 강화 실패 시 최소한의 번역 제공
"""

import json
import os
from typing import List
from pathlib import Path

try:
    from rfs.core.result import Result, Success, Failure
except ImportError:
    from dataclasses import dataclass
    from typing import Generic, TypeVar, Union
    T, E = TypeVar("T"), TypeVar("E")

    @dataclass
    class Success(Generic[T]):
        value: T
        def is_success(self) -> bool: return True
        def unwrap(self) -> T: return self.value

    @dataclass
    class Failure(Generic[E]):
        error: E
        def is_success(self) -> bool: return False
        def unwrap_error(self) -> E: return self.error

    Result = Union[Success[T], Failure[E]]

from ....domain.ai_model.value_objects.template_context import TemplateContext
from ....domain.ai_model.value_objects.model_type import ModelType
from ....domain.ai_model.value_objects.message import Message
from ....domain.ai_model.entities.model_request import ModelRequest
from ....domain.ai_model.entities.model_config import ModelConfig
from ....infrastructure.ai_model.adapters.jinja2_template_adapter import Jinja2TemplateAdapter
from ....infrastructure.ai_model.adapters.gemini_chat_adapter import GeminiChatAdapter
from ....domain.web_enhancement.entities.enhanced_term import EnhancedTerm
from ....domain.web_enhancement.value_objects.term_info import TermInfo
from ....domain.web_enhancement.ports.web_enhancement_port import WebEnhancementPort


class GeminiSimpleTranslationAdapter(WebEnhancementPort):
    """
    Gemini 2.0 Flash 일반 번역 어댑터

    특징:
    - 웹 검색 없이 LLM 지식만 사용
    - 빠른 응답 (웹 검색 오버헤드 없음)
    - 낮은 비용 (Flash 모델)
    - 폴백 전용 (캐시 저장 안 함)

    Attributes:
        gemini_adapter: Gemini 어댑터
        template_adapter: Jinja2 템플릿 어댑터
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.0-flash-exp",
        template_dir: str = None,
        temperature: float = 0.3,
        max_tokens: int = 3000
    ):
        """
        Gemini 일반 번역 어댑터 초기화

        Args:
            api_key: Google API 키
            model_name: 모델명 (기본: gemini-2.0-flash-exp)
            template_dir: 템플릿 디렉토리 경로
            temperature: 온도 (0.0-1.0)
            max_tokens: 최대 토큰 수
        """
        self._gemini_adapter = GeminiChatAdapter(
            api_key=api_key,
            model_name=model_name
        )

        if template_dir is None:
            template_dir = str(Path(__file__).parent.parent / "templates")

        self._template_adapter = Jinja2TemplateAdapter(template_dir=template_dir)
        self._template_name = "translate_terms_simple.j2"
        self._temperature = temperature
        self._max_tokens = max_tokens

    def enhance_terms(
        self,
        term_infos: List[TermInfo],
        target_languages: List[str]
    ) -> Result[List[EnhancedTerm], str]:
        """
        일반 번역 수행 (웹 검색 없음)

        Args:
            term_infos: 번역할 용어 정보 (최대 5개 권장)
            target_languages: 번역 대상 언어

        Returns:
            Result[List[EnhancedTerm], str]: 번역된 용어 또는 에러
        """
        # 1. 프롬프트 생성
        context = TemplateContext(
            variables={"term_infos": [info.to_dict() for info in term_infos]}
        )
        prompt_result = self._template_adapter.render(
            template_name=self._template_name,
            context=context
        )

        if not prompt_result.is_success():
            return Failure(f"프롬프트 생성 실패: {prompt_result.unwrap_error()}")

        prompt = prompt_result.unwrap()

        # 2. ModelRequest 생성
        message_result = Message.create(role="user", content=prompt)
        if not message_result.is_success():
            return Failure(f"메시지 생성 실패: {message_result.unwrap_error()}")

        request = ModelRequest.create(
            model_type=ModelType.CHAT,
            messages=[message_result.unwrap()],
            config=ModelConfig(
                temperature=self._temperature,
                max_tokens=self._max_tokens
            )
        )

        if not request.is_success():
            return Failure(f"요청 생성 실패: {request.unwrap_error()}")

        # 3. Gemini 호출 (웹 검색 없음)
        response_result = self._gemini_adapter.execute(request.unwrap())

        if not response_result.is_success():
            return Failure(f"Gemini 호출 실패: {response_result.unwrap_error()}")

        response = response_result.unwrap()

        # 4. JSON 파싱
        try:
            response_text = response.content.strip()

            # JSON 코드 블록 제거
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            response_text = response_text.strip()
            data = json.loads(response_text)

            if "enhanced_terms" not in data:
                return Failure("응답에 'enhanced_terms' 필드가 없습니다")

            enhanced_terms = []
            for term_data in data["enhanced_terms"]:
                # source 필드 추가
                term_data["source"] = "gemini_simple"
                term = EnhancedTerm.from_dict(term_data)
                enhanced_terms.append(term)

            return Success(enhanced_terms)

        except json.JSONDecodeError as e:
            return Failure(f"JSON 파싱 실패: {str(e)}\n응답: {response_text[:200]}")
        except Exception as e:
            return Failure(f"응답 처리 실패: {str(e)}")

    def get_source_name(self) -> str:
        """어댑터 소스 이름"""
        return "gemini_simple"
