"""
Slack 연동 모듈
Slack API를 사용하여 메시지 전송 및 파일 업로드를 처리합니다.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# 로깅 설정
logger = logging.getLogger(__name__)

# KST 시간대 설정
KST = timezone(timedelta(hours=9))

def get_service_display_name(service_name: str) -> str:
    """
    AWS 서비스명을 한국어로 변환하여 읽기 쉽게 표시
    
    Args:
        service_name: AWS 서비스명
        
    Returns:
        한국어 표시명
    """
    service_mapping = {
        'Amazon Elastic Compute Cloud - Compute': 'EC2 컴퓨팅',
        'Amazon Elastic Compute Cloud': 'EC2',
        'Amazon Simple Storage Service': 'S3 스토리지',
        'Amazon Relational Database Service': 'RDS 데이터베이스',
        'AWS Lambda': 'Lambda 함수',
        'Amazon CloudFront': 'CloudFront CDN',
        'Amazon Route 53': 'Route 53 DNS',
        'Amazon Virtual Private Cloud': 'VPC 네트워크',
        'Amazon CloudWatch': 'CloudWatch 모니터링',
        'AWS CloudTrail': 'CloudTrail 로깅',
        'Amazon Elastic Load Balancing': 'ELB 로드밸런서',
        'Amazon ElastiCache': 'ElastiCache 캐시',
        'Amazon Elastic Container Service': 'ECS 컨테이너',
        'Amazon Elastic Kubernetes Service': 'EKS 쿠버네티스',
        'AWS Systems Manager': 'Systems Manager',
        'Amazon API Gateway': 'API Gateway',
        'Amazon Elastic Block Store': 'EBS 블록 스토리지',
        'AWS Key Management Service': 'KMS 키 관리',
        'Amazon SNS': 'SNS 알림',
        'Amazon SQS': 'SQS 메시지 큐',
        'AWS Config': 'Config 구성 관리',
        'Amazon CloudFormation': 'CloudFormation 인프라',
        'AWS Identity and Access Management': 'IAM 권한 관리',
        'Amazon Elastic File System': 'EFS 파일 시스템',
        'Amazon GuardDuty': 'GuardDuty 보안',
        'AWS WAF': 'WAF 웹 방화벽',
        'Amazon Inspector': 'Inspector 보안 평가',
        'AWS Certificate Manager': 'ACM 인증서 관리',
        'Amazon Macie': 'Macie 데이터 보안',
        'AWS Secrets Manager': 'Secrets Manager 암호 관리'
    }
    
    # 정확한 매칭 시도
    if service_name in service_mapping:
        return f"{service_mapping[service_name]}"
    
    # 부분 매칭 시도
    for key, value in service_mapping.items():
        if key.lower() in service_name.lower() or service_name.lower() in key.lower():
            return f"{value}"
    
    # 매칭되지 않는 경우 원본 반환
    return service_name

def get_slack_client() -> WebClient:
    """
    Slack 클라이언트 초기화
    
    Returns:
        Slack WebClient 인스턴스
    """
    token = os.environ.get('SLACK_BOT_TOKEN')
    if not token:
        raise ValueError("SLACK_BOT_TOKEN 환경 변수가 설정되지 않았습니다.")
    
    return WebClient(token=token)

def send_slack_message(
    blocks: List[Dict[str, Any]], 
    text: str = "AWS 비용 리포트",
    channel: Optional[str] = None
) -> bool:
    """
    Slack 메시지 전송
    
    Args:
        blocks: Block Kit 형태의 메시지 블록
        text: 대체 텍스트
        channel: 채널 ID (None이면 환경 변수 사용)
        
    Returns:
        전송 성공 여부
    """
    try:
        client = get_slack_client()
        
        if not channel:
            channel = os.environ.get('SLACK_CHANNEL')
            if not channel:
                raise ValueError("SLACK_CHANNEL 환경 변수가 설정되지 않았습니다.")
        
        response = client.chat_postMessage(
            channel=channel,
            blocks=blocks,
            text=text
        )
        
        logger.info(f"Slack 메시지 전송 성공: {response['ts']}")
        return True
        
    except SlackApiError as e:
        logger.error(f"Slack 메시지 전송 실패: {e.response['error']}")
        return False
    except Exception as e:
        logger.error(f"Slack 메시지 전송 중 예상치 못한 오류: {e}")
        return False

def upload_file_to_slack(
    file_content: bytes, 
    filename: str, 
    title: str = "차트",
    channel: Optional[str] = None
) -> bool:
    """
    Slack 파일 업로드
    
    Args:
        file_content: 파일 내용 (bytes)
        filename: 파일명
        title: 파일 제목
        channel: 채널 ID (None이면 환경 변수 사용)
        
    Returns:
        업로드 성공 여부
    """
    try:
        client = get_slack_client()
        
        if not channel:
            channel = os.environ.get('SLACK_CHANNEL')
            if not channel:
                raise ValueError("SLACK_CHANNEL 환경 변수가 설정되지 않았습니다.")
        
        # files_upload_v2를 사용하여 파일 업로드 (권장 방법)
        import tempfile
        import os as os_module
        
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
            tmp_file.write(file_content)
            tmp_file_path = tmp_file.name
        
        try:
            response = client.files_upload_v2(
                channel=channel,
                file=tmp_file_path,
                filename=filename,
                title=title
            )
        finally:
            # 임시 파일 정리
            try:
                os_module.unlink(tmp_file_path)
            except:
                pass
        
        logger.info(f"Slack 파일 업로드 성공: {response['file']['id']}")
        return True
        
    except SlackApiError as e:
        logger.error(f"Slack 파일 업로드 실패: {e.response['error']}")
        return False
    except Exception as e:
        logger.error(f"Slack 파일 업로드 중 예상치 못한 오류: {e}")
        return False

def create_cost_report_blocks(
    daily_cost_usd: float,
    daily_cost_krw: float,
    monthly_cost_usd: float,
    monthly_cost_krw: float,
    exchange_rate: float,
    budget_usage_percent: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    비용 리포트 Slack 블록 생성
    
    Args:
        daily_cost_usd: 일일 비용 (USD)
        daily_cost_krw: 일일 비용 (KRW)
        monthly_cost_usd: 월간 비용 (USD)
        monthly_cost_krw: 월간 비용 (KRW)
        exchange_rate: 환율
        budget_usage_percent: 예산 사용률 (선택사항)
        
    Returns:
        Slack Block Kit 블록 리스트
    """
    # 예산 사용률에 따른 이모지 선택
    if budget_usage_percent is not None:
        if budget_usage_percent < 50:
            budget_emoji = "🟢"
        elif budget_usage_percent < 80:
            budget_emoji = "🟡"
        else:
            budget_emoji = "🔴"
    else:
        budget_emoji = "📊"
    
    # 현재 KST 시간
    now = datetime.now(KST)
    
    # 일일 비용 상태에 따른 이모지 선택
    if daily_cost_usd >= 10:
        daily_emoji = "🔴"  # 고비용
    elif daily_cost_usd >= 1:
        daily_emoji = "🟡"  # 중간비용
    else:
        daily_emoji = "🟢"  # 저비용
    
    # 월간 비용 상태에 따른 이모지 선택
    if monthly_cost_usd >= 100:
        monthly_emoji = "🔴"
    elif monthly_cost_usd >= 50:
        monthly_emoji = "🟡"
    else:
        monthly_emoji = "🟢"
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "💰 AWS 비용 상세 리포트"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{now.strftime('%Y년 %m월 %d일')} AWS 사용 현황 요약*"
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"{daily_emoji} *오늘 현재까지 과금액*\n`${daily_cost_usd:.4f}`\n*₩{daily_cost_krw:,.0f}*"
                },
                {
                    "type": "mrkdwn",
                    "text": f"{monthly_emoji} *이번 달 누적 총액*\n`${monthly_cost_usd:.2f}`\n*₩{monthly_cost_krw:,.0f}*"
                }
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"💱 *현재 환율*: 1 USD = ₩{exchange_rate:,.2f}"
            }
        }
    ]
    
    # 예산 사용률이 있는 경우 추가
    if budget_usage_percent is not None:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{budget_emoji} *예산 사용률:* {budget_usage_percent:.1f}%"
            }
        })
    
    # 구분선 추가
    blocks.append({
        "type": "divider"
    })
    
    # 하단 정보
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"마지막 업데이트: {now.strftime('%Y-%m-%d %H:%M:%S KST')}"
            }
        ]
    })
    
    return blocks

def create_service_breakdown_blocks(service_costs: Dict[str, float], exchange_rate: float = 1300.0) -> List[Dict[str, Any]]:
    """
    서비스별 상세 비용 내역 Slack 블록 생성
    
    Args:
        service_costs: 서비스별 비용 딕셔너리
        exchange_rate: USD -> KRW 환율
        
    Returns:
        Slack Block Kit 블록 리스트
    """
    if not service_costs:
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "📋 *서비스별 비용 내역*\n비용 데이터가 없습니다."
                }
            }
        ]
    
    # 전체 비용 계산
    total_cost = sum(service_costs.values())
    
    # 상위 10개 서비스 표시 (더 상세한 정보 제공)
    top_services = dict(sorted(service_costs.items(), key=lambda x: x[1], reverse=True)[:10])
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "💰 AWS 서비스별 상세 과금 현황"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*📊 총 {len(service_costs)}개 서비스 사용 중 (상위 10개 표시)*\n*💵 전체 비용: ${total_cost:.2f} (₩{total_cost * exchange_rate:,.0f})*"
            }
        },
        {
            "type": "divider"
        }
    ]
    
    # 서비스별 상세 정보
    for i, (service, cost) in enumerate(top_services.items(), 1):
        # 전체 비용 대비 비율 계산
        percentage = (cost / total_cost * 100) if total_cost > 0 else 0
        
        # 비용 규모에 따른 이모지
        if cost >= 10:
            cost_emoji = "🔴"  # 고비용
        elif cost >= 1:
            cost_emoji = "🟡"  # 중간비용
        else:
            cost_emoji = "🟢"  # 저비용
        
        # 서비스명 한국어 표시 개선
        service_display = get_service_display_name(service)
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{cost_emoji} *{i}. {service_display}*\n💰 `${cost:.4f}` (₩{cost * exchange_rate:,.0f}) • {percentage:.1f}%"
            }
        })
    
    # 기타 서비스 비용 계산
    other_cost = sum(service_costs.values()) - sum(top_services.values())
    if other_cost > 0:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*기타 서비스*\n${other_cost:.2f}"
            }
        })
    
    return blocks

def send_cost_report(
    daily_cost_usd: float,
    daily_cost_krw: float,
    monthly_cost_usd: float,
    monthly_cost_krw: float,
    exchange_rate: float,
    service_costs: Dict[str, float],
    chart_image: Optional[bytes] = None,
    budget_usage_percent: Optional[float] = None
) -> bool:
    """
    완전한 비용 리포트 전송
    
    Args:
        daily_cost_usd: 일일 비용 (USD)
        daily_cost_krw: 일일 비용 (KRW)
        monthly_cost_usd: 월간 비용 (USD)
        monthly_cost_krw: 월간 비용 (KRW)
        exchange_rate: 환율
        service_costs: 서비스별 비용
        chart_image: 차트 이미지 (선택사항)
        budget_usage_percent: 예산 사용률 (선택사항)
        
    Returns:
        전송 성공 여부
    """
    try:
        # 메인 비용 리포트 블록 생성
        main_blocks = create_cost_report_blocks(
            daily_cost_usd, daily_cost_krw,
            monthly_cost_usd, monthly_cost_krw,
            exchange_rate, budget_usage_percent
        )
        
        # 메인 메시지 전송
        success = send_slack_message(main_blocks)
        if not success:
            return False
        
        # 서비스별 내역 블록 생성 및 전송
        if service_costs:
            breakdown_blocks = create_service_breakdown_blocks(service_costs, exchange_rate)
            success = send_slack_message(breakdown_blocks)
            if not success:
                logger.warning("서비스별 내역 전송 실패")
        
        # 차트 이미지 업로드
        if chart_image:
            now = datetime.now(KST)
            filename = f"aws_cost_chart_{now.strftime('%Y%m%d')}.png"
            
            success = upload_file_to_slack(
                chart_image, 
                filename, 
                "AWS 월간 비용 분석 차트"
            )
            if not success:
                logger.warning("차트 이미지 업로드 실패")
        
        logger.info("비용 리포트 전송 완료")
        return True
        
    except Exception as e:
        logger.error(f"비용 리포트 전송 실패: {e}")
        return False

def test_slack_connection() -> bool:
    """
    Slack 연결 테스트
    
    Returns:
        연결 성공 여부
    """
    try:
        client = get_slack_client()
        
        # auth.test API 호출로 토큰 유효성 확인
        response = client.auth_test()
        
        logger.info(f"Slack 연결 성공: {response['user']} ({response['team']})")
        return True
        
    except SlackApiError as e:
        logger.error(f"Slack 연결 실패: {e.response['error']}")
        return False
    except Exception as e:
        logger.error(f"Slack 연결 중 예상치 못한 오류: {e}")
        return False
