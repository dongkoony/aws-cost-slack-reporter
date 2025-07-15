"""
공휴일 확인 모듈 테스트
"""

import pytest
from unittest.mock import patch, Mock
from datetime import datetime, timezone, timedelta
from src.holiday_checker import (
    check_holiday,
    is_business_day,
    should_send_report,
    get_date_range,
    get_monthly_date_range
)

class TestHolidayChecker:
    """공휴일 확인 모듈 테스트 클래스"""
    
    def test_is_business_day(self):
        """평일 확인 테스트"""
        # 월요일 (평일)
        monday = datetime(2024, 1, 15)  # 월요일
        assert is_business_day(monday) == True
        
        # 금요일 (평일)
        friday = datetime(2024, 1, 19)  # 금요일
        assert is_business_day(friday) == True
        
        # 토요일 (주말)
        saturday = datetime(2024, 1, 20)  # 토요일
        assert is_business_day(saturday) == False
        
        # 일요일 (주말)
        sunday = datetime(2024, 1, 21)  # 일요일
        assert is_business_day(sunday) == False
    
    @patch('src.holiday_checker.safe_api_request')
    def test_check_holiday_success(self, mock_api_request):
        """공휴일 확인 성공 테스트"""
        # Mock API 응답 (수정된 응답 구조에 맞게)
        mock_response = {
            'response': {
                'header': {
                    'resultCode': '00',
                    'resultMsg': 'NORMAL SERVICE.'
                },
                'body': {
                    'totalCount': 1,
                    'items': {
                        'item': {
                            'locdate': 20241225,
                            'dateName': '크리스마스',
                            'isHoliday': 'Y'
                        }
                    }
                }
            }
        }
        mock_api_request.return_value = mock_response
        
        # 크리스마스 테스트
        result = check_holiday('20241225', 'test-api-key')
        assert result == True
        
        # API 호출 확인
        mock_api_request.assert_called_once()
    
    @patch('src.holiday_checker.safe_api_request')
    def test_check_holiday_not_holiday(self, mock_api_request):
        """평일 확인 테스트"""
        # Mock API 응답 (공휴일 없음)
        mock_response = {
            'response': {
                'body': {
                    'items': {}
                }
            }
        }
        mock_api_request.return_value = mock_response
        
        # 평일 테스트
        result = check_holiday('20241226', 'test-api-key')
        assert result == False
    
    @patch('src.holiday_checker.safe_api_request')
    def test_check_holiday_api_error(self, mock_api_request):
        """API 에러 처리 테스트"""
        # API 에러 시뮬레이션
        mock_api_request.side_effect = Exception("API Error")
        
        # 에러 시 기본값(평일) 반환
        result = check_holiday('20241225', 'test-api-key')
        assert result == False
    
    @patch('src.holiday_checker.check_holiday')
    @patch('src.holiday_checker.is_business_day')
    def test_should_send_report_weekend(self, mock_is_business_day, mock_check_holiday):
        """주말 리포트 전송 여부 테스트"""
        # 주말 시뮬레이션
        mock_is_business_day.return_value = False
        
        result = should_send_report()
        assert result == False
        
        # 공휴일 체크는 호출되지 않음
        mock_check_holiday.assert_not_called()
    
    @patch('src.holiday_checker.check_holiday')
    @patch('src.holiday_checker.is_business_day')
    def test_should_send_report_holiday(self, mock_is_business_day, mock_check_holiday):
        """공휴일 리포트 전송 여부 테스트"""
        # 평일이지만 공휴일
        mock_is_business_day.return_value = True
        mock_check_holiday.return_value = True
        
        result = should_send_report()
        assert result == False
    
    @patch('src.holiday_checker.check_holiday')
    @patch('src.holiday_checker.is_business_day')
    def test_should_send_report_business_day(self, mock_is_business_day, mock_check_holiday):
        """평일 리포트 전송 여부 테스트"""
        # 평일이면서 공휴일 아님
        mock_is_business_day.return_value = True
        mock_check_holiday.return_value = False
        
        result = should_send_report()
        assert result == True
    
    def test_get_date_range(self):
        """날짜 범위 조회 테스트"""
        start_date, end_date = get_date_range()
        
        # 금일 날짜와 동일해야 함 (현재까지의 사용 비용 조회)
        today = datetime.now().strftime('%Y-%m-%d')
        assert start_date == today
        assert end_date == today
    
    def test_get_monthly_date_range(self):
        """월간 날짜 범위 조회 테스트"""
        start_date, end_date = get_monthly_date_range()
        
        # 시작일은 이번 달 1일
        expected_start = datetime.now().replace(day=1).strftime('%Y-%m-%d')
        assert start_date == expected_start
        
        # 종료일은 금일 (현재까지의 사용 비용)
        expected_end = datetime.now().strftime('%Y-%m-%d')
        assert end_date == expected_end
    
    @patch('src.holiday_checker.check_holiday')
    def test_should_send_report_no_api_key(self, mock_check_holiday):
        """API 키 없을 때 처리 테스트"""
        import os
        
        # API 키 제거
        original_key = os.environ.get('PUBLIC_DATA_API_KEY')
        if 'PUBLIC_DATA_API_KEY' in os.environ:
            del os.environ['PUBLIC_DATA_API_KEY']
        
        try:
            result = should_send_report()
            # API 키가 없으면 전송 (경고 로그는 출력되지만 전송됨)
            assert result == True
            mock_check_holiday.assert_not_called()
        finally:
            # 원래 API 키 복원
            if original_key:
                os.environ['PUBLIC_DATA_API_KEY'] = original_key 