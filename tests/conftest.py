"""
pytest 설정 파일
테스트 환경 설정 및 공통 fixture들을 관리합니다.
"""

import os
import sys
from unittest.mock import Mock

import pytest
from dotenv import load_dotenv

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 테스트용 .env 파일 로드 (존재하는 경우)
test_env_path = os.path.join(os.path.dirname(__file__), "..", ".env.test")
if os.path.exists(test_env_path):
    load_dotenv(test_env_path)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """테스트 환경 설정"""
    # 테스트용 환경 변수 설정
    test_env_vars = {
        "SLACK_BOT_TOKEN": "xoxb-test-token-1234567890",
        "SLACK_CHANNEL": "C1234567890",
        "PUBLIC_DATA_API_KEY": "test-public-data-api-key",
        "CURRENCY_API_KEY": "test-currency-api-key",
        "AWS_DEFAULT_REGION": "ap-northeast-2",
        "LOG_LEVEL": "DEBUG",
        "DEBUG_MODE": "true",
    }

    # 기존 환경 변수 백업
    original_env = {}
    for key in test_env_vars.keys():
        original_env[key] = os.environ.get(key)

    # 테스트용 환경 변수 설정
    for key, value in test_env_vars.items():
        os.environ[key] = value

    yield

    # 테스트 후 원래 환경 변수 복원
    for key, value in original_env.items():
        if value is not None:
            os.environ[key] = value
        else:
            os.environ.pop(key, None)


@pytest.fixture
def mock_aws_credentials():
    """AWS 자격 증명 Mock"""
    os.environ["AWS_ACCESS_KEY_ID"] = "test-access-key"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "test-secret-key"
    os.environ["AWS_DEFAULT_REGION"] = "ap-northeast-2"

    yield

    # 정리
    for key in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]:
        os.environ.pop(key, None)


@pytest.fixture
def mock_lambda_context():
    """Lambda 컨텍스트 Mock"""
    context = Mock()
    context.function_name = "aws-cost-slack-reporter-test"
    context.aws_request_id = "test-request-id-12345"
    context.memory_limit_in_mb = 512
    context.get_remaining_time_in_millis.return_value = 30000
    return context


@pytest.fixture
def sample_cost_data():
    """샘플 비용 데이터"""
    return {
        "daily_cost": 25.50,
        "monthly_cost": 450.75,
        "service_breakdown": {
            "Amazon EC2": 180.25,
            "Amazon RDS": 95.50,
            "Amazon S3": 45.20,
            "Amazon CloudWatch": 15.30,
            "AWS Lambda": 12.45,
            "Amazon DynamoDB": 8.75,
            "Amazon API Gateway": 5.20,
            "Amazon Route 53": 3.50,
            "AWS Certificate Manager": 2.00,
            "Amazon CloudFront": 1.50,
        },
        "date_range": {
            "daily": ("2024-01-15", "2024-01-15"),
            "monthly": ("2024-01-01", "2024-01-15"),
        },
    }


@pytest.fixture
def sample_exchange_rate_data():
    """샘플 환율 데이터"""
    return {
        "rate": 1300.0,
        "base_currency": "USD",
        "target_currency": "KRW",
        "formatted_rate": "1 USD = 1,300.00 KRW",
    }


@pytest.fixture
def sample_holiday_data():
    """샘플 공휴일 데이터"""
    return {
        "20241225": True,  # 크리스마스
        "20241226": False,  # 평일
        "20241228": False,  # 평일
        "20241229": False,  # 토요일
        "20241230": False,  # 평일
    }
