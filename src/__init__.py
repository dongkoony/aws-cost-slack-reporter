"""
AWS Cost Slack Reporter
매일 평일(월~금), 공휴일을 제외한 날 한국시간 오후 6시에 AWS 비용 현황을 Slack으로 보고하는 서버리스 Lambda 기반 자동화 서비스
"""

__version__ = "0.1.0"
__author__ = "AWS Cost Slack Reporter Team"

# 주요 모듈들
from . import (cost_explorer, exchange_rate, holiday_checker,
               lambda_function, slack_utils)
from .cost_explorer import get_cost_summary
from .exchange_rate import convert_usd_to_krw, get_exchange_rate
from .holiday_checker import should_send_report
# 주요 함수들
from .lambda_function import lambda_handler
from .slack_utils import send_cost_report, test_slack_connection

__all__ = [
    # 모듈
    "holiday_checker",
    "cost_explorer",
    "exchange_rate",
    "slack_utils",
    "lambda_function",
    # 주요 함수
    "lambda_handler",
    "should_send_report",
    "get_cost_summary",
    "get_exchange_rate",
    "convert_usd_to_krw",
    "send_cost_report",
    "test_slack_connection",
]
