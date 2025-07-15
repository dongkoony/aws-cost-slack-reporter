"""
환율 변환 모듈 테스트
"""

import pytest
from unittest.mock import patch, Mock
from src.exchange_rate import (
    get_exchange_rate,
    convert_usd_to_krw,
    format_cost_krw,
    get_cost_in_both_currencies,
    get_current_exchange_rate_info
)

class TestExchangeRate:
    """환율 변환 모듈 테스트 클래스"""
    
    @patch('src.exchange_rate.safe_api_request')
    def test_get_exchange_rate_success(self, mock_api_request):
        """환율 조회 성공 테스트"""
        # Mock API 응답
        mock_response = {
            'data': {
                'KRW': {
                    'value': 1300.50
                }
            }
        }
        mock_api_request.return_value = mock_response
        
        result = get_exchange_rate('USD', 'KRW')
        assert result == 1300.50
        
        # API 호출 확인
        mock_api_request.assert_called_once()
    
    @patch('src.exchange_rate.safe_api_request')
    def test_get_exchange_rate_no_data(self, mock_api_request):
        """환율 데이터 없음 테스트"""
        # Mock API 응답 (데이터 없음)
        mock_response = {
            'data': {}
        }
        mock_api_request.return_value = mock_response
        
        result = get_exchange_rate('USD', 'KRW')
        assert result == 1300.0  # 기본값
    
    @patch('src.exchange_rate.safe_api_request')
    def test_get_exchange_rate_api_error(self, mock_api_request):
        """API 에러 처리 테스트"""
        # API 에러 시뮬레이션
        mock_api_request.side_effect = Exception("API Error")
        
        result = get_exchange_rate('USD', 'KRW')
        assert result == 1300.0  # 기본값
    
    def test_get_exchange_rate_no_api_key(self):
        """API 키 없을 때 처리 테스트"""
        import os
        
        # API 키 제거
        original_key = os.environ.get('CURRENCY_API_KEY')
        if 'CURRENCY_API_KEY' in os.environ:
            del os.environ['CURRENCY_API_KEY']
        
        try:
            result = get_exchange_rate('USD', 'KRW')
            assert result == 1300.0  # 기본값
        finally:
            # 원래 API 키 복원
            if original_key:
                os.environ['CURRENCY_API_KEY'] = original_key
    
    @patch('src.exchange_rate.get_exchange_rate')
    def test_convert_usd_to_krw(self, mock_get_rate):
        """USD to KRW 변환 테스트"""
        mock_get_rate.return_value = 1300.0
        
        result = convert_usd_to_krw(100.0)
        assert result == 130000.0
        
        mock_get_rate.assert_called_once_with('USD', 'KRW')
    
    @patch('src.exchange_rate.get_exchange_rate')
    def test_convert_usd_to_krw_error(self, mock_get_rate):
        """환율 변환 에러 처리 테스트"""
        mock_get_rate.side_effect = Exception("Rate Error")
        
        result = convert_usd_to_krw(100.0)
        assert result == 130000.0  # 기본 환율 사용
    
    def test_format_cost_krw(self):
        """KRW 포맷팅 테스트"""
        # 1000원 미만
        assert format_cost_krw(500) == "₩500"
        
        # 1000원 이상
        assert format_cost_krw(1500) == "₩1,500"
        assert format_cost_krw(15000) == "₩15,000"
        assert format_cost_krw(150000) == "₩150,000"
    
    @patch('src.exchange_rate.convert_usd_to_krw')
    @patch('src.exchange_rate.get_exchange_rate')
    def test_get_cost_in_both_currencies(self, mock_get_rate, mock_convert):
        """이중 통화 비용 조회 테스트"""
        mock_get_rate.return_value = 1300.0
        mock_convert.return_value = 130000.0
        
        result = get_cost_in_both_currencies(100.0)
        
        expected = {
            'usd': 100.0,
            'krw': 130000.0,
            'exchange_rate': 1300.0,
            'formatted_usd': '$100.00',
            'formatted_krw': '₩130,000'
        }
        
        assert result == expected
    
    @patch('src.exchange_rate.convert_usd_to_krw')
    @patch('src.exchange_rate.get_exchange_rate')
    def test_get_cost_in_both_currencies_error(self, mock_get_rate, mock_convert):
        """이중 통화 비용 조회 에러 처리 테스트"""
        mock_get_rate.side_effect = Exception("Rate Error")
        mock_convert.side_effect = Exception("Convert Error")
        
        result = get_cost_in_both_currencies(100.0)
        
        # 에러 시 기본값 반환
        assert result['usd'] == 100.0
        assert result['krw'] == 130000.0  # 100 * 1300
        assert result['exchange_rate'] == 1300.0
    
    @patch('src.exchange_rate.get_exchange_rate')
    def test_get_current_exchange_rate_info(self, mock_get_rate):
        """현재 환율 정보 조회 테스트"""
        mock_get_rate.return_value = 1300.50
        
        result = get_current_exchange_rate_info()
        
        assert result['rate'] == 1300.50
        assert result['base_currency'] == 'USD'
        assert result['target_currency'] == 'KRW'
        assert 'timestamp' in result
        assert result['formatted_rate'] == '1 USD = 1300.50 KRW'
    
    @patch('src.exchange_rate.get_exchange_rate')
    def test_get_current_exchange_rate_info_error(self, mock_get_rate):
        """현재 환율 정보 조회 에러 처리 테스트"""
        mock_get_rate.side_effect = Exception("Rate Error")
        
        result = get_current_exchange_rate_info()
        
        assert result['rate'] == 1300.0  # 기본값
        assert result['formatted_rate'] == '1 USD = 1,300.00 KRW (기본값)'
    
    def test_format_cost_usd(self):
        """USD 포맷팅 테스트"""
        from src.exchange_rate import format_cost_usd
        
        # 1달러 미만
        assert format_cost_usd(0.1234) == "$0.1234"
        
        # 1달러 이상
        assert format_cost_usd(1.0) == "$1.00"
        assert format_cost_usd(10.5) == "$10.50"
        assert format_cost_usd(100.75) == "$100.75" 