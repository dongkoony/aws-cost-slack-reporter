"""
차트 생성 모듈
matplotlib을 사용하여 AWS 비용 추이 차트를 생성합니다.
"""

import io
import logging
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple
import numpy as np

# 로깅 설정
logger = logging.getLogger(__name__)

# KST 시간대 설정
KST = timezone(timedelta(hours=9))

# 한글 폰트 설정
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

def create_monthly_cost_chart(service_costs: Dict[str, float], monthly_total: float) -> bytes:
    """
    월간 서비스별 비용 차트 생성
    
    Args:
        service_costs: 서비스별 비용 딕셔너리
        monthly_total: 월간 총 비용
        
    Returns:
        차트 이미지 바이트 데이터
    """
    try:
        # 상위 10개 서비스만 선택
        top_services = dict(sorted(service_costs.items(), key=lambda x: x[1], reverse=True)[:10])
        
        # 기타 서비스 비용 계산
        other_cost = sum(service_costs.values()) - sum(top_services.values())
        if other_cost > 0:
            top_services['기타 서비스'] = other_cost
        
        # 차트 생성
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
        fig.suptitle('AWS 월간 비용 분석', fontsize=16, fontweight='bold')
        
        # 1. 파이 차트 (서비스별 비용 비율)
        ax1.pie(top_services.values(), labels=top_services.keys(), autopct='%1.1f%%', startangle=90)
        ax1.set_title('서비스별 비용 비율', fontsize=12, fontweight='bold')
        
        # 2. 막대 차트 (서비스별 비용 금액)
        services = list(top_services.keys())
        costs = list(top_services.values())
        
        bars = ax2.bar(range(len(services)), costs, color='skyblue', alpha=0.7)
        ax2.set_title('서비스별 비용 금액', fontsize=12, fontweight='bold')
        ax2.set_xlabel('서비스')
        ax2.set_ylabel('비용 (USD)')
        ax2.set_xticks(range(len(services)))
        ax2.set_xticklabels(services, rotation=45, ha='right')
        
        # 막대 위에 값 표시
        for bar, cost in zip(bars, costs):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                    f'${cost:.2f}', ha='center', va='bottom', fontsize=8)
        
        # 총 비용 정보 추가
        fig.text(0.5, 0.02, f'월간 총 비용: ${monthly_total:.2f}', 
                ha='center', fontsize=14, fontweight='bold', 
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.7))
        
        plt.tight_layout()
        
        # 이미지를 바이트로 변환
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        img_bytes = img_buffer.getvalue()
        
        plt.close()
        
        logger.info(f"월간 비용 차트 생성 완료: {len(top_services)}개 서비스")
        return img_bytes
        
    except Exception as e:
        logger.error(f"차트 생성 실패: {e}")
        # 에러 시 빈 이미지 반환
        return create_error_chart()

def create_daily_cost_trend_chart(daily_costs: List[Tuple[str, float]]) -> bytes:
    """
    일일 비용 추이 차트 생성
    
    Args:
        daily_costs: (날짜, 비용) 튜플 리스트
        
    Returns:
        차트 이미지 바이트 데이터
    """
    try:
        if not daily_costs:
            return create_error_chart("데이터가 없습니다")
        
        # 데이터 분리
        dates = [datetime.strptime(date, '%Y-%m-%d') for date, _ in daily_costs]
        costs = [cost for _, cost in daily_costs]
        
        # 차트 생성
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 선 그래프
        ax.plot(dates, costs, marker='o', linewidth=2, markersize=6, color='blue', alpha=0.7)
        
        # 영역 채우기
        ax.fill_between(dates, costs, alpha=0.3, color='skyblue')
        
        # 축 설정
        ax.set_title('일일 AWS 비용 추이', fontsize=14, fontweight='bold')
        ax.set_xlabel('날짜')
        ax.set_ylabel('비용 (USD)')
        
        # 날짜 포맷 설정
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates)//10)))
        
        # 격자 설정
        ax.grid(True, alpha=0.3)
        
        # 값 표시
        for date, cost in zip(dates, costs):
            ax.annotate(f'${cost:.2f}', (date, cost), 
                       textcoords="offset points", xytext=(0,10), ha='center', fontsize=8)
        
        # 통계 정보 추가
        avg_cost = np.mean(costs)
        max_cost = max(costs)
        min_cost = min(costs)
        
        stats_text = f'평균: ${avg_cost:.2f} | 최대: ${max_cost:.2f} | 최소: ${min_cost:.2f}'
        fig.text(0.5, 0.02, stats_text, ha='center', fontsize=10, 
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgreen", alpha=0.7))
        
        plt.tight_layout()
        
        # 이미지를 바이트로 변환
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        img_bytes = img_buffer.getvalue()
        
        plt.close()
        
        logger.info(f"일일 비용 추이 차트 생성 완료: {len(daily_costs)}일 데이터")
        return img_bytes
        
    except Exception as e:
        logger.error(f"추이 차트 생성 실패: {e}")
        return create_error_chart()

def create_cost_comparison_chart(daily_cost: float, monthly_cost: float) -> bytes:
    """
    일일 vs 월간 비용 비교 차트 생성
    
    Args:
        daily_cost: 일일 비용
        monthly_cost: 월간 비용
        
    Returns:
        차트 이미지 바이트 데이터
    """
    try:
        # 차트 생성
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        fig.suptitle('AWS 비용 비교', fontsize=16, fontweight='bold')
        
        # 1. 일일 비용 게이지 차트
        daily_percentage = min(100, (daily_cost / max(monthly_cost * 0.1, 1)) * 100)
        
        ax1.pie([daily_percentage, 100-daily_percentage], 
                labels=['일일 비용', ''], 
                colors=['red', 'lightgray'],
                startangle=90)
        ax1.set_title(f'일일 비용\n${daily_cost:.2f}', fontsize=12, fontweight='bold')
        
        # 2. 월간 비용 막대 차트
        categories = ['일일 평균', '월간 총액']
        values = [monthly_cost / 30, monthly_cost]  # 30일 기준
        
        bars = ax2.bar(categories, values, color=['orange', 'blue'], alpha=0.7)
        ax2.set_title('월간 비용 분석', fontsize=12, fontweight='bold')
        ax2.set_ylabel('비용 (USD)')
        
        # 막대 위에 값 표시
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                    f'${value:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        # 비율 정보 추가
        if monthly_cost > 0:
            daily_ratio = (daily_cost / (monthly_cost / 30)) * 100
            ratio_text = f'오늘 비용: 월 평균의 {daily_ratio:.1f}%'
        else:
            ratio_text = '오늘 비용: 월 평균 대비 계산 불가'
        
        fig.text(0.5, 0.02, ratio_text, ha='center', fontsize=12, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.7))
        
        plt.tight_layout()
        
        # 이미지를 바이트로 변환
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        img_bytes = img_buffer.getvalue()
        
        plt.close()
        
        logger.info("비용 비교 차트 생성 완료")
        return img_bytes
        
    except Exception as e:
        logger.error(f"비용 비교 차트 생성 실패: {e}")
        return create_error_chart()

def create_error_chart(message: str = "차트 생성 중 오류가 발생했습니다") -> bytes:
    """
    에러 차트 생성
    
    Args:
        message: 에러 메시지
        
    Returns:
        에러 차트 이미지 바이트 데이터
    """
    try:
        fig, ax = plt.subplots(figsize=(8, 6))
        
        ax.text(0.5, 0.5, message, ha='center', va='center', 
                fontsize=14, fontweight='bold', transform=ax.transAxes)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        # 이미지를 바이트로 변환
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        img_bytes = img_buffer.getvalue()
        
        plt.close()
        
        logger.warning(f"에러 차트 생성: {message}")
        return img_bytes
        
    except Exception as e:
        logger.error(f"에러 차트 생성 실패: {e}")
        # 최소한의 빈 이미지 반환
        return b''

def generate_cost_report_chart(cost_summary: Dict[str, Any]) -> bytes:
    """
    비용 리포트용 종합 차트 생성
    
    Args:
        cost_summary: 비용 요약 데이터
        
    Returns:
        차트 이미지 바이트 데이터
    """
    try:
        daily_cost = cost_summary.get('daily_cost', 0.0)
        monthly_cost = cost_summary.get('monthly_cost', 0.0)
        service_breakdown = cost_summary.get('service_breakdown', {})
        
        # 서비스별 비용 차트 생성
        return create_monthly_cost_chart(service_breakdown, monthly_cost)
        
    except Exception as e:
        logger.error(f"비용 리포트 차트 생성 실패: {e}")
        return create_error_chart()
