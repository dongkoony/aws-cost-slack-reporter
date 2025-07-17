"""
Lambda 메인 함수 통합 테스트
"""

import json
import os
from unittest.mock import Mock, patch

import pytest

from src.lambda_function import lambda_handler


@pytest.fixture
def mock_lambda_context():
    """Mock Lambda 컨텍스트"""
    context = Mock()
    context.function_name = "aws-cost-slack-reporter-test"
    context.aws_request_id = "test-request-id"
    context.memory_limit_in_mb = 512
    context.get_remaining_time_in_millis.return_value = 30000
    return context


@pytest.fixture
def sample_cost_data():
    """샘플 비용 데이터"""
    return {
        "daily_cost": 15.50,
        "monthly_cost": 465.75,
        "service_breakdown": {"EC2": 8.25, "S3": 3.50, "RDS": 2.75, "CloudWatch": 1.00},
    }


@pytest.fixture
def sample_exchange_rate_data():
    """샘플 환율 데이터"""
    return {
        "rate": 1350.50,
        "formatted_rate": "1 USD = 1,350.50 KRW",
        "last_updated": "2024-01-15 10:30:00",
    }


class TestLambdaFunction:
    """Lambda 메인 함수 테스트 클래스"""

    @patch("src.holiday_checker.should_send_report")
    @patch("src.cost_explorer.get_cost_summary")
    @patch("src.exchange_rate.get_current_exchange_rate_info")
    @patch("src.chart_generator.generate_cost_report_chart")
    @patch("src.slack_utils.send_cost_report")
    def test_lambda_handler_success(
        self,
        mock_send_report,
        mock_generate_chart,
        mock_exchange_rate,
        mock_get_costs,
        mock_should_send,
        mock_lambda_context,
        sample_cost_data,
        sample_exchange_rate_data,
    ):
        """Lambda 핸들러 성공 테스트"""
        # Mock 설정
        mock_should_send.return_value = True
        mock_get_costs.return_value = sample_cost_data
        mock_exchange_rate.return_value = sample_exchange_rate_data
        mock_generate_chart.return_value = b"fake_chart_data"
        mock_send_report.return_value = True

        # Lambda 핸들러 호출
        event = {}
        result = lambda_handler(event, mock_lambda_context)

        # 결과 검증
        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert "비용 리포트 전송 완료" in response_body["message"]

        # Mock 호출 확인
        mock_should_send.assert_called_once()
        mock_get_costs.assert_called_once()
        mock_exchange_rate.assert_called_once()
        mock_generate_chart.assert_called_once()
        mock_send_report.assert_called_once()

    @patch("src.holiday_checker.should_send_report")
    def test_lambda_handler_no_report_day(self, mock_should_send, mock_lambda_context):
        """리포트 전송하지 않는 날 테스트"""
        # Mock 설정 (리포트 전송하지 않는 날)
        mock_should_send.return_value = False

        # Lambda 핸들러 호출
        event = {}
        result = lambda_handler(event, mock_lambda_context)

        # 결과 검증
        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert "리포트 전송 생략" in response_body["message"]

        # Mock 호출 확인
        mock_should_send.assert_called_once()

    @patch("src.holiday_checker.should_send_report")
    @patch("src.cost_explorer.get_cost_summary")
    def test_lambda_handler_cost_error(
        self, mock_get_costs, mock_should_send, mock_lambda_context
    ):
        """비용 조회 에러 처리 테스트"""
        # Mock 설정
        mock_should_send.return_value = True
        mock_get_costs.side_effect = Exception("Cost API Error")

        # Lambda 핸들러 호출
        event = {}
        result = lambda_handler(event, mock_lambda_context)

        # 결과 검증
        assert result["statusCode"] == 500
        response_body = json.loads(result["body"])
        assert "내부 서버 오류" in response_body["error"]

    @patch("src.holiday_checker.should_send_report")
    @patch("src.cost_explorer.get_cost_summary")
    @patch("src.exchange_rate.get_current_exchange_rate_info")
    def test_lambda_handler_exchange_rate_error(
        self,
        mock_exchange_rate,
        mock_get_costs,
        mock_should_send,
        mock_lambda_context,
        sample_cost_data,
    ):
        """환율 조회 에러 처리 테스트"""
        # Mock 설정
        mock_should_send.return_value = True
        mock_get_costs.return_value = sample_cost_data
        mock_exchange_rate.side_effect = Exception("Exchange Rate Error")

        # Lambda 핸들러 호출
        event = {}
        result = lambda_handler(event, mock_lambda_context)

        # 결과 검증
        assert result["statusCode"] == 500
        response_body = json.loads(result["body"])
        assert "내부 서버 오류" in response_body["error"]

    @patch("src.holiday_checker.should_send_report")
    @patch("src.cost_explorer.get_cost_summary")
    @patch("src.exchange_rate.get_current_exchange_rate_info")
    @patch("src.chart_generator.generate_cost_report_chart")
    def test_lambda_handler_chart_error(
        self,
        mock_generate_chart,
        mock_exchange_rate,
        mock_get_costs,
        mock_should_send,
        mock_lambda_context,
        sample_cost_data,
        sample_exchange_rate_data,
    ):
        """차트 생성 에러 처리 테스트"""
        # Mock 설정
        mock_should_send.return_value = True
        mock_get_costs.return_value = sample_cost_data
        mock_exchange_rate.return_value = sample_exchange_rate_data
        mock_generate_chart.side_effect = Exception("Chart Generation Error")

        # Lambda 핸들러 호출
        event = {}
        result = lambda_handler(event, mock_lambda_context)

        # 결과 검증
        assert result["statusCode"] == 500
        response_body = json.loads(result["body"])
        assert "내부 서버 오류" in response_body["error"]

    @patch("src.holiday_checker.should_send_report")
    @patch("src.cost_explorer.get_cost_summary")
    @patch("src.exchange_rate.get_current_exchange_rate_info")
    @patch("src.chart_generator.generate_cost_report_chart")
    @patch("src.slack_utils.send_cost_report")
    def test_lambda_handler_slack_error(
        self,
        mock_send_report,
        mock_generate_chart,
        mock_exchange_rate,
        mock_get_costs,
        mock_should_send,
        mock_lambda_context,
        sample_cost_data,
        sample_exchange_rate_data,
    ):
        """Slack 전송 에러 처리 테스트"""
        # Mock 설정
        mock_should_send.return_value = True
        mock_get_costs.return_value = sample_cost_data
        mock_exchange_rate.return_value = sample_exchange_rate_data
        mock_generate_chart.return_value = b"fake_chart_data"
        mock_send_report.return_value = False  # Slack 전송 실패

        # Lambda 핸들러 호출
        event = {}
        result = lambda_handler(event, mock_lambda_context)

        # 결과 검증
        assert result["statusCode"] == 500
        response_body = json.loads(result["body"])
        assert "비용 리포트 전송 실패" in response_body["error"]

    @patch("src.holiday_checker.should_send_report")
    @patch("src.cost_explorer.get_cost_summary")
    @patch("src.exchange_rate.get_current_exchange_rate_info")
    @patch("src.chart_generator.generate_cost_report_chart")
    @patch("src.slack_utils.send_cost_report")
    def test_lambda_handler_with_debug_mode(
        self,
        mock_send_report,
        mock_generate_chart,
        mock_exchange_rate,
        mock_get_costs,
        mock_should_send,
        mock_lambda_context,
        sample_cost_data,
        sample_exchange_rate_data,
    ):
        """디버그 모드 테스트"""
        # 디버그 모드 활성화
        original_debug = os.environ.get("DEBUG_MODE")
        os.environ["DEBUG_MODE"] = "true"

        try:
            # Mock 설정
            mock_should_send.return_value = True
            mock_get_costs.return_value = sample_cost_data
            mock_exchange_rate.return_value = sample_exchange_rate_data
            mock_generate_chart.return_value = b"fake_chart_data"
            mock_send_report.return_value = True

            # Lambda 핸들러 호출
            event = {}
            result = lambda_handler(event, mock_lambda_context)

            # 결과 검증
            assert result["statusCode"] == 200
            response_body = json.loads(result["body"])
            assert "비용 리포트 전송 완료" in response_body["message"]

        finally:
            # 원래 설정 복원
            if original_debug:
                os.environ["DEBUG_MODE"] = original_debug
            else:
                os.environ.pop("DEBUG_MODE", None)

    def test_lambda_handler_invalid_event(self, mock_lambda_context):
        """잘못된 이벤트 처리 테스트"""
        # 잘못된 이벤트
        event = None

        # Lambda 핸들러 호출
        result = lambda_handler(event, mock_lambda_context)

        # 결과 검증
        assert result["statusCode"] == 500
        response_body = json.loads(result["body"])
        # 실제로는 Slack 전송 실패로 인해 "비용 리포트 전송 실패" 메시지가 반환됨
        assert "비용 리포트 전송 실패" in response_body["error"]

    @patch("src.holiday_checker.should_send_report")
    @patch("src.cost_explorer.get_cost_summary")
    @patch("src.exchange_rate.get_current_exchange_rate_info")
    @patch("src.chart_generator.generate_cost_report_chart")
    @patch("src.slack_utils.send_cost_report")
    def test_lambda_handler_slack_exception(
        self,
        mock_send_report,
        mock_generate_chart,
        mock_exchange_rate,
        mock_get_costs,
        mock_should_send,
        mock_lambda_context,
        sample_cost_data,
        sample_exchange_rate_data,
    ):
        """Slack 전송 예외 처리 테스트"""
        # Mock 설정
        mock_should_send.return_value = True
        mock_get_costs.return_value = sample_cost_data
        mock_exchange_rate.return_value = sample_exchange_rate_data
        mock_generate_chart.return_value = b"fake_chart_data"
        mock_send_report.side_effect = Exception("Slack API Error")

        # Lambda 핸들러 호출
        event = {}
        result = lambda_handler(event, mock_lambda_context)

        # 결과 검증
        assert result["statusCode"] == 500
        response_body = json.loads(result["body"])
        assert "내부 서버 오류" in response_body["error"]
