"""
AWS Cost Explorer API 모듈
AWS Cost Explorer API를 사용하여 비용 데이터를 조회합니다.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError

# 로깅 설정
logger = logging.getLogger(__name__)

# KST 시간대 설정
KST = timezone(timedelta(hours=9))


def get_aws_client(service_name: str):
    """AWS 클라이언트 안전한 초기화"""
    try:
        return boto3.client(service_name)
    except Exception as e:
        logger.error(f"AWS 클라이언트 초기화 실패: {service_name}")
        raise


def get_cost_data(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    AWS Cost Explorer API를 통한 비용 데이터 조회

    Args:
        start_date: 시작 날짜 (YYYY-MM-DD)
        end_date: 종료 날짜 (YYYY-MM-DD)

    Returns:
        비용 데이터 딕셔너리
    """
    ce_client = get_aws_client("ce")

    try:
        # AWS Cost Explorer는 종료일이 시작일보다 뒤에 있어야 함
        # 하루 데이터 조회 시에는 다음날을 종료일로 설정
        # 시작일과 종료일이 같으면 종료일에 1일 추가
        if start_date == end_date:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            actual_end_date = end_date_obj.strftime("%Y-%m-%d")
        else:
            actual_end_date = end_date

        response = ce_client.get_cost_and_usage(
            TimePeriod={"Start": start_date, "End": actual_end_date},
            Granularity="DAILY",
            Metrics=["BlendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )

        logger.info(f"비용 데이터 조회 성공: {start_date} ~ {end_date}")
        return response

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        logger.error(f"AWS Cost Explorer API 에러: {error_code}")
        raise
    except Exception:
        logger.exception("비용 데이터 조회 실패")
        return {}


def parse_cost_data(cost_data: Dict[str, Any]) -> Dict[str, float]:
    """
    Cost Explorer API 응답을 파싱하여 서비스별 비용 추출

    Args:
        cost_data: Cost Explorer API 응답

    Returns:
        서비스별 비용 딕셔너리
    """
    service_costs = {}

    try:
        for result in cost_data.get("ResultsByTime", []):
            for group in result.get("Groups", []):
                service_name = group["Keys"][0]
                cost_amount = float(group["Metrics"]["BlendedCost"]["Amount"])

                if service_name in service_costs:
                    service_costs[service_name] += cost_amount
                else:
                    service_costs[service_name] = cost_amount

        logger.info(f"비용 데이터 파싱 완료: {len(service_costs)}개 서비스")
        return service_costs

    except Exception as e:
        logger.error(f"비용 데이터 파싱 실패: {e}")
        raise


def get_daily_cost(start_date: str, end_date: str) -> float:
    """
    특정 기간의 일일 총 비용 조회

    Args:
        start_date: 시작 날짜 (YYYY-MM-DD)
        end_date: 종료 날짜 (YYYY-MM-DD)

    Returns:
        일일 총 비용 (USD)
    """
    try:
        cost_data = get_cost_data(start_date, end_date)
        service_costs = parse_cost_data(cost_data)

        total_cost = sum(service_costs.values())
        logger.info(f"일일 총 비용: ${total_cost:.2f}")

        return total_cost

    except Exception as e:
        logger.error(f"일일 비용 조회 실패: {e}")
        return 0.0


def get_monthly_cost(start_date: str, end_date: str) -> float:
    """
    특정 기간의 월간 총 비용 조회

    Args:
        start_date: 시작 날짜 (YYYY-MM-DD)
        end_date: 종료 날짜 (YYYY-MM-DD)

    Returns:
        월간 총 비용 (USD)
    """
    try:
        cost_data = get_cost_data(start_date, end_date)
        service_costs = parse_cost_data(cost_data)

        total_cost = sum(service_costs.values())
        logger.info(f"월간 총 비용: ${total_cost:.2f}")

        return total_cost

    except Exception as e:
        logger.error(f"월간 비용 조회 실패: {e}")
        return 0.0


def get_service_breakdown(start_date: str, end_date: str) -> Dict[str, float]:
    """
    서비스별 비용 내역 조회

    Args:
        start_date: 시작 날짜 (YYYY-MM-DD)
        end_date: 종료 날짜 (YYYY-MM-DD)

    Returns:
        서비스별 비용 딕셔너리
    """
    try:
        cost_data = get_cost_data(start_date, end_date)
        service_costs = parse_cost_data(cost_data)

        # 비용 순으로 정렬
        sorted_costs = dict(
            sorted(service_costs.items(), key=lambda x: x[1], reverse=True)
        )

        logger.info(f"서비스별 비용 내역 조회 완료: {len(sorted_costs)}개 서비스")
        return sorted_costs

    except Exception as e:
        logger.error(f"서비스별 비용 내역 조회 실패: {e}")
        return {}


def format_cost_usd(amount: float) -> str:
    """
    USD 비용을 포맷팅

    Args:
        amount: 비용 금액

    Returns:
        포맷팅된 비용 문자열
    """
    if amount < 1:
        return f"${amount:.4f}"
    else:
        return f"${amount:.2f}"


def get_cost_summary() -> Dict[str, Any]:
    """
    금일과 이번 달 비용 요약 조회
    (오후 6시 현재까지의 사용 비용)

    Returns:
        비용 요약 딕셔너리
    """
    from .holiday_checker import get_date_range, get_monthly_date_range

    try:
        # 금일 비용 (현재까지)
        today_start, today_end = get_date_range()
        daily_cost = get_daily_cost(today_start, today_end)

        # 이번 달 누적 비용 (금일까지)
        month_start, month_end = get_monthly_date_range()
        monthly_cost = get_monthly_cost(month_start, month_end)

        # 서비스별 내역 (이번 달 누적)
        service_breakdown = get_service_breakdown(month_start, month_end)

        summary = {
            "daily_cost": daily_cost,
            "monthly_cost": monthly_cost,
            "service_breakdown": service_breakdown,
            "date_range": {
                "daily": (today_start, today_end),
                "monthly": (month_start, month_end),
            },
        }

        logger.info(
            f"비용 요약 완료: 금일 ${daily_cost:.2f}, 이번달 누적 ${monthly_cost:.2f}"
        )
        return summary

    except Exception as e:
        logger.error(f"비용 요약 조회 실패: {e}")
        return {
            "daily_cost": 0.0,
            "monthly_cost": 0.0,
            "service_breakdown": {},
            "date_range": {"daily": ("", ""), "monthly": ("", "")},
        }
