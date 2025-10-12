"""
ModelExecutionService

모델 실행 유스케이스 서비스
"""

from typing import Optional

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

from ...domain.ai_model.entities.model_request import ModelRequest
from ...domain.ai_model.ports.model_port import ModelPort
from ...domain.ai_model.ports.template_port import TemplatePort
from ...domain.ai_model.value_objects.message import Message

from ..dto.model_request_dto import ModelRequestDTO
from ..dto.model_response_dto import ModelResponseDTO


class ModelExecutionService:
    """
    모델 실행 유스케이스 서비스

    단일책임: 모델 실행 파이프라인 오케스트레이션
    """

    def __init__(
        self,
        model_port: ModelPort,
        template_port: TemplatePort
    ):
        """
        서비스 초기화

        Args:
            model_port: 모델 실행 포트 구현
            template_port: 템플릿 렌더링 포트 구현
        """
        self._model_port = model_port
        self._template_port = template_port

    def execute_with_template(
        self,
        request_dto: ModelRequestDTO
    ) -> Result[ModelResponseDTO, str]:
        """
        템플릿을 사용하여 모델을 실행합니다.

        처리 순서:
        1. DTO → Domain Entity 변환
        2. 템플릿 렌더링
        3. 렌더링된 텍스트를 메시지로 추가
        4. 모델 실행
        5. Domain Entity → DTO 변환
        """
        # 1. DTO → Domain 변환
        domain_result = request_dto.to_domain()
        if not domain_result.is_success():
            return Failure(domain_result.unwrap_error())

        request = domain_result.unwrap()

        # 2. 템플릿 검증
        if not request.has_template():
            return Failure("템플릿 이름이 제공되지 않았습니다")

        # 3. 템플릿 렌더링
        rendered_result = self._template_port.render(
            template_name=request.template_name,
            context=request.template_context
        )

        if not rendered_result.is_success():
            return Failure(
                f"템플릿 렌더링 실패: {rendered_result.unwrap_error()}"
            )

        rendered_text = rendered_result.unwrap()

        # 4. 렌더링된 텍스트를 user 메시지로 추가
        user_message = Message.user(rendered_text)
        updated_request = ModelRequest.create(
            model_type=request.model_type,
            messages=[*request.messages, user_message],
            config=request.config
        )

        if not updated_request.is_success():
            return Failure(updated_request.unwrap_error())

        # 5. 모델 실행
        response_result = self._model_port.execute(updated_request.unwrap())

        if not response_result.is_success():
            return Failure(
                f"모델 실행 실패: {response_result.unwrap_error()}"
            )

        # 6. Domain → DTO 변환
        response = response_result.unwrap()
        return Success(ModelResponseDTO.from_domain(response))

    def execute_direct(
        self,
        request_dto: ModelRequestDTO
    ) -> Result[ModelResponseDTO, str]:
        """
        템플릿 없이 직접 모델을 실행합니다.

        처리 순서:
        1. DTO → Domain Entity 변환
        2. 모델 실행
        3. Domain Entity → DTO 변환
        """
        # 1. DTO → Domain 변환
        domain_result = request_dto.to_domain()
        if not domain_result.is_success():
            return Failure(domain_result.unwrap_error())

        request = domain_result.unwrap()

        # 2. 모델 실행
        response_result = self._model_port.execute(request)

        if not response_result.is_success():
            return Failure(
                f"모델 실행 실패: {response_result.unwrap_error()}"
            )

        # 3. Domain → DTO 변환
        response = response_result.unwrap()
        return Success(ModelResponseDTO.from_domain(response))

    def execute(
        self,
        request_dto: ModelRequestDTO
    ) -> Result[ModelResponseDTO, str]:
        """
        모델을 실행합니다. (템플릿 사용 여부 자동 판단)

        Args:
            request_dto: 모델 요청 DTO

        Returns:
            Result[ModelResponseDTO, str]: 성공 시 응답 DTO, 실패 시 에러 메시지
        """
        # 템플릿 사용 여부에 따라 적절한 메서드 호출
        if request_dto.template_name:
            return self.execute_with_template(request_dto)
        else:
            return self.execute_direct(request_dto)
