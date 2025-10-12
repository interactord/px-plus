"""
BaseOpenAIAdapter

OpenAI API 공통 기능 제공 추상 클래스
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

from ...domain.ai_model.entities.model_request import ModelRequest
from ...domain.ai_model.entities.model_response import ModelResponse
from ...domain.ai_model.ports.model_port import ModelPort


class BaseOpenAIAdapter(ABC, ModelPort):
    """OpenAI API 공통 기능 제공 추상 클래스"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 60
    ):
        """어댑터 초기화"""
        if not api_key or not api_key.strip():
            raise ValueError("API 키가 필요합니다")

        self._api_key = api_key.strip()
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._http_client = self._create_http_client()

    def _create_http_client(self) -> httpx.Client:
        """HTTP 클라이언트 생성"""
        return httpx.Client(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json"
            },
            timeout=self._timeout
        )

    @abstractmethod
    def execute(self, request: ModelRequest) -> Result[ModelResponse, str]:
        """모델 실행 (하위 클래스에서 구현)"""
        pass

    @abstractmethod
    def _build_payload(self, request: ModelRequest) -> Dict[str, Any]:
        """API 요청 페이로드 구성 (하위 클래스에서 구현)"""
        pass

    def _make_request(
        self,
        endpoint: str,
        payload: Dict[str, Any]
    ) -> Result[Dict[str, Any], str]:
        """REST API 요청 실행"""
        try:
            response = self._http_client.post(endpoint, json=payload)
            response.raise_for_status()
            return Success(response.json())
        except httpx.HTTPStatusError as e:
            error_detail = self._extract_error_detail(e.response)
            return Failure(f"HTTP {e.response.status_code} 에러: {error_detail}")
        except httpx.TimeoutException:
            return Failure(f"요청 타임아웃 ({self._timeout}초 초과)")
        except httpx.RequestError as e:
            return Failure(f"네트워크 에러: {str(e)}")
        except Exception as e:
            return Failure(f"예기치 않은 에러: {str(e)}")

    @staticmethod
    def _extract_error_detail(response: httpx.Response) -> str:
        """에러 응답에서 상세 메시지 추출"""
        try:
            error_data = response.json()
            if "error" in error_data:
                error_info = error_data["error"]
                if isinstance(error_info, dict):
                    return error_info.get("message", str(error_info))
                return str(error_info)
            return response.text
        except Exception:
            return response.text

    def _parse_response(
        self,
        response_data: Dict[str, Any]
    ) -> Result[ModelResponse, str]:
        """API 응답을 ModelResponse로 파싱"""
        try:
            choices = response_data.get("choices", [])
            if not choices:
                return Failure("응답에 choices가 없습니다")

            first_choice = choices[0]
            message = first_choice.get("message", {})
            content = message.get("content", "")

            if not content:
                return Failure("응답 내용이 비어있습니다")

            usage = response_data.get("usage", {})
            model = response_data.get("model", "unknown")
            finish_reason = first_choice.get("finish_reason", "unknown")

            metadata = {
                "id": response_data.get("id"),
                "created": response_data.get("created"),
                "system_fingerprint": response_data.get("system_fingerprint")
            }

            return ModelResponse.create(
                content=content,
                model=model,
                usage=usage,
                finish_reason=finish_reason,
                metadata=metadata
            )

        except KeyError as e:
            return Failure(f"응답 파싱 실패 (필수 키 누락): {str(e)}")
        except Exception as e:
            return Failure(f"응답 파싱 실패: {str(e)}")

    def __del__(self):
        """소멸자: HTTP 클라이언트 정리"""
        if hasattr(self, "_http_client"):
            self._http_client.close()
