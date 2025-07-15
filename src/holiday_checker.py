"""
공휴일 확인 모듈
공공데이터포털 API를 사용하여 한국의 법정공휴일 및 대체공휴일을 확인합니다.
"""

import os
import requests
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

# 로깅 설정
logger = logging.getLogger(__name__)

# KST 시간대 설정
KST = timezone(timedelta(hours=9))

def parse_xml_to_dict(xml_string: str) -> Dict[str, Any]:
    """XML 문자열을 딕셔너리로 변환"""
    try:
        root = ET.fromstring(xml_string)
        
        def xml_to_dict(element):
            """재귀적으로 XML 요소를 딕셔너리로 변환"""
            result = {}
            
            # 자식 요소들 처리
            for child in element:
                if len(child) == 0:  # 리프 노드
                    result[child.tag] = child.text
                else:  # 중간 노드
                    if child.tag in result:
                        # 같은 태그가 여러 개인 경우 리스트로 처리
                        if not isinstance(result[child.tag], list):
                            result[child.tag] = [result[child.tag]]
                        result[child.tag].append(xml_to_dict(child))
                    else:
                        result[child.tag] = xml_to_dict(child)
            
            return result
        
        return xml_to_dict(root)
        
    except ET.ParseError as e:
        logger.error(f"XML 파싱 실패: {e}")
        raise ValueError(f"XML 파싱 실패: {e}")

def safe_api_request(
    url: str, 
    method: str = 'GET', 
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """안전한 API 요청 함수 (JSON 및 XML 응답 지원)"""
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            timeout=timeout
        )
        response.raise_for_status()
        
        # 응답 내용 디버깅
        logger.debug(f"API 응답 상태코드: {response.status_code}")
        logger.debug(f"API 응답 Content-Type: {response.headers.get('content-type', 'Unknown')}")
        logger.debug(f"API 응답 내용 (첫 200자): {response.text[:200]}")
        
        # JSON 파싱 시도
        try:
            return response.json()
        except ValueError as json_error:
            # JSON 파싱 실패시 XML 파싱 시도
            logger.info("JSON 파싱 실패, XML 파싱 시도")
            try:
                return parse_xml_to_dict(response.text)
            except ValueError as xml_error:
                logger.error(f"JSON과 XML 파싱 모두 실패. JSON 에러: {json_error}, XML 에러: {xml_error}")
                logger.error(f"응답 내용: {response.text[:500]}")
                raise ValueError(f"API 응답 파싱 실패: {xml_error}")
                
    except requests.exceptions.RequestException as e:
        logger.error(f"API 요청 실패: {url} - {e}")
        raise

def check_holiday(date: str, api_key: str) -> bool:
    """
    공공데이터포털 API를 통한 공휴일 확인
    
    Args:
        date: 확인할 날짜 (YYYYMMDD)
        api_key: 공공데이터포털 API 키
        
    Returns:
        공휴일 여부 (True: 공휴일, False: 평일)
    """
    # 휴일 정보 API 사용 (법정공휴일 및 대체공휴일)
    url = "http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo"
    
    # API 키가 이미 인코딩된 경우 디코딩 후 다시 인코딩되는 문제 방지
    import urllib.parse
    
    # API 키 디코딩 (이미 인코딩된 경우)
    try:
        decoded_key = urllib.parse.unquote(api_key)
        logger.debug(f"API 키 디코딩: {decoded_key[:10]}...")
    except:
        decoded_key = api_key
        logger.debug(f"API 키 디코딩 실패, 원본 사용: {api_key[:10]}...")
    
    params = {
        'serviceKey': decoded_key,
        'pageNo': '1',
        'numOfRows': '100',  # 한 달 최대 공휴일 수를 고려하여 충분히 설정
        'solYear': date[:4],
        'solMonth': date[4:6],
        '_type': 'json'  # JSON 형식으로 응답 요청
    }
    
    try:
        data = safe_api_request(url, params=params)
        
        # API 응답 구조 확인
        if 'cmmMsgHeader' in data:
            # 에러 응답 처리
            header = data['cmmMsgHeader']
            return_reason_code = header.get('returnReasonCode', '')
            error_msg = header.get('returnAuthMsg', header.get('errMsg', 'Unknown error'))
            
            if return_reason_code == '30':
                logger.error(f"API 키 오류: {error_msg}")
                logger.error("💡 해결 방법:")
                logger.error("  1. 공공데이터포털(data.go.kr)에서 API 키를 다시 확인하세요")
                logger.error("  2. API 키가 올바르게 .env 파일에 설정되었는지 확인하세요")
                logger.error("  3. API 키에 특수문자가 포함되어 있으면 URL 인코딩 문제일 수 있습니다")
                return False
            else:
                logger.error(f"공휴일 API 에러 (코드: {return_reason_code}): {error_msg}")
                return False
        
        elif 'response' in data:
            response_data = data['response']
            
            # 성공 응답 체크
            if response_data.get('header', {}).get('resultCode') == '00':
                body = response_data.get('body', {})
                
                # totalCount가 0이면 해당 월에 공휴일 없음
                total_count = body.get('totalCount', 0)
                if total_count == 0:
                    logger.info(f"해당 월에 공휴일 없음: {date[:6]}")
                    return False
                
                # 공휴일 목록에서 해당 날짜 확인
                items = body.get('items', {})
                if 'item' in items:
                    holidays = items['item']
                    if isinstance(holidays, dict):
                        holidays = [holidays]
                    
                    for holiday in holidays:
                        holiday_date = str(holiday.get('locdate', ''))
                        if holiday_date == date:
                            holiday_name = holiday.get('dateName', '공휴일')
                            logger.info(f"공휴일 확인됨: {date} - {holiday_name}")
                            return True
                
                logger.info(f"평일 확인됨: {date}")
                return False
            else:
                error_msg = response_data.get('header', {}).get('resultMsg', 'Unknown error')
                logger.error(f"공휴일 API 응답 에러: {error_msg}")
                return False
        else:
            logger.error(f"예상치 못한 API 응답 구조: {data}")
            return False
        
    except Exception as e:
        logger.error(f"공휴일 확인 API 호출 실패: {e}")
        # 에러 시 기본값으로 평일 반환 (서비스 중단 방지)
        return False

def is_business_day(date: datetime) -> bool:
    """
    해당 날짜가 평일(월~금)인지 확인
    
    Args:
        date: 확인할 날짜
        
    Returns:
        평일 여부 (True: 평일, False: 주말)
    """
    # 월요일(0) ~ 금요일(4)이 평일
    return date.weekday() < 5

def should_send_report() -> bool:
    """
    오늘 비용 리포트를 전송해야 하는지 확인
    (평일이면서 공휴일이 아닌 경우)
    
    Returns:
        리포트 전송 여부
    """
    # 현재 KST 시간
    now = datetime.now(KST)
    today_str = now.strftime('%Y%m%d')
    
    # 주말 체크
    if not is_business_day(now):
        logger.info(f"주말이므로 리포트 전송 생략: {today_str}")
        return False
    
    # 공휴일 체크
    api_key = os.environ.get('PUBLIC_DATA_API_KEY')
    if not api_key:
        logger.warning("PUBLIC_DATA_API_KEY가 설정되지 않음. 공휴일 체크를 건너뜁니다.")
        return True  # API 키가 없으면 전송
    
    is_holiday = check_holiday(today_str, api_key)
    if is_holiday:
        logger.info(f"공휴일이므로 리포트 전송 생략: {today_str}")
        return False
    
    logger.info(f"평일이므로 리포트 전송 진행: {today_str}")
    return True

def get_date_range() -> tuple[str, str]:
    """
    비용 조회를 위한 날짜 범위 반환
    (금일 날짜 기준 - 오후 6시 현재까지의 사용 비용)
    
    Returns:
        (시작날짜, 종료날짜) 튜플 (YYYY-MM-DD 형식)
    """
    now = datetime.now(KST)
    # 금일 날짜 계산
    today_str = now.strftime('%Y-%m-%d')
    
    return today_str, today_str

def get_monthly_date_range() -> tuple[str, str]:
    """
    이번 달 비용 조회를 위한 날짜 범위 반환
    (금일까지의 누적 비용)
    
    Returns:
        (시작날짜, 종료날짜) 튜플 (YYYY-MM-DD 형식)
    """
    now = datetime.now(KST)
    
    # 이번 달 첫날
    first_day = now.replace(day=1)
    start_date = first_day.strftime('%Y-%m-%d')
    
    # 금일 날짜 (현재까지의 사용 비용)
    today_str = now.strftime('%Y-%m-%d')
    end_date = today_str
    
    return start_date, end_date
