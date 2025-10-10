"""
통합 로깅 시스템

RFS Framework 4.6.6 기반 동기/비동기 통합 로거
"""

import logging
import json
import sys
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from rfs.core.result import Result, Success, Failure


class LogLevel(str, Enum):
    """로그 레벨"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class UnifiedLogger:
    """
    통합 로거 클래스
    
    동기/비동기 메서드를 모두 지원하며, 구조화된 JSON 로깅을 제공합니다.
    """
    
    def __init__(self, name: str, context: Optional[Dict[str, Any]] = None):
        """
        로거 초기화
        
        Args:
            name: 로거 이름 (일반적으로 __name__ 사용)
            context: 기본 컨텍스트 (모든 로그에 포함됨)
        """
        self.name = name
        self.context = context or {}
        self._logger = logging.getLogger(name)
    
    def _format_log_data(self, message: str, **kwargs: Any) -> Dict[str, Any]:
        """
        로그 데이터를 구조화된 형식으로 포맷팅
        
        Args:
            message: 로그 메시지
            **kwargs: 추가 데이터
        
        Returns:
            구조화된 로그 데이터
        """
        return {
            "message": message,
            "context": {**self.context, **kwargs},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    # ===========================================
    # 동기 로깅 메서드
    # ===========================================
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """DEBUG 레벨 로그 (동기)"""
        log_data = self._format_log_data(message, **kwargs)
        self._logger.debug(json.dumps(log_data, ensure_ascii=False))
    
    def info(self, message: str, **kwargs: Any) -> None:
        """INFO 레벨 로그 (동기)"""
        log_data = self._format_log_data(message, **kwargs)
        self._logger.info(json.dumps(log_data, ensure_ascii=False))
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """WARNING 레벨 로그 (동기)"""
        log_data = self._format_log_data(message, **kwargs)
        self._logger.warning(json.dumps(log_data, ensure_ascii=False))
    
    def error(self, message: str, **kwargs: Any) -> None:
        """ERROR 레벨 로그 (동기)"""
        log_data = self._format_log_data(message, **kwargs)
        self._logger.error(json.dumps(log_data, ensure_ascii=False))
    
    def critical(self, message: str, **kwargs: Any) -> None:
        """CRITICAL 레벨 로그 (동기)"""
        log_data = self._format_log_data(message, **kwargs)
        self._logger.critical(json.dumps(log_data, ensure_ascii=False))
    
    # ===========================================
    # 비동기 로깅 메서드
    # ===========================================
    
    async def debug_async(self, message: str, **kwargs: Any) -> Result[None, str]:
        """DEBUG 레벨 로그 (비동기)"""
        try:
            self.debug(message, **kwargs)
            return Success(None)
        except Exception as e:
            return Failure(f"로그 작성 실패: {str(e)}")
    
    async def info_async(self, message: str, **kwargs: Any) -> Result[None, str]:
        """INFO 레벨 로그 (비동기)"""
        try:
            self.info(message, **kwargs)
            return Success(None)
        except Exception as e:
            return Failure(f"로그 작성 실패: {str(e)}")
    
    async def warning_async(self, message: str, **kwargs: Any) -> Result[None, str]:
        """WARNING 레벨 로그 (비동기)"""
        try:
            self.warning(message, **kwargs)
            return Success(None)
        except Exception as e:
            return Failure(f"로그 작성 실패: {str(e)}")
    
    async def error_async(self, message: str, **kwargs: Any) -> Result[None, str]:
        """ERROR 레벨 로그 (비동기)"""
        try:
            self.error(message, **kwargs)
            return Success(None)
        except Exception as e:
            return Failure(f"로그 작성 실패: {str(e)}")
    
    async def critical_async(self, message: str, **kwargs: Any) -> Result[None, str]:
        """CRITICAL 레벨 로그 (비동기)"""
        try:
            self.critical(message, **kwargs)
            return Success(None)
        except Exception as e:
            return Failure(f"로그 작성 실패: {str(e)}")
    
    # ===========================================
    # 특수 로깅 메서드
    # ===========================================
    
    def log_operation(
        self, 
        operation: str, 
        status: str = "started", 
        **metadata: Any
    ) -> None:
        """
        작업 로깅
        
        Args:
            operation: 작업 이름
            status: 작업 상태 (started, completed, failed)
            **metadata: 추가 메타데이터
        """
        self.info(
            f"작업 {status}",
            operation=operation,
            status=status,
            **metadata
        )
    
    def log_performance(
        self,
        operation: str,
        duration_ms: float,
        **metadata: Any
    ) -> None:
        """
        성능 메트릭 로깅
        
        Args:
            operation: 측정 대상 작업
            duration_ms: 실행 시간 (밀리초)
            **metadata: 추가 성능 지표
        """
        self.info(
            "성능 메트릭",
            operation=operation,
            duration_ms=duration_ms,
            **metadata
        )
    
    def log_error_with_context(
        self,
        error: Exception,
        operation: str,
        **context: Any
    ) -> None:
        """
        에러와 컨텍스트를 함께 로깅
        
        Args:
            error: 발생한 예외
            operation: 에러 발생 작업
            **context: 디버깅 컨텍스트
        """
        self.error(
            f"에러 발생: {str(error)}",
            operation=operation,
            error_type=type(error).__name__,
            error_message=str(error),
            **context
        )
    
    async def log_error_with_context_async(
        self,
        error: Exception,
        operation: str,
        **context: Any
    ) -> Result[None, str]:
        """
        에러와 컨텍스트를 함께 로깅 (비동기)
        
        Args:
            error: 발생한 예외
            operation: 에러 발생 작업
            **context: 디버깅 컨텍스트
        """
        try:
            self.log_error_with_context(error, operation, **context)
            return Success(None)
        except Exception as e:
            return Failure(f"에러 로깅 실패: {str(e)}")
    
    # ===========================================
    # 컨텍스트 관리
    # ===========================================
    
    def with_context(self, **additional_context: Any) -> "UnifiedLogger":
        """
        새로운 컨텍스트를 추가한 로거 생성
        
        Args:
            **additional_context: 추가할 컨텍스트
        
        Returns:
            새로운 컨텍스트를 가진 로거
        """
        merged_context = {**self.context, **additional_context}
        return UnifiedLogger(self.name, merged_context)


# ===========================================
# 전역 함수
# ===========================================

def get_logger(name: str, context: Optional[Dict[str, Any]] = None) -> UnifiedLogger:
    """
    로거 인스턴스 생성
    
    Args:
        name: 로거 이름 (일반적으로 __name__ 사용)
        context: 기본 컨텍스트
    
    Returns:
        UnifiedLogger 인스턴스
    """
    return UnifiedLogger(name, context)


def setup_logging(
    level: LogLevel = LogLevel.INFO,
    enable_json: bool = True,
    log_file: Optional[Path] = None
) -> None:
    """
    로깅 시스템 초기화
    
    Args:
        level: 로그 레벨
        enable_json: JSON 형식 로깅 활성화 (False면 텍스트 형식)
        log_file: 로그 파일 경로 (None이면 stdout만 사용)
    """
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.value))
    
    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.value))
    
    if enable_json:
        # JSON 형식
        formatter = logging.Formatter('%(message)s')
    else:
        # 텍스트 형식
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 파일 핸들러 (선택사항)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, level.value))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
