"""
BaseGeminiAdapter

Google Gemini API 공통 기능 제공 추상 클래스
OpenAI BaseAdapter와 동일한 패턴 적용
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import httpx

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

from ....domain.ai_model.entities.model_request import ModelRequest
from ....domain.ai_model.entities.model_response import ModelResponse
from ....domain.ai_model.ports.model_port import ModelPort


class BaseGeminiAdapter(ModelPort, ABC):
    """
    Google Gemini API 공통 기능 제공 추상 클래스

    OpenAI BaseAdapter와 동일한 구조:
    - HTTP 클라이언트 관리
    - API 요청/응답 처리
    - 에러 핸들링
    - 하위 클래스에서 execute, _build_payload 구현
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://generativelanguage.googleapis.com",
        timeout: int = 60
    ):
        """
        어댑터 초기화

        Args:
            api_key: Google API 키
            base_url: Gemini API 기본 URL
            timeout: 요청 타임아웃 (초)

        Raises:
            ValueError: API 키가 비어있는 경우
        """
        if not api_key or not api_key.strip():
            raise ValueError("Google API 키가 필요합니다")

        self._api_key = api_key.strip()
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._http_client = self._create_http_client()

    def _create_http_client(self) -> httpx.Client:
        """
        HTTP 클라이언트 생성

        Gemini는 API 키를 쿼리 파라미터로 전달

        Returns:
            httpx.Client: 구성된 HTTP 클라이언트
        """
        return httpx.Client(
            base_url=self._base_url,
            headers={
                "Content-Type": "application/json"
            },
            params={
                "key": self._api_key  # Gemini는 쿼리 파라미터로 API 키 전달
            },
            timeout=self._timeout
        )

    @abstractmethod
    def execute(self, request: ModelRequest) -> Result[ModelResponse, str]:
        """
        모델 실행 (하위 클래스에서 구현)

        Args:
            request: 모델 요청

        Returns:
            Result[ModelResponse, str]: 성공 시 응답, 실패 시 에러 메시지
        """
        pass

    @abstractmethod
    def _build_payload(self, request: ModelRequest) -> Dict[str, Any]:
        """
        API 요청 페이로드 구성 (하위 클래스에서 구현)

        Args:
            request: 모델 요청

        Returns:
            Dict[str, Any]: Gemini API 페이로드
        """
        pass

    def _make_request(
        self,
        endpoint: str,
        payload: Dict[str, Any]
    ) -> Result[Dict[str, Any], str]:
        """
        Gemini API 호출 (공통 로직)

        Args:
            endpoint: API 엔드포인트 (예: "/v1beta/models/gemini-2.0-flash-exp:generateContent")
            payload: 요청 페이로드

        Returns:
            Result[Dict[str, Any], str]: 성공 시 응답 JSON, 실패 시 에러 메시지
        """
        try:
            response = self._http_client.post(endpoint, json=payload)
            response.raise_for_status()
            return Success(response.json())

        except httpx.HTTPStatusError as e:
            error_detail = self._parse_error_response(e.response)
            return Failure(
                f"Gemini API 오류 (status {e.response.status_code}): {error_detail}"
            )

        except httpx.TimeoutException:
            return Failure(f"Gemini API 타임아웃 ({self._timeout}초 초과)")

        except httpx.RequestError as e:
            return Failure(f"Gemini API 요청 실패: {str(e)}")

        except Exception as e:
            return Failure(f"예상치 못한 오류: {str(e)}")

    def _parse_error_response(self, response: httpx.Response) -> str:
        """
        Gemini API 에러 응답 파싱

        Args:
            response: HTTP 응답

        Returns:
            str: 에러 메시지
        """
        try:
            error_data = response.json()

            # Gemini 에러 형식: {"error": {"code": 400, "message": "...", "status": "INVALID_ARGUMENT"}}
            if "error" in error_data:
                error_obj = error_data["error"]
                message = error_obj.get("message", "알 수 없는 오류")
                status = error_obj.get("status", "")

                if status:
                    return f"{status}: {message}"
                return message

            return str(error_data)

        except Exception:
            return response.text[:200]  # 파싱 실패 시 본문 일부 반환

    def _parse_response(self, response_data: Dict[str, Any]) -> Result[ModelResponse, str]:
        """
        Gemini API 응답을 ModelResponse로 변환

        Gemini 응답 형식:
        {
          "candidates": [{
            "content": {
              "parts": [{"text": "..."}],
              "role": "model"
            },
            "finishReason": "STOP"
          }],
          "usageMetadata": {
            "promptTokenCount": 10,
            "candidatesTokenCount": 50,
            "totalTokenCount": 60
          }
        }

        Args:
            response_data: Gemini API 응답 JSON

        Returns:
            Result[ModelResponse, str]: 파싱된 ModelResponse 또는 에러
        """
        try:
            candidates = response_data.get("candidates", [])

            if not candidates:
                return Failure("Gemini 응답에 candidates가 없습니다")

            # 첫 번째 candidate 사용
            candidate = candidates[0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])

            if not parts:
                return Failure("Gemini 응답에 content parts가 없습니다")

            # 모든 text parts 결합
            text_content = "".join(
                part.get("text", "") for part in parts if "text" in part
            )

            # Usage 정보 추출
            usage_metadata = response_data.get("usageMetadata", {})
            prompt_tokens = usage_metadata.get("promptTokenCount", 0)
            completion_tokens = usage_metadata.get("candidatesTokenCount", 0)
            total_tokens = usage_metadata.get("totalTokenCount", 0)

            # ModelResponse 생성
            model_response = ModelResponse.create(
                content=text_content,
                model="gemini",
                usage={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens
                },
                finish_reason=candidate.get("finishReason", "STOP")
            )

            if model_response.is_success():
                return Success(model_response.value)
            else:
                return Failure(f"ModelResponse 생성 실패: {model_response.error}")

        except Exception as e:
            return Failure(f"Gemini 응답 파싱 실패: {str(e)}")

    def __del__(self):
        """HTTP 클라이언트 정리"""
        if hasattr(self, '_http_client'):
            self._http_client.close()
