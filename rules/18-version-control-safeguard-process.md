# 버전 관리 보호 프로세스 (Version Control Safeguard Process)

## 🎯 목적
자동화된 코드 수정 도구 사용 시 발생할 수 있는 문제를 방지하고, 안전한 버전 관리 프로세스를 보장합니다.

## ⚠️ 핵심 원칙

### 1. 사전 검증 필수 (Pre-Validation Required)
```bash
# 모든 자동화 도구 사용 전 필수 체크
PRE_VALIDATION_CHECKLIST=(
    "가상환경 활성화 확인"
    "현재 상태 통계 기록"
    "Git 상태 정리 (clean working tree)"
    "작업 백업 생성"
    "전용 브랜치 생성"
)
```

### 2. 점진적 적용 원칙 (Incremental Application)
- **금지**: 전체 프로젝트 한 번에 수정
- **권장**: 디렉토리별, 모듈별 단계적 적용
- **필수**: 각 단계마다 검증 후 다음 단계 진행

### 3. 즉시 롤백 준비 (Immediate Rollback Readiness)
- **검증 실패 시**: 해당 변경사항 즉시 폐기
- **구문 오류 발견 시**: 자동 롤백 프로세스 실행
- **테스트 실패 시**: 원인 분석 후 롤백/수정 결정

## 🛡️ 자동화 도구별 보호 프로세스

### Black (코드 포맷터)
```bash
# 안전한 Black 적용 프로세스
safe_black_format() {
    local target_dir=$1
    
    # 1. 사전 체크
    black --check --diff "$target_dir" || {
        echo "Black 포맷팅이 필요합니다: $target_dir"
        
        # 2. 백업
        git stash push -m "black_backup_$(date +%s)_$target_dir"
        
        # 3. 적용
        black "$target_dir"
        
        # 4. 검증
        if python -m py_compile $(find "$target_dir" -name "*.py") 2>/dev/null; then
            echo "✅ Black 포맷팅 성공: $target_dir"
            git add "$target_dir"
        else
            echo "❌ Black 포맷팅으로 구문 오류 발생: $target_dir"
            git checkout -- "$target_dir"
            return 1
        fi
    }
}
```

### Isort (임포트 정리)
```bash
# 안전한 Isort 적용 프로세스
safe_isort_format() {
    local target_dir=$1
    
    # 1. 사전 체크
    isort --check-only --diff "$target_dir" || {
        echo "Isort 정리가 필요합니다: $target_dir"
        
        # 2. 적용
        isort "$target_dir"
        
        # 3. 검증 (임포트 오류 체크)
        if python -c "import sys; sys.path.insert(0, '$target_dir'); import importlib; importlib.import_module($(basename $target_dir))" 2>/dev/null; then
            echo "✅ Isort 정리 성공: $target_dir"
        else
            echo "❌ Isort 정리로 임포트 오류 발생: $target_dir"
            git checkout -- "$target_dir"
            return 1
        fi
    }
}
```

### Flake8 (코드 품질 검사)
```bash
# 안전한 Flake8 기반 수정
safe_flake8_fix() {
    local target_file=$1
    
    # 1. 수정 전 위반 수 기록
    local before_count=$(flake8 --count "$target_file" 2>/dev/null || echo "0")
    
    # 2. 자동 수정 적용 (예: autopep8)
    autopep8 --in-place --aggressive "$target_file"
    
    # 3. 수정 후 검증
    local after_count=$(flake8 --count "$target_file" 2>/dev/null || echo "0")
    
    if [[ $after_count -le $before_count ]] && [[ $(python -m py_compile "$target_file" 2>/dev/null; echo $?) -eq 0 ]]; then
        echo "✅ Flake8 수정 성공: $target_file ($before_count → $after_count)"
    else
        echo "❌ Flake8 수정으로 문제 발생: $target_file"
        git checkout -- "$target_file"
        return 1
    fi
}
```

## 📋 필수 체크리스트

### 자동화 도구 사용 전
- [ ] **가상환경 활성화**: `source venv/bin/activate`
- [ ] **Git 상태 정리**: `git status` (clean working tree)
- [ ] **현재 통계 저장**: `flake8 --statistics --count src/ > before_stats.txt`
- [ ] **백업 생성**: `git stash push -m "automation_backup_$(date +%s)"`
- [ ] **전용 브랜치**: `git checkout -b feature/automated-fixes`

### 자동화 도구 사용 중
- [ ] **디렉토리별 적용**: 전체 프로젝트 한 번에 처리 금지
- [ ] **단계별 검증**: 각 디렉토리 처리 후 즉시 검증
- [ ] **구문 오류 체크**: `flake8 --select=E999 target_dir/`
- [ ] **컴파일 검증**: `python -m py_compile target_files`
- [ ] **테스트 실행**: 관련 테스트가 있는 경우 실행

### 자동화 도구 사용 후
- [ ] **전체 통계 비교**: `flake8 --statistics --count src/ > after_stats.txt`
- [ ] **개선 효과 측정**: before vs after 비교
- [ ] **전체 테스트**: `pytest` 또는 관련 테스트 수행
- [ ] **최종 커밋**: 검증 완료된 변경사항만 커밋

## 🚨 긴급 롤백 프로시저

### 즉시 롤백 (Critical Issues)
```bash
# 구문 오류, 컴파일 실패 등 즉시 해결해야 하는 경우
emergency_rollback() {
    echo "🚨 긴급 롤백 실행 중..."
    
    # 1. 모든 변경사항 폐기
    git checkout -- .
    
    # 2. 스태시된 백업 복구
    git stash list | head -1 | grep -q "automation_backup" && {
        git stash pop
        echo "✅ 백업에서 복구 완료"
    }
    
    echo "✅ 긴급 롤백 완료"
}
```

### 선택적 롤백 (Partial Issues)
```bash
# 일부 파일만 문제가 있는 경우
selective_rollback() {
    local problem_files=("$@")
    
    echo "⚠️ 선택적 롤백 실행 중..."
    
    for file in "${problem_files[@]}"; do
        git checkout -- "$file"
        echo "복구 완료: $file"
    done
    
    echo "✅ 선택적 롤백 완료"
}
```

## 🔧 자동화 스크립트

### 마스터 안전 스크립트
```bash
#!/bin/bash
# scripts/safe_automation.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 설정
TOOLS=("black" "isort" "flake8")
DIRECTORIES=("src/shared/kernel" "src/health" "src/config")

main() {
    echo "🛡️ 안전한 자동화 프로세스 시작"
    
    # 사전 검증
    pre_validation || exit 1
    
    # 백업 생성
    create_backup || exit 1
    
    # 디렉토리별 처리
    for dir in "${DIRECTORIES[@]}"; do
        process_directory "$dir" || {
            echo "❌ $dir 처리 실패, 롤백 중..."
            emergency_rollback
            exit 1
        }
    done
    
    # 최종 검증
    final_validation || {
        echo "❌ 최종 검증 실패, 롤백 중..."
        emergency_rollback
        exit 1
    }
    
    echo "✅ 안전한 자동화 프로세스 완료"
}

pre_validation() {
    echo "📋 사전 검증 중..."
    
    # 가상환경 체크
    [[ -n "$VIRTUAL_ENV" ]] || {
        echo "❌ 가상환경이 활성화되지 않음"
        return 1
    }
    
    # Git 상태 체크
    git diff-index --quiet HEAD -- || {
        echo "❌ Git working tree가 clean하지 않음"
        return 1
    }
    
    # 도구 설치 체크
    for tool in "${TOOLS[@]}"; do
        command -v "$tool" >/dev/null || {
            echo "❌ $tool이 설치되지 않음"
            return 1
        }
    done
    
    echo "✅ 사전 검증 완료"
}

create_backup() {
    echo "💾 백업 생성 중..."
    
    # 현재 통계 저장
    flake8 --statistics --count src/ > "$PROJECT_DIR/before_automation_stats.txt"
    
    # Git 백업
    git stash push -m "automation_backup_$(date +%s)"
    
    # 브랜치 생성
    git checkout -b "feature/automated-fixes-$(date +%Y%m%d-%H%M%S)"
    
    echo "✅ 백업 생성 완료"
}

process_directory() {
    local dir=$1
    echo "🔧 처리 중: $dir"
    
    # Black 적용
    safe_black_format "$dir" || return 1
    
    # Isort 적용
    safe_isort_format "$dir" || return 1
    
    # 검증
    validate_directory "$dir" || return 1
    
    # 커밋
    git add "$dir"
    git commit -m "자동화: $dir Black/Isort 적용"
    
    echo "✅ 완료: $dir"
}

# 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
```

## 📝 학습된 교훈 기록

### 2024년 경험 사례
**상황**: Black/Isort 전체 프로젝트 적용
**문제**: 4개 파일에 null bytes 구문 오류 발생
**해결**: 즉시 수동 수정, 개선된 프로세스 도입
**교훈**: 전체 적용보다 점진적 적용이 안전

### 핵심 원칙 재확인
1. **사용자 직감 신뢰**: "자동 수정이 더 문제를 일으킬 수 있다"는 우려가 정확
2. **철저한 검증**: 자동화 도구도 완벽하지 않음
3. **단계적 접근**: 작은 단위로 나누어 적용
4. **즉시 복구**: 문제 발견 시 지체 없이 롤백

## 🎯 적용 가이드라인

### 언제 이 프로세스를 사용해야 하는가?
- 코드 포맷팅 도구 (Black, autopep8) 사용 시
- 임포트 정리 도구 (isort, reorder-python-imports) 사용 시  
- 코드 품질 도구 (flake8, pylint) 기반 자동 수정 시
- 대규모 리팩토링 도구 사용 시

### 예외 상황
- 단일 파일 수정
- 명확히 안전한 변경 (주석, 문서화)
- 테스트 환경에서의 실험

---

**최종 메시지**: 자동화는 생산성을 높이지만, 안전성을 보장하는 프로세스가 반드시 필요합니다. 이 가이드라인을 통해 자동화의 이점을 누리면서도 예상치 못한 문제를 방지할 수 있습니다.