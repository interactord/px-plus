"""
파일 업로드 검증 모듈

파일 크기, 확장자, 개수 등을 검증합니다.
"""

from typing import List, Tuple

from fastapi import HTTPException, UploadFile, status

from ...shared.config import get_upload_settings


class FileUploadValidator:
    """
    파일 업로드 검증 클래스
    """

    def __init__(self):
        """초기화"""
        self.settings = get_upload_settings()

    async def validate_files(
        self, files: List[UploadFile]
    ) -> List[Tuple[str, bytes]]:
        """
        업로드된 파일들을 검증하고 (파일명, 바이트) 튜플 리스트로 반환

        Args:
            files: 업로드된 파일 리스트

        Returns:
            List[Tuple[str, bytes]]: (파일명, 파일 바이트) 튜플 리스트

        Raises:
            HTTPException: 검증 실패 시
        """
        # 1. 파일 개수 검증
        self._validate_file_count(files)

        # 2. 파일 읽기 및 크기 검증
        documents: List[Tuple[str, bytes]] = []
        total_size = 0

        for file in files:
            filename = file.filename or "unnamed"

            # 2-1. 파일 확장자 검증
            self._validate_file_extension(filename)

            # 2-2. 파일 읽기
            file_bytes = await file.read()
            file_size = len(file_bytes)

            # 2-3. 단일 파일 크기 검증
            self._validate_single_file_size(filename, file_size)

            # 2-4. 총합 크기 누적
            total_size += file_size

            documents.append((filename, file_bytes))

        # 3. 전체 파일 총합 크기 검증
        self._validate_total_file_size(total_size)

        return documents

    def _validate_file_count(self, files: List[UploadFile]) -> None:
        """
        파일 개수 검증

        Args:
            files: 업로드된 파일 리스트

        Raises:
            HTTPException: 파일 개수 초과 시
        """
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="업로드된 파일이 없습니다.",
            )

        if len(files) > self.settings.max_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"최대 {self.settings.max_files}개까지 업로드 가능합니다. "
                f"(현재: {len(files)}개)",
            )

    def _validate_file_extension(self, filename: str) -> None:
        """
        파일 확장자 검증

        Args:
            filename: 파일 이름

        Raises:
            HTTPException: 허용되지 않는 확장자인 경우
        """
        # 파일 확장자 추출 (소문자로 변환)
        ext = ""
        if "." in filename:
            ext = "." + filename.rsplit(".", 1)[-1].lower()

        # 허용된 확장자 목록과 비교
        allowed_exts = self.settings.allowed_extensions_list
        if ext not in allowed_exts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{filename}': 허용되지 않는 파일 형식입니다. "
                f"허용 형식: {', '.join(allowed_exts)}",
            )

    def _validate_single_file_size(self, filename: str, file_size: int) -> None:
        """
        단일 파일 크기 검증

        Args:
            filename: 파일 이름
            file_size: 파일 크기 (바이트)

        Raises:
            HTTPException: 파일 크기 초과 시
        """
        if file_size > self.settings.max_file_size:
            max_size_str = self.settings.format_size(self.settings.max_file_size)
            current_size_str = self.settings.format_size(file_size)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"'{filename}': 파일 크기가 최대 크기({max_size_str})를 초과했습니다. "
                f"(현재: {current_size_str})",
            )

    def _validate_total_file_size(self, total_size: int) -> None:
        """
        전체 파일 총합 크기 검증

        Args:
            total_size: 전체 파일 크기 합계 (바이트)

        Raises:
            HTTPException: 총합 크기 초과 시
        """
        if total_size > self.settings.max_total_file_size:
            max_total_str = self.settings.format_size(
                self.settings.max_total_file_size
            )
            current_total_str = self.settings.format_size(total_size)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"전체 파일 크기가 최대 총합({max_total_str})을 초과했습니다. "
                f"(현재: {current_total_str})",
            )


# 전역 인스턴스
_validator: FileUploadValidator | None = None


def get_file_validator() -> FileUploadValidator:
    """
    파일 검증 인스턴스를 반환 (싱글톤 패턴)

    Returns:
        FileUploadValidator: 파일 검증 인스턴스
    """
    global _validator
    if _validator is None:
        _validator = FileUploadValidator()
    return _validator
