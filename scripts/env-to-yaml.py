#!/usr/bin/env python3
"""
.env 파일을 Cloud Run YAML 환경변수 형식으로 변환하는 스크립트

사용법:
    python scripts/env-to-yaml.py .env > env-vars.yaml
    python scripts/env-to-yaml.py .env.production > env-vars-prod.yaml
"""

import sys
import re
from pathlib import Path
from typing import Dict, List, Tuple


def parse_env_file(env_path: Path) -> Dict[str, str]:
    """
    .env 파일을 파싱하여 환경변수 딕셔너리 반환
    
    Args:
        env_path: .env 파일 경로
        
    Returns:
        환경변수 딕셔너리 {key: value}
    """
    env_vars = {}
    
    if not env_path.exists():
        print(f"Error: {env_path} 파일을 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)
    
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            
            # 주석이나 빈 줄 건너뛰기
            if not line or line.startswith('#') or line.startswith('='):
                continue
            
            # KEY=VALUE 형식 파싱
            match = re.match(r'^([A-Z_][A-Z0-9_]*)=(.*)$', line)
            if match:
                key, value = match.groups()
                
                # 따옴표 제거
                value = value.strip()
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                env_vars[key] = value
    
    return env_vars


def filter_sensitive_vars(env_vars: Dict[str, str]) -> Tuple[Dict[str, str], List[str]]:
    """
    민감한 환경변수와 일반 환경변수 분리
    
    민감한 변수는 Google Secret Manager를 사용해야 함
    
    Args:
        env_vars: 전체 환경변수 딕셔너리
        
    Returns:
        (일반 환경변수, 민감한 변수 키 리스트)
    """
    sensitive_keywords = [
        'API_KEY', 'SECRET', 'PASSWORD', 'TOKEN', 'PRIVATE', 'CREDENTIAL',
        'AWS_ACCESS_KEY', 'AWS_SECRET', 'WEBHOOK_URL'
    ]
    
    normal_vars = {}
    sensitive_keys = []
    
    for key, value in env_vars.items():
        is_sensitive = any(keyword in key for keyword in sensitive_keywords)
        
        if is_sensitive:
            sensitive_keys.append(key)
        else:
            normal_vars[key] = value
    
    return normal_vars, sensitive_keys


def generate_yaml(env_vars: Dict[str, str], sensitive_keys: List[str]) -> str:
    """
    Cloud Run YAML 형식의 환경변수 설정 생성
    
    Args:
        env_vars: 일반 환경변수 딕셔너리
        sensitive_keys: 민감한 변수 키 리스트
        
    Returns:
        YAML 형식 문자열
    """
    yaml_lines = [
        "# ========================================",
        "# Cloud Run Environment Variables",
        "# ========================================",
        "# 이 파일은 자동 생성되었습니다. 직접 수정하지 마세요.",
        "",
        "env:",
    ]
    
    # 일반 환경변수
    for key, value in sorted(env_vars.items()):
        # 값에 특수문자가 있으면 따옴표로 감싸기
        if any(char in value for char in [' ', ':', '#', ',', '[', ']', '{', '}']):
            yaml_lines.append(f"  - name: {key}")
            yaml_lines.append(f'    value: "{value}"')
        else:
            yaml_lines.append(f"  - name: {key}")
            yaml_lines.append(f"    value: {value}")
    
    # 민감한 변수는 주석으로 표시
    if sensitive_keys:
        yaml_lines.extend([
            "",
            "# ========================================",
            "# 민감한 환경변수 (Secret Manager 사용 필요)",
            "# ========================================",
            "# 다음 변수들은 Google Secret Manager를 통해 설정하세요:",
        ])
        
        for key in sorted(sensitive_keys):
            yaml_lines.append(f"# - {key}")
        
        yaml_lines.extend([
            "",
            "# Secret Manager 설정 예시:",
            "# secrets:",
            "#   - name: GOOGLE_API_KEY",
            "#     valueFrom:",
            "#       secretKeyRef:",
            "#         key: latest",
            "#         name: google-api-key",
        ])
    
    return '\n'.join(yaml_lines)


def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("Usage: python env-to-yaml.py <env-file>", file=sys.stderr)
        print("Example: python env-to-yaml.py .env > env-vars.yaml", file=sys.stderr)
        sys.exit(1)
    
    env_path = Path(sys.argv[1])
    
    # .env 파일 파싱
    env_vars = parse_env_file(env_path)
    
    # 민감한 변수 분리
    normal_vars, sensitive_keys = filter_sensitive_vars(env_vars)
    
    # YAML 생성
    yaml_content = generate_yaml(normal_vars, sensitive_keys)
    
    # 출력
    print(yaml_content)
    
    # 통계 정보 (stderr로 출력)
    print(f"\n# 변환 완료:", file=sys.stderr)
    print(f"# - 일반 환경변수: {len(normal_vars)}개", file=sys.stderr)
    print(f"# - 민감한 환경변수: {len(sensitive_keys)}개", file=sys.stderr)
    print(f"# - 총 환경변수: {len(env_vars)}개", file=sys.stderr)


if __name__ == "__main__":
    main()
