"""
GPT4oWebEnhancementAdapter

GPT-4o + 웹서치 기반 웹 강화 어댑터
"""

import json
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

from ....domain.web_enhancement.entities.enhanced_term import EnhancedTerm
from ....domain.web_enhancement.value_objects.term_info import TermInfo
from ....domain.web_enhancement.ports.web_enhancement_port import WebEnhancementPort
from ....domain.ai_model.entities.model_request import ModelRequest
from ....domain.ai_model.entities.model_config import ModelConfig
from ....domain.ai_model.value_objects.template_context import TemplateContext
from ....domain.ai_model.value_objects.model_type import ModelType
from ....domain.ai_model.value_objects.message import Message
from ...ai_model.adapters.jinja2_template_adapter import Jinja2TemplateAdapter
from ...ai_model.adapters.openai_chat_adapter import OpenAIChatAdapter


class GPT4oWebEnhancementAdapter(WebEnhancementPort):
    """
    GPT-4o + 웹서치 기반 웹 강화 어댑터
    
    특징:
    - GPT-4o 모델 사용 (자동 웹서치 지원)
    - Single-shot 프롬프트로 웹검색 + 10개 언어 번역
    - Jinja2 템플릿 기반 프롬프트 생성
    
    Attributes:
        openai_adapter: OpenAI Chat 어댑터
        template_adapter: Jinja2 템플릿 어댑터
    """
    
    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-4o",
        template_dir: str = None,
        temperature: float = 0.3,
        max_tokens: int = 4000
    ):
        """
        GPT-4o 웹 강화 어댑터 초기화

        Args:
            api_key: OpenAI API 키
            model_name: 모델명 (기본: gpt-4o)
            template_dir: 템플릿 디렉토리 경로 (None이면 기본 경로)
            temperature: 온도 (0.0-1.0, 낮을수록 일관성)
            max_tokens: 최대 토큰 수
        """
        self._openai_adapter = OpenAIChatAdapter(
            api_key=api_key,
            model_name=model_name
        )

        # 템플릿 디렉토리 설정
        if template_dir is None:
            template_dir = str(Path(__file__).parent.parent / "templates")

        self._template_adapter = Jinja2TemplateAdapter(template_dir=template_dir)
        self._template_name = "enhance_terms_with_web.j2"
        self._temperature = temperature
        self._max_tokens = max_tokens
    
    def enhance_terms(
        self,
        term_infos: List[TermInfo],
        target_languages: List[str]
    ) -> Result[List[EnhancedTerm], str]:
        """
        GPT-4o로 용어 웹 강화
        
        Single-shot 프롬프트:
        1. 웹 검색으로 공식 번역 확인
        2. 10개 언어 동시 번역
        3. 웹 출처 URL 수집
        
        Args:
            term_infos: 강화할 용어 정보 (최대 5개 권장)
            target_languages: 번역 대상 언어
        
        Returns:
            Result[List[EnhancedTerm], str]: 강화된 용어 리스트 또는 에러
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
        
        # 3. GPT-4o 호출
        response_result = self._openai_adapter.execute(request.unwrap())
        
        if not response_result.is_success():
            return Failure(f"GPT-4o 호출 실패: {response_result.unwrap_error()}")
        
        response = response_result.unwrap()
        
        # 4. JSON 응답 파싱
        parse_result = self._parse_response(response.content, term_infos)
        
        return parse_result
    
    def _parse_response(
        self,
        content: str,
        term_infos: List[TermInfo]
    ) -> Result[List[EnhancedTerm], str]:
        """
        GPT-4o 응답 파싱
        
        JSON 응답을 EnhancedTerm 리스트로 변환
        
        Args:
            content: LLM 응답 내용
            term_infos: 원본 용어 정보
        
        Returns:
            Result[List[EnhancedTerm], str]: 파싱된 엔티티 또는 에러
        """
        try:
            # JSON 추출 (코드 블록 제거)
            json_content = content.strip()
            if json_content.startswith("```json"):
                json_content = json_content[7:]
            if json_content.startswith("```"):
                json_content = json_content[3:]
            if json_content.endswith("```"):
                json_content = json_content[:-3]
            
            json_content = json_content.strip()
            
            # JSON 파싱
            data = json.loads(json_content)
            
            if "enhanced_terms" not in data:
                return Failure("응답에 'enhanced_terms' 키가 없습니다")
            
            enhanced_terms_data = data["enhanced_terms"]
            
            # EnhancedTerm 엔티티 생성
            enhanced_terms = []
            
            for idx, term_data in enumerate(enhanced_terms_data):
                # 원본 용어 정보 매칭
                if idx >= len(term_infos):
                    return Failure(f"응답 용어 수({len(enhanced_terms_data)})가 입력({len(term_infos)})보다 많습니다")
                
                term_info = term_infos[idx]
                
                # 필수 필드 검증
                if "original_term" not in term_data:
                    return Failure(f"용어 {idx+1}: 'original_term' 필드 누락")
                
                if "translations" not in term_data:
                    return Failure(f"용어 {idx+1}: 'translations' 필드 누락")
                
                # EnhancedTerm 생성
                term_result = EnhancedTerm.create(
                    original_term=term_data["original_term"],
                    term_type=term_info.type,
                    primary_domain=term_info.primary_domain,
                    context=term_info.context,
                    tags=term_info.tags,
                    translations=term_data.get("translations", {}),
                    web_sources=term_data.get("web_sources", []),
                    source="gpt4o_web",
                    confidence_score=term_data.get("confidence_score", 0.8)
                )
                
                if not term_result.is_success():
                    return Failure(
                        f"용어 {idx+1} 생성 실패: {term_result.unwrap_error()}"
                    )
                
                enhanced_terms.append(term_result.unwrap())
            
            # 개수 검증
            if len(enhanced_terms) != len(term_infos):
                return Failure(
                    f"응답 용어 수({len(enhanced_terms)})와 입력({len(term_infos)})이 일치하지 않습니다"
                )
            
            return Success(enhanced_terms)
            
        except json.JSONDecodeError as e:
            return Failure(f"JSON 파싱 실패: {str(e)}\n응답: {content[:200]}")
        except Exception as e:
            return Failure(f"응답 처리 실패: {str(e)}")
    
    def get_source_name(self) -> str:
        """소스 이름 반환"""
        return "gpt4o_web"
