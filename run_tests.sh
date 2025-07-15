#!/bin/bash

# AWS Cost Slack Reporter 테스트 실행 스크립트
# 사용법: ./run_tests.sh [옵션]

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 도움말 출력
show_help() {
    echo "AWS Cost Slack Reporter 테스트 실행 스크립트"
    echo ""
    echo "사용법: $0 [옵션]"
    echo ""
    echo "옵션:"
    echo "  -h, --help          이 도움말을 출력합니다"
    echo "  -u, --unit          단위 테스트만 실행합니다"
    echo "  -i, --integration   통합 테스트만 실행합니다"
    echo "  -a, --all           모든 테스트를 실행합니다 (기본값)"
    echo "  -c, --coverage      커버리지 리포트를 생성합니다"
    echo "  -v, --verbose       상세한 출력을 활성화합니다"
    echo "  -k, --keep-going    실패해도 계속 진행합니다"
    echo "  --no-cov            커버리지 측정을 비활성화합니다"
    echo ""
    echo "예시:"
    echo "  $0                    # 모든 테스트 실행"
    echo "  $0 -u                 # 단위 테스트만 실행"
    echo "  $0 -i -v              # 통합 테스트를 상세하게 실행"
    echo "  $0 -c --no-cov        # 커버리지 없이 모든 테스트 실행"
}

# 환경 확인
check_environment() {
    log_info "환경 확인 중..."
    
    # Python 버전 확인
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        log_info "Python 버전: $PYTHON_VERSION"
    else
        log_error "Python3가 설치되지 않았습니다."
        exit 1
    fi
    
    # pytest 확인
    if ! python3 -c "import pytest" &> /dev/null; then
        log_warning "pytest가 설치되지 않았습니다. 설치를 시도합니다..."
        pip install pytest pytest-cov pytest-mock
    fi
    
    # 환경 변수 확인
    if [ -f ".env" ]; then
        log_info ".env 파일이 존재합니다."
        source .env
    else
        log_warning ".env 파일이 없습니다. 테스트용 환경 변수를 사용합니다."
    fi
    
    # 테스트 디렉토리 확인
    if [ ! -d "tests" ]; then
        log_error "tests 디렉토리가 없습니다."
        exit 1
    fi
}

# 테스트 실행
run_tests() {
    local test_type="$1"
    local pytest_args="$2"
    
    log_info "$test_type 테스트 실행 중..."
    
    case "$test_type" in
        "unit")
            pytest tests/test_holiday_checker.py tests/test_exchange_rate.py $pytest_args
            ;;
        "integration")
            pytest tests/test_integration.py tests/test_lambda_function.py $pytest_args
            ;;
        "all")
            pytest tests/ $pytest_args
            ;;
        *)
            log_error "알 수 없는 테스트 타입: $test_type"
            exit 1
            ;;
    esac
}

# 커버리지 리포트 생성
generate_coverage_report() {
    log_info "커버리지 리포트 생성 중..."
    
    # HTML 리포트
    if [ -d "htmlcov" ]; then
        log_info "HTML 커버리지 리포트: file://$(pwd)/htmlcov/index.html"
    fi
    
    # XML 리포트 (CI/CD용)
    if [ -f "coverage.xml" ]; then
        log_info "XML 커버리지 리포트: coverage.xml"
    fi
}

# 메인 함수
main() {
    local test_type="all"
    local pytest_args=""
    local coverage_enabled=true
    local verbose=false
    local keep_going=false
    
    # 인자 파싱
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -u|--unit)
                test_type="unit"
                shift
                ;;
            -i|--integration)
                test_type="integration"
                shift
                ;;
            -a|--all)
                test_type="all"
                shift
                ;;
            -c|--coverage)
                coverage_enabled=true
                shift
                ;;
            -v|--verbose)
                verbose=true
                pytest_args="$pytest_args -v"
                shift
                ;;
            -k|--keep-going)
                keep_going=true
                pytest_args="$pytest_args --tb=no"
                shift
                ;;
            --no-cov)
                coverage_enabled=false
                shift
                ;;
            *)
                log_error "알 수 없는 옵션: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 기본 설정
    if [ "$verbose" = false ]; then
        pytest_args="$pytest_args -q"
    fi
    
    if [ "$coverage_enabled" = true ]; then
        pytest_args="$pytest_args --cov=src --cov-report=term-missing --cov-report=html --cov-report=xml"
    fi
    
    # 환경 확인
    check_environment
    
    # 테스트 실행
    echo ""
    log_info "테스트 시작: $(date)"
    echo "=================================="
    
    if run_tests "$test_type" "$pytest_args"; then
        log_success "모든 테스트가 성공적으로 완료되었습니다!"
        
        if [ "$coverage_enabled" = true ]; then
            generate_coverage_report
        fi
    else
        log_error "일부 테스트가 실패했습니다."
        if [ "$keep_going" = false ]; then
            exit 1
        fi
    fi
    
    echo "=================================="
    log_info "테스트 완료: $(date)"
}

# 스크립트 실행
main "$@" 