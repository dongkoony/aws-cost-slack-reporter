"""
환율 변환 모듈
CurrencyAPI.com을 사용하여 USD를 KRW로 변환합니다.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import requests

# 로깅 설정
logger = logging.getLogger(__name__)

# KST 시간대 설정
KST = timezone(timedelta(hours=9))


def safe_api_request(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """안전한 API 요청 함수"""
    try:
        response = requests.request(
            method=method, url=url, headers=headers, params=params, timeout=timeout
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"API 요청 실패: {url} - {e}")
        raise


def get_exchange_rate(base: str = "USD", target: str = "KRW") -> float:
    """
    실시간 환율 조회 (currencyapi.com 사용)

    Args:
        base: 기준 통화 (기본값: USD)
        target: 대상 통화 (기본값: KRW)

    Returns:
        환율 (1 USD = ? KRW)
    """
    # currencyapi.com API 사용
    url = f"https://api.currencyapi.com/v3/latest"

    api_key = os.environ.get("CURRENCY_API_KEY")
    if not api_key:
        logger.warning("CURRENCY_API_KEY가 설정되지 않음. 기본 환율 1300을 사용합니다.")
        return 1300.0

    params = {"apikey": api_key, "base_currency": base, "currencies": target}

    try:
        data = safe_api_request(url, params=params)

        # currencyapi.com 응답 구조
        if "data" in data and target in data["data"]:
            rate = float(data["data"][target]["value"])
            logger.info(f"환율 조회 성공: 1 {base} = {rate:.2f} {target}")
            return rate
        else:
            logger.warning(f"환율 정보 없음: {base} -> {target}")
            return 1300.0  # 기본값

    except Exception as e:
        logger.error(f"환율 조회 실패: {e}")
        return 1300.0  # 기본값


def convert_usd_to_krw(usd_amount: float) -> float:
    """
    USD를 KRW로 변환

    Args:
        usd_amount: USD 금액

    Returns:
        KRW 금액
    """
    try:
        exchange_rate = get_exchange_rate("USD", "KRW")
        krw_amount = usd_amount * exchange_rate

        logger.info(f"환율 변환: ${usd_amount:.2f} = ₩{krw_amount:,.0f}")
        return krw_amount

    except Exception as e:
        logger.error(f"환율 변환 실패: {e}")
        # 기본 환율 1300 사용
        return usd_amount * 1300.0


def format_cost_krw(amount: float) -> str:
    """
    KRW 비용을 포맷팅

    Args:
        amount: KRW 금액

    Returns:
        포맷팅된 KRW 문자열
    """
    if amount < 1000:
        return f"₩{amount:.0f}"
    else:
        return f"₩{amount:,.0f}"


def get_cost_in_both_currencies(usd_amount: float) -> Dict[str, Any]:
    """
    USD 비용을 USD와 KRW로 모두 반환

    Args:
        usd_amount: USD 금액

    Returns:
        USD와 KRW 금액을 포함한 딕셔너리
    """
    try:
        krw_amount = convert_usd_to_krw(usd_amount)
        exchange_rate = get_exchange_rate("USD", "KRW")

        return {
            "usd": usd_amount,
            "krw": krw_amount,
            "exchange_rate": exchange_rate,
            "formatted_usd": format_cost_usd(usd_amount),
            "formatted_krw": format_cost_krw(krw_amount),
        }

    except Exception as e:
        logger.error(f"통화 변환 실패: {e}")
        # 기본값 반환
        return {
            "usd": usd_amount,
            "krw": usd_amount * 1300.0,
            "exchange_rate": 1300.0,
            "formatted_usd": format_cost_usd(usd_amount),
            "formatted_krw": format_cost_krw(usd_amount * 1300.0),
        }


def format_cost_usd(amount: float) -> str:
    """
    USD 비용을 포맷팅

    Args:
        amount: USD 금액

    Returns:
        포맷팅된 USD 문자열
    """
    if amount < 1:
        return f"${amount:.4f}"
    else:
        return f"${amount:.2f}"


def get_current_exchange_rate_info() -> Dict[str, Any]:
    """
    현재 환율 정보 조회

    Returns:
        환율 정보 딕셔너리
    """
    try:
        exchange_rate = get_exchange_rate("USD", "KRW")
        now = datetime.now(KST)

        return {
            "rate": exchange_rate,
            "base_currency": "USD",
            "target_currency": "KRW",
            "timestamp": now.isoformat(),
            "formatted_rate": f"1 USD = {exchange_rate:.2f} KRW",
        }

    except Exception as e:
        logger.error(f"환율 정보 조회 실패: {e}")
        return {
            "rate": 1300.0,
            "base_currency": "USD",
            "target_currency": "KRW",
            "timestamp": datetime.now(KST).isoformat(),
            "formatted_rate": "1 USD = 1,300.00 KRW (기본값)",
        }
