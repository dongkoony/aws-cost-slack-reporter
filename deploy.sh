#!/bin/bash
# AWS Cost Slack Reporter - 배포 스크립트

set -e  # 에러 발생 시 스크립트 중단

echo "🚀 AWS Cost Slack Reporter 배포 시작"
echo "=================================="

# 환경 변수 파일 확인
if [ ! -f .env ]; then
    echo "❌ .env 파일이 존재하지 않습니다."
    echo "💡 python setup_env.py를 실행하여 .env 파일을 생성하세요."
    exit 1
fi

# 환경 변수 검증
echo "🔧 환경 변수 검증 중..."
python setup_env.py validate
if [ $? -ne 0 ]; then
    echo "❌ 환경 변수 설정이 올바르지 않습니다."
    exit 1
fi

# 의존성 설치
echo "📦 의존성 설치 중..."
uv sync

# 테스트 실행
echo "🧪 테스트 실행 중..."
if command -v pytest &> /dev/null; then
    pytest tests/ -v
else
    echo "⚠️  pytest가 설치되지 않았습니다. 테스트를 건너뜁니다."
fi

# Lambda 패키지 생성 (pip install -t 방식)
echo "📦 Lambda 패키지 생성 중..."
rm -f lambda-package.zip
rm -rf lambda_build
mkdir lambda_build

# 필요한 패키지만 lambda_build 디렉토리에 설치
echo "📦 필요한 패키지 설치 중..."
pip install requests slack_sdk matplotlib python-dotenv -t lambda_build

# 패키지 설치 확인
echo "📋 설치된 패키지 확인..."
ls -la lambda_build/

# 소스코드 복사
echo "📁 소스코드 복사 중..."
cp -r src lambda_build/

# zip 생성
echo "📦 zip 파일 생성 중..."
cd lambda_build
zip -r ../lambda-package.zip . -x "*.pyc" "__pycache__/*" "*.dist-info/*" "*.egg-info/*"
cd ..

# 정리
rm -rf lambda_build

# zip 파일 확인
if [ -f lambda-package.zip ]; then
    echo "✅ Lambda 패키지 생성 성공"
else
    echo "❌ Lambda 패키지 생성 실패"
    exit 1
fi

# 2. src/ 디렉토리 추가 압축
zip -g lambda-package.zip -r src/ -x "*.pyc" "__pycache__/*" "*.DS_Store"

# 패키지 크기 확인
package_size=$(du -h lambda-package.zip | cut -f1)
echo "📊 패키지 크기: $package_size"

# Lambda 함수 존재 여부 확인
FUNCTION_NAME="aws-cost-slack-reporter"
REGION="${AWS_DEFAULT_REGION:-ap-northeast-2}"

if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION &> /dev/null; then
    echo "🔄 기존 Lambda 함수 업데이트 중..."
    
    # 함수 코드 업데이트
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://lambda-package.zip \
        --region $REGION
    
    # 환경 변수 설정
    echo "🔧 환경 변수 설정 중..."
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --environment Variables="{
            SLACK_BOT_TOKEN=$(grep SLACK_BOT_TOKEN .env | cut -d'=' -f2),
            SLACK_CHANNEL=$(grep SLACK_CHANNEL .env | cut -d'=' -f2),
            PUBLIC_DATA_API_KEY=$(grep PUBLIC_DATA_API_KEY .env | cut -d'=' -f2),
            CURRENCY_API_KEY=$(grep CURRENCY_API_KEY .env | cut -d'=' -f2)
        }" \
        --region $REGION
    
    # 함수 설정 업데이트
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --timeout 300 \
        --memory-size 512 \
        --region $REGION
    
else
    echo "🆕 새로운 Lambda 함수 생성 중..."
    
    # IAM 역할 생성 (필요시)
    ROLE_NAME="aws-cost-slack-reporter-role"
    if ! aws iam get-role --role-name $ROLE_NAME &> /dev/null; then
        echo "🔐 IAM 역할 생성 중..."
        
        # 신뢰 정책 생성
        cat > trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF
        
        # 역할 생성
        aws iam create-role \
            --role-name $ROLE_NAME \
            --assume-role-policy-document file://trust-policy.json
        
        # 정책 연결
        aws iam attach-role-policy \
            --role-name $ROLE_NAME \
            --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
        
        # Cost Explorer 정책 생성
        cat > cost-explorer-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ce:GetCostAndUsage",
                "ce:GetDimensionValues",
                "ce:GetReservationUtilization",
                "ce:GetReservationCoverage"
            ],
            "Resource": "*"
        }
    ]
}
EOF
        
        aws iam put-role-policy \
            --role-name $ROLE_NAME \
            --policy-name CostExplorerPolicy \
            --policy-document file://cost-explorer-policy.json
        
        # 역할이 활성화될 때까지 대기
        echo "⏳ IAM 역할 활성화 대기 중..."
        sleep 10
        
        # 임시 파일 정리
        rm -f trust-policy.json cost-explorer-policy.json
    fi
    
    # 역할 ARN 가져오기
    ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
    
    # Lambda 함수 생성
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime python3.12 \
        --role $ROLE_ARN \
        --handler src.lambda_function.lambda_handler \
        --zip-file fileb://lambda-package.zip \
        --timeout 300 \
        --memory-size 512 \
        --environment Variables="{
            SLACK_BOT_TOKEN=$(grep SLACK_BOT_TOKEN .env | cut -d'=' -f2),
            SLACK_CHANNEL=$(grep SLACK_CHANNEL .env | cut -d'=' -f2),
            PUBLIC_DATA_API_KEY=$(grep PUBLIC_DATA_API_KEY .env | cut -d'=' -f2),
            CURRENCY_API_KEY=$(grep CURRENCY_API_KEY .env | cut -d'=' -f2)
        }" \
        --region $REGION
fi

# EventBridge 규칙 생성 (필요시)
RULE_NAME="aws-cost-slack-reporter-schedule"
if ! aws events describe-rule --name $RULE_NAME --region $REGION &> /dev/null; then
    echo "⏰ EventBridge 규칙 생성 중..."
    
    # 규칙 생성 (매일 13:00 KST = 04:00 UTC) - 테스트용
    aws events put-rule \
        --name $RULE_NAME \
        --schedule-expression "cron(0 4 ? * * *)" \
        --description "AWS Cost Slack Reporter - 매일 13:00 KST 실행 (테스트용)" \
        --region $REGION
    
    # Lambda 함수에 권한 부여
    aws lambda add-permission \
        --function-name $FUNCTION_NAME \
        --statement-id EventBridgeInvoke \
        --action lambda:InvokeFunction \
        --principal events.amazonaws.com \
        --source-arn $(aws events describe-rule --name $RULE_NAME --region $REGION --query 'Arn' --output text) \
        --region $REGION
    
    # 타겟 설정
    aws events put-targets \
        --rule $RULE_NAME \
        --targets "Id"="1","Arn"="arn:aws:lambda:$REGION:$(aws sts get-caller-identity --query 'Account' --output text):function:$FUNCTION_NAME" \
        --region $REGION
fi

# 배포 완료
echo "✅ 배포 완료!"
echo "📊 함수 정보:"
aws lambda get-function --function-name $FUNCTION_NAME --region $REGION --query 'Configuration.{FunctionName:FunctionName,Runtime:Runtime,Handler:Handler,Timeout:Timeout,MemorySize:MemorySize}' --output table

echo ""
echo "🧪 테스트 실행:"
echo "aws lambda invoke --function-name $FUNCTION_NAME --region $REGION response.json"

echo ""
echo "📋 다음 단계:"
echo "1. Slack Bot Token과 Channel ID를 설정하세요"
echo "2. 공공데이터포털 API 키를 설정하세요"
echo "3. CurrencyAPI.com API 키를 설정하세요"
echo "4. 테스트 실행으로 정상 작동을 확인하세요" 