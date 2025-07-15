#!/bin/bash
# AWS Cost Slack Reporter - 설치 스크립트

set -e

echo "🚀 AWS Cost Slack Reporter 설치 시작"
echo "=================================="

# 시스템 체크
echo "🔍 시스템 환경 확인 중..."

# Python 확인
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3이 설치되지 않았습니다."
    echo "💡 Python 3.9 이상을 설치해주세요."
    exit 1
fi

python_version=$(python3 --version | grep -o '[0-9]\+\.[0-9]\+' | head -1)
echo "✅ Python $python_version 감지"

# AWS CLI 확인
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI가 설치되지 않았습니다."
    echo "💡 AWS CLI를 설치하고 'aws configure'를 실행해주세요."
    echo "📖 가이드: https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html"
    exit 1
fi

echo "✅ AWS CLI 감지"

# AWS 인증 확인
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS 인증이 설정되지 않았습니다."
    echo "💡 'aws configure' 명령어로 인증을 설정해주세요."
    exit 1
fi

aws_account=$(aws sts get-caller-identity --query 'Account' --output text)
aws_region=$(aws configure get region)
echo "✅ AWS 계정: $aws_account, 리전: $aws_region"

# uv 설치 확인
if ! command -v uv &> /dev/null; then
    echo "📦 uv 패키지 매니저 설치 중..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source ~/.bashrc
    
    # uv 재확인
    if ! command -v uv &> /dev/null; then
        echo "⚠️  uv 설치가 완료되었지만 PATH에 추가되지 않았습니다."
        echo "💡 터미널을 재시작하거나 'source ~/.bashrc'를 실행해주세요."
        echo "💡 또는 다음 명령어를 실행하세요:"
        echo "   export PATH=\"\$HOME/.cargo/bin:\$PATH\""
    fi
fi

echo "✅ uv 패키지 매니저 사용 가능"

# 의존성 설치
echo "📦 의존성 설치 중..."
uv sync

# 환경 변수 파일 생성
echo "🔧 환경 변수 파일 생성 중..."
python setup_env.py

echo ""
echo "✅ 설치 완료!"
echo ""
echo "📋 다음 단계:"
echo "1. .env 파일을 편집하여 API 키들을 입력하세요:"
echo "   nano .env"
echo ""
echo "2. 필요한 API 키들:"
echo "   - Slack Bot Token (https://api.slack.com/apps)"
echo "   - 공공데이터포털 API Key (https://www.data.go.kr/)"
echo "   - CurrencyAPI.com API Key (https://currencyapi.com/)"
echo ""
echo "3. 설정 완료 후 배포하세요:"
echo "   ./deploy.sh"
echo ""
echo "📖 자세한 가이드는 README.md를 참고하세요." 