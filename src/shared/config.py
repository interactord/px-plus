"""
환경 변수 설정 모듈

.env 파일의 환경 변수를 로딩하고 타입 안전하게 관리합니다.
"""

import os
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class UploadSettings(BaseSettings):
    """
    파일 업로드 관련 설정
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 단일 파일 최대 크기 (바이트 단위, 기본: 10MB)
    max_file_size: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        description="단일 파일 최대 크기 (바이트)",
    )

    # 전체 업로드 파일 총합 최대 크기 (바이트 단위, 기본: 20MB)
    max_total_file_size: int = Field(
        default=20 * 1024 * 1024,  # 20MB
        description="전체 업로드 파일 총합 최대 크기 (바이트)",
    )

    # 허용되는 파일 확장자
    allowed_extensions: str = Field(
        default=".txt,.md,.pdf,.docx,.xlsx,.csv,.json,.pptx,.ppt",
        description="허용되는 파일 확장자 (콤마로 구분)",
    )

    # 최대 업로드 파일 개수
    max_files: int = Field(
        default=10,
        description="최대 업로드 파일 개수",
    )

    # 업로드 디렉토리
    upload_dir: str = Field(
        default="./uploads",
        description="업로드 파일 저장 디렉토리",
    )

    # 업로드 파일 정리 주기 (일 단위)
    cleanup_days: int = Field(
        default=30,
        description="업로드 파일 정리 주기 (일)",
    )

    @property
    def allowed_extensions_list(self) -> List[str]:
        """
        허용되는 파일 확장자 리스트 반환

        Returns:
            List[str]: 허용 확장자 리스트 (예: ['.txt', '.pdf'])
        """
        return [ext.strip() for ext in self.allowed_extensions.split(",")]

    def format_size(self, size_bytes: int) -> str:
        """
        바이트 크기를 사람이 읽기 쉬운 형식으로 변환

        Args:
            size_bytes: 바이트 단위 크기

        Returns:
            str: 포맷된 크기 문자열 (예: "10.5 MB")
        """
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


class Settings(BaseSettings):
    """
    전체 애플리케이션 설정
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 서버 설정
    api_host: str = Field(default="0.0.0.0", description="API 서버 호스트")
    api_port: int = Field(default=8002, description="API 서버 포트")
    workers: int = Field(default=1, description="워커 프로세스 수")

    # 애플리케이션 설정
    log_level: str = Field(default="INFO", description="로그 레벨")
    environment: str = Field(default="development", description="실행 환경")

    # 업로드 설정
    upload: UploadSettings = Field(default_factory=UploadSettings)


# 싱글톤 인스턴스
_settings: Settings | None = None


def get_settings() -> Settings:
    """
    설정 인스턴스를 반환 (싱글톤 패턴)

    Returns:
        Settings: 애플리케이션 설정 인스턴스
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def get_upload_settings() -> UploadSettings:
    """
    업로드 설정 인스턴스를 반환

    Returns:
        UploadSettings: 업로드 설정 인스턴스
    """
    return get_settings().upload
