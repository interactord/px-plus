"""
Response Converters

Result 패턴의 결과를 HTTP 응답으로 변환하는 유틸리티
"""

from typing import Any

from fastapi import status
from fastapi.responses import JSONResponse

# RFS Framework Result 패턴
try:
    from rfs.core.result import Result
except ImportError:
    from typing import Union

    Result = Union


def result_to_response(
    result: Result,
    success_status: int = status.HTTP_200_OK,
    error_status: int = status.HTTP_400_BAD_REQUEST,
) -> JSONResponse:
    """
    Result를 JSONResponse로 변환

    Args:
        result: 변환할 Result 객체
        success_status: 성공 시 HTTP 상태 코드
        error_status: 실패 시 HTTP 상태 코드

    Returns:
        JSONResponse: HTTP 응답

    Examples:
        >>> success_result = Success({"message": "Hello"})
        >>> response = result_to_response(success_result)
        >>> # JSONResponse(status_code=200, content={"message": "Hello"})

        >>> failure_result = Failure("에러 발생")
        >>> response = result_to_response(failure_result)
        >>> # JSONResponse(status_code=400, content={"error": "에러 발생"})
    """
    if result.is_success():
        content = result.unwrap()
        # dict가 아니면 {"data": content}로 래핑
        if not isinstance(content, dict):
            content = {"data": content}
        return JSONResponse(status_code=success_status, content=content)
    else:
        error_message = result.unwrap_error()
        return JSONResponse(
            status_code=error_status,
            content={"error": error_message, "code": "BUSINESS_ERROR"},
        )


def success_response(data: Any, status_code: int = status.HTTP_200_OK) -> JSONResponse:
    """
    성공 응답 생성

    Args:
        data: 응답 데이터
        status_code: HTTP 상태 코드

    Returns:
        JSONResponse: 성공 응답
    """
    if not isinstance(data, dict):
        data = {"data": data}
    return JSONResponse(status_code=status_code, content=data)


def error_response(
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    error_code: str = "BUSINESS_ERROR",
) -> JSONResponse:
    """
    에러 응답 생성

    Args:
        message: 에러 메시지
        status_code: HTTP 상태 코드
        error_code: 에러 코드

    Returns:
        JSONResponse: 에러 응답
    """
    return JSONResponse(
        status_code=status_code, content={"error": message, "code": error_code}
    )
