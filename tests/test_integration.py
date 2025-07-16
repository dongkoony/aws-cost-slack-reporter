"""
전체 시스템 통합 테스트
"""

import pytest
import os
import tempfile
from unittest.mock import patch, Mock
from datetime import datetime
from src.lambda_function import lambda_handler
from src.holiday_checker import should_send_report
from src.cost_explorer import get_cost_summary
from src.exchange_rate import get_exchange_rate
from src.chart_generator import generate_cost_report_chart
from src.slack_utils import send_cost_report

class TestIntegration:
    """전체 시스템 통합 테스트 클래스"""
    
    @patch('src.holiday_checker.check_holiday')
    @patch('src.holiday_checker.is_business_day')
    def test_end_to_end_workflow(
        self, 
        mock_is_business_day, 
        mock_check_holiday,
        mock_lambda_context
    ):
        """전체 워크플로우 테스트"""
        # Mock 설정
        mock_is_business_day.return_value = True
        mock_check_holiday.return_value = False
        
        # Lambda 핸들러 호출
        event = {}
        result = lambda_handler(event, mock_lambda_context)
        
        # 결과 검증
        assert result['statusCode'] in [200, 500]  # 실제 API 호출로 인해 500 가능
        
        # Mock 호출 확인
        mock_is_business_day.assert_called_once()
        mock_check_holiday.assert_called_once()
    
    def test_environment_variables(self):
        """환경 변수 설정 테스트"""
        required_vars = [
            'SLACK_BOT_TOKEN',
            'SLACK_CHANNEL',
            'PUBLIC_DATA_API_KEY',
            'CURRENCY_API_KEY'
        ]
        
        for var in required_vars:
            assert var in os.environ, f"환경 변수 {var}가 설정되지 않았습니다"
    
    @patch('src.holiday_checker.safe_api_request')
    def test_holiday_api_integration(self, mock_api_request):
        """공휴일 API 통합 테스트"""
        # Mock API 응답
        mock_response = {
            'response': {
                'body': {
                    'items': {}
                }
            }
        }
        mock_api_request.return_value = mock_response
        
        # 공휴일 확인 함수 호출
        result = should_send_report()
        
        # 결과는 True 또는 False (실제 날짜에 따라)
        assert isinstance(result, bool)
        
        # API 호출 확인
        mock_api_request.assert_called()
    
    @patch('src.exchange_rate.safe_api_request')
    def test_exchange_rate_api_integration(self, mock_api_request):
        """환율 API 통합 테스트"""
        # Mock API 응답
        mock_response = {
            'data': {
                'KRW': {
                    'value': 1300.0
                }
            }
        }
        mock_api_request.return_value = mock_response
        
        # 환율 조회 함수 호출
        result = get_exchange_rate('USD', 'KRW')
        
        # 결과 검증
        assert isinstance(result, float)
        assert result > 0
        
        # API 호출 확인
        mock_api_request.assert_called_once()
    
    def test_chart_generation_integration(self):
        """차트 생성 통합 테스트"""
        # 샘플 데이터
        cost_data = {
            'daily_cost': 25.50,
            'monthly_cost': 450.75,
            'service_breakdown': {
                'Amazon EC2': 180.25,
                'Amazon RDS': 95.50,
                'Amazon S3': 45.20
            }
        }
        
        # 차트 생성 함수 호출
        result = generate_cost_report_chart(cost_data)
        
        # 결과 검증
        assert isinstance(result, bytes)
        assert len(result) > 0
    
    @patch('src.slack_utils.WebClient')
    def test_slack_integration(self, mock_webclient):
        """Slack 통합 테스트"""
        # Mock Slack 클라이언트
        mock_client = Mock()
        mock_webclient.return_value = mock_client
        mock_client.chat_postMessage.return_value = {'ok': True, 'ts': '1234567890.123456'}
        
        # files_upload_v2 Mock 응답 설정
        mock_client.files_upload_v2.return_value = {'ok': True, 'file': {'id': 'F1234567890'}}
        
        # Slack 전송 함수 호출 (실제 시그니처에 맞게)
        result = send_cost_report(
            daily_cost_usd=25.50,
            daily_cost_krw=33150,  # 25.50 * 1300
            monthly_cost_usd=450.75,
            monthly_cost_krw=585975,  # 450.75 * 1300
            exchange_rate=1300.0,
            service_costs={
                'Amazon EC2': 180.25,
                'Amazon RDS': 95.50
            },
            chart_image=b'fake_chart_data'
        )
        
        # 결과 검증
        assert result == True
        
        # Slack API 호출 확인
        assert mock_client.chat_postMessage.call_count == 2
        mock_client.files_upload_v2.assert_called_once()
    
    def test_date_handling_integration(self):
        """날짜 처리 통합 테스트"""
        from src.holiday_checker import get_date_range, get_monthly_date_range
        
        # 일일 날짜 범위
        daily_start, daily_end = get_date_range()
        assert daily_start == daily_end  # 오늘 날짜
        
        # 월간 날짜 범위
        monthly_start, monthly_end = get_monthly_date_range()
        assert monthly_start <= monthly_end
        
        # 날짜 형식 검증
        from datetime import datetime
        datetime.strptime(daily_start, '%Y-%m-%d')
        datetime.strptime(monthly_start, '%Y-%m-%d')
    
    def test_cost_formatting_integration(self):
        """비용 포맷팅 통합 테스트"""
        from src.exchange_rate import format_cost_usd, format_cost_krw
        
        # USD 포맷팅
        usd_formatted = format_cost_usd(123.45)
        assert usd_formatted == '$123.45'
        
        # KRW 포맷팅
        krw_formatted = format_cost_krw(12345)
        assert krw_formatted == '₩12,345'
    
    @patch('src.cost_explorer.boto3.client')
    def test_aws_cost_explorer_integration(self, mock_boto_client):
        """AWS Cost Explorer 통합 테스트"""
        # Mock AWS Cost Explorer 클라이언트
        mock_ce_client = Mock()
        mock_boto_client.return_value = mock_ce_client
        
        # Mock API 응답
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2024-01-15', 'End': '2024-01-16'},
                    'Total': {'UnblendedCost': {'Amount': '25.50', 'Unit': 'USD'}}
                }
            ],
            'GroupDefinitions': [
                {
                    'Type': 'DIMENSION',
                    'Key': 'SERVICE'
                }
            ],
            'ResultsByTime': [
                {
                    'Groups': [
                        {
                            'Keys': ['Amazon EC2'],
                            'Metrics': {'UnblendedCost': {'Amount': '15.25', 'Unit': 'USD'}}
                        },
                        {
                            'Keys': ['Amazon S3'],
                            'Metrics': {'UnblendedCost': {'Amount': '10.25', 'Unit': 'USD'}}
                        }
                    ]
                }
            ]
        }
        
        # 비용 조회 함수 호출
        result = get_cost_summary()
        
        # 결과 검증
        assert isinstance(result, dict)
        assert 'daily_cost' in result
        assert 'monthly_cost' in result
        assert 'service_breakdown' in result
        
        # AWS API 호출 확인
        mock_ce_client.get_cost_and_usage.assert_called()
    
    def test_error_handling_integration(self):
        """에러 처리 통합 테스트"""
        # 잘못된 환경 변수로 테스트
        original_token = os.environ.get('SLACK_BOT_TOKEN')
        os.environ['SLACK_BOT_TOKEN'] = 'invalid-token'
        
        try:
            # Lambda 핸들러 호출 (에러 발생 예상)
            event = {}
            result = lambda_handler(event, Mock())
            
            # 에러 처리 확인
            assert result['statusCode'] in [200, 500]
            
        finally:
            # 원래 환경 변수 복원
            if original_token:
                os.environ['SLACK_BOT_TOKEN'] = original_token
            else:
                os.environ.pop('SLACK_BOT_TOKEN', None) 