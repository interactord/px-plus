"""
Message Value Object

대화 메시지 값 객체
"""

from dataclasses import dataclass
from typing import Literal

try:
    from rfs.core.result import Result, Success, Failure
except ImportError:
    # 폴백: 기본 Result 구현
    from dataclasses import dataclass as _dataclass
    from typing import Generic, TypeVar, Union

    T = TypeVar("T")
    E = TypeVar("E")

    @_dataclass
    class Success(Generic[T]):
        """성공 결과"""
        value: T

        def is_success(self) -> bool:
            return True

        def unwrap(self) -> T:
            return self.value

    @_dataclass
    class Failure(Generic[E]):
        """실패 결과"""
        error: E

        def is_success(self) -> bool:
            return False

        def unwrap_error(self) -> E:
            return self.error

    Result = Union[Success[T], Failure[E]]


# 메시지 role 타입
MessageRole = Literal["system", "user", "assistant", "developer"]


@dataclass(frozen=True)
class Message:
    """
    대화 메시지 값 객체 (불변)

    Attributes:
        role: 메시지 역할 (system, user, assistant, developer)
        content: 메시지 내용
    """

    role: MessageRole
    content: str

    @classmethod
    def create(cls, role: str, content: str) -> Result["Message", str]:
        """
        Message 생성 (검증 포함)

        Args:
            role: 메시지 역할
            content: 메시지 내용

        Returns:
            Result[Message, str]: 성공 시 Message 객체, 실패 시 에러 메시지
        """
        # role 검증
        valid_roles = {"system", "user", "assistant", "developer"}
        if role not in valid_roles:
            return Failure(
                f"잘못된 메시지 role: {role}. "
                f"가능한 값: {', '.join(valid_roles)}"
            )

        # content 검증
        if not content or not content.strip():
            return Failure("메시지 내용은 비어있을 수 없습니다")

        return Success(cls(role=role, content=content.strip()))  # type: ignore

    @classmethod
    def system(cls, content: str) -> "Message":
        """시스템 메시지 생성"""
        result = cls.create("system", content)
        if result.is_success():
            return result.unwrap()
        raise ValueError(result.unwrap_error())

    @classmethod
    def user(cls, content: str) -> "Message":
        """사용자 메시지 생성"""
        result = cls.create("user", content)
        if result.is_success():
            return result.unwrap()
        raise ValueError(result.unwrap_error())

    @classmethod
    def assistant(cls, content: str) -> "Message":
        """어시스턴트 메시지 생성"""
        result = cls.create("assistant", content)
        if result.is_success():
            return result.unwrap()
        raise ValueError(result.unwrap_error())

    @classmethod
    def developer(cls, content: str) -> "Message":
        """개발자 메시지 생성"""
        result = cls.create("developer", content)
        if result.is_success():
            return result.unwrap()
        raise ValueError(result.unwrap_error())

    def to_dict(self) -> dict:
        """딕셔너리로 변환 (OpenAI API 포맷)"""
        return {
            "role": self.role,
            "content": self.content
        }
