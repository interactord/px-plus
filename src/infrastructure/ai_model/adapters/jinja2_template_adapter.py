"""
Jinja2TemplateAdapter

Jinja2 템플릿 렌더링 어댑터
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, TemplateSyntaxError

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

from ....domain.ai_model.ports.template_port import TemplatePort
from ....domain.ai_model.value_objects.template_context import TemplateContext


class Jinja2TemplateAdapter(TemplatePort):
    """Jinja2 템플릿 렌더링 어댑터"""

    def __init__(self, template_dir: str):
        """
        어댑터 초기화

        Args:
            template_dir: 템플릿 디렉토리 경로 (절대 경로)
        """
        template_path = Path(template_dir)

        if not template_path.exists():
            raise ValueError(f"템플릿 디렉토리가 존재하지 않습니다: {template_dir}")

        if not template_path.is_dir():
            raise ValueError(f"경로가 디렉토리가 아닙니다: {template_dir}")

        self._template_dir = str(template_path)
        self._env = self._create_environment()

    def _create_environment(self) -> Environment:
        """Jinja2 Environment 생성"""
        return Environment(
            loader=FileSystemLoader(self._template_dir),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )

    def render(
        self,
        template_name: str,
        context: TemplateContext
    ) -> Result[str, str]:
        """템플릿 렌더링"""
        if not template_name or not template_name.strip():
            return Failure("템플릿 이름이 필요합니다")

        if context is None:
            return Failure("템플릿 컨텍스트가 필요합니다")

        try:
            template = self._env.get_template(template_name)
            rendered = template.render(context.to_dict())
            return Success(rendered.strip())

        except TemplateNotFound:
            return Failure(
                f"템플릿을 찾을 수 없습니다: {template_name} "
                f"(디렉토리: {self._template_dir})"
            )
        except TemplateSyntaxError as e:
            return Failure(
                f"템플릿 문법 에러: {e.message} "
                f"(파일: {e.filename}, 라인: {e.lineno})"
            )
        except Exception as e:
            return Failure(f"템플릿 렌더링 실패: {str(e)}")

    def list_templates(self) -> Result[list, str]:
        """사용 가능한 템플릿 목록 반환"""
        try:
            templates = self._env.list_templates()
            return Success(sorted(templates))
        except Exception as e:
            return Failure(f"템플릿 목록 조회 실패: {str(e)}")
