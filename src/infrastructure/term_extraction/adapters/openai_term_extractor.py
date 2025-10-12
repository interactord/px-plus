"""
OpenAI 기반 용어 추출 Adapter 모듈

OpenAI GPT-4o를 사용하여 실제 용어 추출을 수행합니다.
기존 ai_model 시스템(ModelExecutionService)을 재사용합니다.
"""

import json
import time
from typing import List, Dict, Any

# RFS Framework - Result 패턴
try:
    from rfs.core.result import Result, Success, Failure
except ImportError:
    from dataclasses import dataclass
    from typing import Generic, TypeVar, Union
    
    T = TypeVar('T')
    E = TypeVar('E')
    
    @dataclass(frozen=True)
    class Success(Generic[T]):
        value: T
        def is_success(self) -> bool: return True
        def is_failure(self) -> bool: return False
    
    @dataclass(frozen=True)
    class Failure(Generic[E]):
        error: E
        def is_success(self) -> bool: return False
        def is_failure(self) -> bool: return True
    
    Result = Union[Success[T], Failure[E]]

# 도메인 객체 import
from ....domain.term_extraction.value_objects.chunk_text import ChunkText
from ....domain.term_extraction.value_objects.extraction_context import ExtractionContext
from ....domain.term_extraction.value_objects.entity_type import EntityType
from ....domain.term_extraction.entities.extracted_entity import ExtractedEntity
from ....domain.term_extraction.entities.extraction_result import ExtractionResult
from ....domain.term_extraction.ports.term_extraction_port import TermExtractionPort

# 기존 ai_model 시스템 import (Domain Layer에 위치)
from ....domain.ai_model.ports.model_port import ModelPort
from ....domain.ai_model.ports.template_port import TemplatePort


class OpenAITermExtractor(TermExtractionPort):
    """
    OpenAI GPT-4o 기반 용어 추출 구현체
    
    기존 ModelExecutionService 패턴을 따라 ModelPort와 TemplatePort를 사용합니다.
    """
    
    def __init__(
        self,
        model_port: ModelPort,
        template_port: TemplatePort
    ):
        """
        Extractor 초기화
        
        Args:
            model_port: AI 모델 실행 포트
            template_port: 템플릿 렌더링 포트
        """
        self._model = model_port
        self._template = template_port
    
    async def extract(
        self,
        chunk: ChunkText,
        context: ExtractionContext = None
    ) -> Result[ExtractionResult, str]:
        """
        단일 청크에서 용어를 추출합니다.
        
        Args:
            chunk: 추출할 청크
            context: 추출 컨텍스트
            
        Returns:
            Result[ExtractionResult, str]: 성공 시 추출 결과, 실패 시 에러 메시지
        """
        if context is None:
            context_result = ExtractionContext.create()
            if context_result.is_failure():
                return Failure(f"기본 컨텍스트 생성 실패: {context_result.error}")
            context = context_result.value
        
        start_time = time.time()
        
        # 1. 프롬프트 렌더링
        prompt_result = await self._render_prompt(chunk, context)
        if prompt_result.is_failure():
            return Failure(f"프롬프트 렌더링 실패: {prompt_result.error}")
        
        prompt = prompt_result.value
        
        # 2. LLM 실행
        llm_result = await self._execute_llm(prompt)
        if llm_result.is_failure():
            return Failure(f"LLM 실행 실패: {llm_result.error}")
        
        llm_response = llm_result.value
        
        # 3. 응답 파싱
        entities_result = self._parse_response(llm_response)
        if entities_result.is_failure():
            return Failure(f"응답 파싱 실패: {entities_result.error}")
        
        entities = entities_result.value
        
        # 4. 필터링 적용
        filtered_entities = self._apply_filters(entities, context)
        
        # 5. 결과 생성
        processing_time = time.time() - start_time
        result = ExtractionResult.success(
            chunk=chunk,
            entities=filtered_entities,
            cached=False,
            processing_time=processing_time
        )
        
        return Success(result)
    
    async def extract_batch(
        self,
        chunks: List[ChunkText],
        context: ExtractionContext = None
    ) -> List[Result[ExtractionResult, str]]:
        """
        여러 청크에서 용어를 추출합니다.
        
        Args:
            chunks: 추출할 청크 목록
            context: 추출 컨텍스트
            
        Returns:
            List[Result[ExtractionResult, str]]: 각 청크의 추출 결과
        """
        results: List[Result[ExtractionResult, str]] = []
        
        for chunk in chunks:
            result = await self.extract(chunk, context)
            results.append(result)
        
        return results
    
    async def _render_prompt(
        self,
        chunk: ChunkText,
        context: ExtractionContext
    ) -> Result[str, str]:
        """
        Jinja2 템플릿을 렌더링하여 프롬프트를 생성합니다.
        
        Args:
            chunk: 청크 데이터
            context: 추출 컨텍스트
            
        Returns:
            Result[str, str]: 성공 시 렌더링된 프롬프트, 실패 시 에러 메시지
        """
        template_vars = {
            "text": chunk.content,
            "filename": chunk.source_filename,
            "chunk_index": chunk.chunk_index,
            "include_context": context.include_context,
        }
        
        # type_filter가 있으면 추가
        if context.type_filter:
            template_vars["allowed_types"] = [
                t.value for t in context.type_filter.allowed_types
            ]
        
        # max_entities가 있으면 추가
        if context.max_entities:
            template_vars["max_entities"] = context.max_entities
        
        try:
            rendered = await self._template.render(
                template_name=context.template_name,
                variables=template_vars
            )
            return Success(rendered)
        except Exception as e:
            return Failure(f"템플릿 렌더링 오류: {str(e)}")
    
    async def _execute_llm(self, prompt: str) -> Result[str, str]:
        """
        LLM을 실행하여 응답을 받습니다.
        
        Args:
            prompt: 실행할 프롬프트
            
        Returns:
            Result[str, str]: 성공 시 LLM 응답, 실패 시 에러 메시지
        """
        try:
            response = await self._model.execute(prompt)
            return Success(response)
        except Exception as e:
            return Failure(f"LLM 실행 오류: {str(e)}")
    
    def _parse_response(self, response: str) -> Result[List[ExtractedEntity], str]:
        """
        LLM 응답을 파싱하여 ExtractedEntity 리스트로 변환합니다.
        
        Args:
            response: LLM 응답 (JSON 문자열)
            
        Returns:
            Result[List[ExtractedEntity], str]: 성공 시 엔티티 리스트, 실패 시 에러 메시지
        """
        try:
            # JSON 파싱
            data = json.loads(response)
            
            if not isinstance(data, dict):
                return Failure("응답이 JSON 객체가 아닙니다")
            
            if "extracted_entities" not in data:
                return Failure("응답에 'extracted_entities' 필드가 없습니다")
            
            entities_data = data["extracted_entities"]
            
            if not isinstance(entities_data, list):
                return Failure("'extracted_entities'가 배열이 아닙니다")
            
            # 각 엔티티 파싱
            entities: List[ExtractedEntity] = []
            
            for idx, entity_data in enumerate(entities_data):
                entity_result = self._parse_entity(entity_data, idx)
                
                if entity_result.is_failure():
                    # 개별 엔티티 파싱 실패는 로그만 하고 계속 진행
                    # (일부 엔티티가 잘못되어도 나머지는 사용 가능)
                    continue
                
                entities.append(entity_result.value)
            
            return Success(entities)
            
        except json.JSONDecodeError as e:
            return Failure(f"JSON 파싱 오류: {str(e)}")
        except Exception as e:
            return Failure(f"응답 파싱 오류: {str(e)}")
    
    def _parse_entity(
        self,
        data: Dict[str, Any],
        index: int
    ) -> Result[ExtractedEntity, str]:
        """
        단일 엔티티 데이터를 ExtractedEntity 객체로 변환합니다.
        
        Args:
            data: 엔티티 JSON 데이터
            index: 엔티티 인덱스 (에러 메시지용)
            
        Returns:
            Result[ExtractedEntity, str]: 성공 시 엔티티, 실패 시 에러 메시지
        """
        try:
            # 필수 필드 확인
            if "term" not in data:
                return Failure(f"엔티티 {index}: 'term' 필드 누락")
            
            if "type" not in data:
                return Failure(f"엔티티 {index}: 'type' 필드 누락")
            
            if "primary_domain" not in data:
                return Failure(f"엔티티 {index}: 'primary_domain' 필드 누락")
            
            # ExtractedEntity 생성
            return ExtractedEntity.create(
                term=data["term"],
                type_value=data["type"],
                primary_domain=data["primary_domain"],
                tags=data.get("tags"),
                context=data.get("context", ""),
                multilingual_expressions=data.get("multilingual_expressions")
            )
            
        except Exception as e:
            return Failure(f"엔티티 {index} 파싱 오류: {str(e)}")
    
    def _apply_filters(
        self,
        entities: List[ExtractedEntity],
        context: ExtractionContext
    ) -> List[ExtractedEntity]:
        """
        컨텍스트에 정의된 필터를 적용합니다.
        
        Args:
            entities: 필터링할 엔티티 목록
            context: 추출 컨텍스트
            
        Returns:
            List[ExtractedEntity]: 필터링된 엔티티 목록
        """
        filtered = entities
        
        # 1. 타입 필터 적용
        if context.type_filter:
            filtered = [
                entity for entity in filtered
                if entity.matches_filter(context.type_filter)
            ]
        
        # 2. 최대 개수 제한
        if context.max_entities and len(filtered) > context.max_entities:
            filtered = filtered[:context.max_entities]
        
        return filtered
