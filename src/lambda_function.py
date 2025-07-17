"""
AWS Cost Slack Reporter - Lambda 함수 메인 핸들러
매일 평일(월~금), 공휴일을 제외한 날 한국시간 오후 6시에 AWS 비용 현황을 Slack으로 보고합니다.
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from dotenv import load_dotenv

# 로컬 개발 환경에서 .env 파일 로드
if os.path.exists(".env"):
    load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# KST 시간대 설정
KST = timezone(timedelta(hours=9))


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda 함수 메인 핸들러

    Args:
        event: Lambda 이벤트 데이터
        context: Lambda 컨텍스트

    Returns:
        Lambda 응답 딕셔너리
    """
    try:
        logger.info("AWS Cost Slack Reporter 시작")
        
        # 실행 시점 시간 정보 로깅
        utc_now = datetime.now(timezone.utc)
        kst_now = datetime.now(KST)
        logger.info(f"실행 시점 UTC: {utc_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info(f"실행 시점 KST: {kst_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info(f"EventBridge 이벤트: {json.dumps(event, indent=2)}")

        # Lambda 컨텍스트 정보 로깅
        if context:
            logger.info(f"Lambda 함수: {context.function_name}")
            logger.info(f"요청 ID: {context.aws_request_id}")
            logger.info(f"메모리 제한: {context.memory_limit_in_mb}MB")
            logger.info(f"남은 시간: {context.get_remaining_time_in_millis()}ms")

        # 공휴일 체크
        try:
            from src.holiday_checker import should_send_report
        except ImportError:
            from holiday_checker import should_send_report

        logger.info("공휴일 체크 시작...")
        should_send = should_send_report()
        logger.info(f"리포트 전송 여부: {should_send}")

        if not should_send:
            logger.info("오늘은 리포트 전송 대상이 아닙니다 (주말 또는 공휴일)")
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": "리포트 전송 생략 (주말 또는 공휴일)",
                        "timestamp": datetime.now(KST).isoformat(),
                    }
                ),
            }

        # 비용 데이터 조회
        try:
            from src.cost_explorer import get_cost_summary
        except ImportError:
            from cost_explorer import get_cost_summary

        cost_summary = get_cost_summary()
        daily_cost = cost_summary["daily_cost"]
        monthly_cost = cost_summary["monthly_cost"]
        service_breakdown = cost_summary["service_breakdown"]

        logger.info(
            f"비용 데이터 조회 완료: 전일 ${daily_cost:.2f}, 이번달 누적 ${monthly_cost:.2f}"
        )

        # 환율 조회 및 통화 변환
        try:
            from src.exchange_rate import (get_cost_in_both_currencies,
                                        get_current_exchange_rate_info)
        except ImportError:
            from exchange_rate import (get_cost_in_both_currencies,
                                    get_current_exchange_rate_info)

        daily_costs = get_cost_in_both_currencies(daily_cost)
        monthly_costs = get_cost_in_both_currencies(monthly_cost)
        exchange_info = get_current_exchange_rate_info()

        logger.info(f"환율 변환 완료: {exchange_info['formatted_rate']}")

        # Slack으로 리포트 전송 (차트 없이 텍스트만)
        try:
            from src.slack_utils import send_cost_report
        except ImportError:
            from slack_utils import send_cost_report

        success = send_cost_report(
            daily_cost_usd=daily_costs["usd"],
            daily_cost_krw=daily_costs["krw"],
            monthly_cost_usd=monthly_costs["usd"],
            monthly_cost_krw=monthly_costs["krw"],
            exchange_rate=exchange_info["rate"],
            service_costs=service_breakdown,
        )

        if success:
            logger.info("비용 리포트 전송 성공")
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": "비용 리포트 전송 완료",
                        "daily_cost_usd": daily_costs["usd"],
                        "monthly_cost_usd": monthly_costs["usd"],
                        "exchange_rate": exchange_info["rate"],
                        "timestamp": datetime.now(KST).isoformat(),
                    }
                ),
            }
        else:
            logger.error("비용 리포트 전송 실패")
            return {
                "statusCode": 500,
                "body": json.dumps(
                    {
                        "error": "비용 리포트 전송 실패",
                        "timestamp": datetime.now(KST).isoformat(),
                    }
                ),
            }

    except Exception as e:
        logger.error(f"Lambda 함수 실행 중 예상치 못한 오류: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"error": "내부 서버 오류", "timestamp": datetime.now(KST).isoformat()}
            ),
        }


def test_lambda_locally():
    """
    로컬에서 Lambda 함수 테스트
    """
    print("🧪 로컬 Lambda 함수 테스트 시작")
    print("=" * 50)

    # 현재 시간 정보 출력
    utc_now = datetime.now(timezone.utc)
    kst_now = datetime.now(KST)
    print(f"테스트 시점 UTC: {utc_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"테스트 시점 KST: {kst_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    # 테스트 이벤트 생성 (EventBridge 스케줄러 시뮬레이션)
    test_event = {
        "version": "0",
        "id": "test-event-id",
        "detail-type": "Scheduled Event",
        "source": "aws.events",
        "account": "123456789012",
        "time": utc_now.isoformat(),
        "region": "ap-northeast-2",
        "resources": ["arn:aws:events:ap-northeast-2:123456789012:rule/test-rule"],
        "detail": {}
    }

    # Mock Lambda 컨텍스트
    class MockContext:
        def __init__(self):
            self.function_name = "aws-cost-slack-reporter-local"
            self.aws_request_id = "test-request-id"
            self.memory_limit_in_mb = 512
            self.get_remaining_time_in_millis = lambda: 30000

    test_context = MockContext()

    # 함수 실행
    result = lambda_handler(test_event, test_context)

    print(f"결과: {json.dumps(result, indent=2, ensure_ascii=False)}")
    print("=" * 50)

    return result


def validate_environment():
    """
    환경 변수 설정 검증
    """
    print("🔧 환경 변수 검증")
    print("=" * 30)

    required_vars = [
        "SLACK_BOT_TOKEN",
        "SLACK_CHANNEL",
        "PUBLIC_DATA_API_KEY",
        "CURRENCY_API_KEY",
    ]

    missing_vars = []

    for var in required_vars:
        value = os.environ.get(var)
        if value:
            # 민감한 정보는 마스킹
            if "TOKEN" in var or "KEY" in var:
                masked_value = (
                    value[:4] + "***" + value[-4:] if len(value) > 8 else "***"
                )
                print(f"✅ {var}: {masked_value}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: 설정되지 않음")
            missing_vars.append(var)

    if missing_vars:
        print(f"\n⚠️  누락된 환경 변수: {', '.join(missing_vars)}")
        return False
    else:
        print("\n✅ 모든 필수 환경 변수가 설정되었습니다.")
        return True


def test_connections():
    """
    외부 서비스 연결 테스트
    """
    print("\n🔗 외부 서비스 연결 테스트")
    print("=" * 30)

    # Slack 연결 테스트
    try:
        try:
            from src.slack_utils import test_slack_connection
        except ImportError:
            from slack_utils import test_slack_connection

        if test_slack_connection():
            print("✅ Slack 연결 성공")
        else:
            print("❌ Slack 연결 실패")
    except Exception as e:
        print(f"❌ Slack 연결 테스트 실패: {e}")

    # 공공데이터포털 API 테스트
    try:
        try:
            from src.holiday_checker import check_holiday, should_send_report
        except ImportError:
            from holiday_checker import check_holiday, should_send_report

        api_key = os.environ.get("PUBLIC_DATA_API_KEY")
        if api_key:
            # 오늘 날짜로 테스트
            today = datetime.now(KST).strftime("%Y%m%d")
            is_holiday = check_holiday(today, api_key)
            print(f"✅ 공공데이터포털 API 연결 성공 (오늘 {today} 공휴일: {is_holiday})")
            
            # 리포트 전송 여부 테스트
            should_send = should_send_report()
            print(f"✅ 리포트 전송 여부: {should_send}")
        else:
            print("❌ PUBLIC_DATA_API_KEY가 설정되지 않음")
    except Exception as e:
        print(f"❌ 공공데이터포털 API 연결 테스트 실패: {e}")

    # 환율 API 테스트
    try:
        try:
            from src.exchange_rate import get_exchange_rate
        except ImportError:
            from exchange_rate import get_exchange_rate

        rate = get_exchange_rate("USD", "KRW")
        print(f"✅ 환율 API 연결 성공 (1 USD = {rate:.2f} KRW)")
    except Exception as e:
        print(f"❌ 환율 API 연결 테스트 실패: {e}")


if __name__ == "__main__":
    # 로컬 실행 시 테스트
    print("🚀 AWS Cost Slack Reporter - 로컬 테스트 모드")
    print("=" * 60)

    # 환경 변수 검증
    if not validate_environment():
        print("\n❌ 환경 변수 설정이 완료되지 않았습니다.")
        print("💡 .env 파일을 확인하고 필요한 환경 변수를 설정하세요.")
        exit(1)

    # 연결 테스트
    test_connections()

    # Lambda 함수 테스트
    print("\n🧪 Lambda 함수 테스트")
    test_lambda_locally()
