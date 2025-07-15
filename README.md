# AWS Cost Slack Reporter

매일 평일(월~금), 공휴일을 제외한 날 한국시간 오후 6시에 AWS 비용 현황을 Slack으로 보고하는 서버리스 Lambda 기반 자동화 서비스입니다.

## 🎯 주요 기능

- **정기 알림**: 매일 워크데이에만 정해진 시간(18:00 KST)에 비용 리포트 전송
- **비용 통제**: 금일 사용액 및 이번 달 누적액을 USD·KRW로 함께 표시
- **공휴일 배제**: 공공데이터포털 API로 법정·대체 공휴일 확인
- **시각화**: 블록 메시지 구성 + 월간 비용 추이 차트 이미지 첨부
- **재활용성**: GitHub 퍼블릭 레포로 배포해 누구나 포크·확장 가능

## 🚀 빠른 시작 (5분 설정)

### 1. 사전 요구사항 설치

```bash
# uv 패키지 매니저 설치 (Python 의존성 관리)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# AWS CLI 설치 및 설정
aws configure
# AWS Access Key ID: (IAM에서 발급받은 키)
# AWS Secret Access Key: (IAM에서 발급받은 시크릿)
# Default region name: ap-northeast-2
# Default output format: json
```

### 2. 프로젝트 설정

```bash
# 프로젝트 폴더로 이동
cd aws-cost-slack-reporter

# 환경 변수 파일 생성
python setup_env.py

# .env 파일 편집하여 API 키들 입력
nano .env  # 또는 vim .env
```

### 3. API 키 발급 및 설정

#### 3.1 Slack Bot Token 발급
1. [Slack API 사이트](https://api.slack.com/apps) 접속
2. "Create New App" → "From scratch" 선택
3. 앱 이름 입력 후 워크스페이스 선택
4. **OAuth & Permissions** 메뉴에서 Bot Token Scopes 추가:
   - `chat:write` (메시지 전송)
   - `files:write` (파일 업로드)
   - `calls:write` (통화 기능)
5. "Install to Workspace" 클릭
6. **Bot User OAuth Token** 복사 (xoxb-로 시작)

#### 3.2 공공데이터포털 API Key 발급
1. [공공데이터포털](https://www.data.go.kr/) 회원가입/로그인
2. "특일 정보" API 검색 후 활용신청
3. 승인 후 **인증키** 복사

#### 3.3 CurrencyAPI.com API Key 발급
1. [CurrencyAPI.com](https://currencyapi.com/) 회원가입
2. 대시보드에서 **API Key** 복사

#### 3.4 .env 파일 편집
```bash
# Slack 설정
SLACK_BOT_TOKEN=xoxb-your-actual-bot-token
SLACK_CHANNEL=C08PGLTTW6T  # 채널 ID (채널 우클릭 → 링크 복사에서 확인)

# 공공데이터포털 API (공휴일 조회)
PUBLIC_DATA_API_KEY=your-actual-api-key

# CurrencyAPI.com (환율 조회)  
CURRENCY_API_KEY=your-actual-api-key

# AWS 설정
AWS_DEFAULT_REGION=ap-northeast-2

# 로깅 설정
LOG_LEVEL=INFO
DEBUG_MODE=false
```

### 4. 배포 실행

```bash
# 배포 스크립트 실행 (모든 AWS 리소스 자동 생성)
chmod +x deploy.sh
./deploy.sh
```

### 5. 테스트

```bash
# Lambda 함수 직접 테스트
aws lambda invoke --function-name aws-cost-slack-reporter --region ap-northeast-2 response.json
cat response.json
```

**🎉 완료! 이제 매일 평일 오후 6시에 자동으로 AWS 비용 리포트가 Slack으로 전송됩니다.**

## 🛠️ 기술 스택

- **언어**: Python 3.12
- **패키지 관리**: pyproject.toml + uv
- **AWS 서비스**: Lambda, EventBridge, Cost Explorer API, CloudWatch Logs
- **외부 API**: 공공데이터포털, CurrencyAPI.com
- **Slack 연동**: slack_sdk
- **차트 생성**: matplotlib

## 📋 필요한 AWS 권한

배포 스크립트가 자동으로 다음 권한을 설정합니다:
- **Cost Explorer**: `ce:GetCostAndUsage`, `ce:GetDimensionValues`
- **Lambda**: 함수 생성/업데이트/실행
- **IAM**: 역할 생성 및 정책 연결
- **EventBridge**: 스케줄 생성 및 관리
- **CloudWatch**: 로그 생성 및 조회

## 🏗️ 시스템 아키텍처

```mermaid
graph TB
    subgraph "AWS Cloud"
        EB[EventBridge<br/>매일 18:00 KST 스케줄]
        L[Lambda Function<br/>aws-cost-slack-reporter]
        CE[Cost Explorer API]
        CW[CloudWatch Logs]
        
        subgraph "Lambda Function"
            HC[Holiday Checker<br/>공휴일 확인]
            CR[Cost Reporter<br/>비용 조회]
            ER[Exchange Rate<br/>환율 변환]
            CG[Chart Generator<br/>차트 생성]
            SU[Slack Utils<br/>메시지 전송]
        end
    end
    
    subgraph "External APIs"
        PD[공공데이터포털<br/>공휴일 정보]
        CA[CurrencyAPI.com<br/>환율 정보]
    end
    
    subgraph "Slack Workspace"
        SC[Slack Channel<br/>비용 리포트 수신]
    end
    
    EB -->|트리거| L
    L --> HC
    HC -->|공휴일 확인| PD
    L --> CR
    CR -->|비용 데이터 조회| CE
    L --> ER
    ER -->|환율 정보 조회| CA
    L --> CG
    CG -->|차트 생성| L
    L --> SU
    SU -->|메시지 전송| SC
    L -->|로깅| CW
    
    style EB fill:#FF9900
    style L fill:#009900
    style CE fill:#FF9900
    style CW fill:#FF9900
    style PD fill:#4285F4
    style CA fill:#4285F4
    style SC fill:#ffc9de
```

## 🔄 데이터 플로우

```mermaid
sequenceDiagram
    participant EB as EventBridge
    participant L as Lambda
    participant HC as Holiday Checker
    participant PD as 공공데이터포털
    participant CR as Cost Reporter
    participant CE as Cost Explorer
    participant ER as Exchange Rate
    participant CA as CurrencyAPI
    participant CG as Chart Generator
    participant SU as Slack Utils
    participant SC as Slack Channel
    
    EB->>L: 매일 18:00 KST 트리거
    L->>HC: 공휴일 확인 요청
    HC->>PD: 공휴일 정보 조회
    PD-->>HC: 공휴일 여부 응답
    HC-->>L: 평일 여부 확인
    
    alt 평일인 경우
        L->>CR: AWS 비용 조회 요청
        CR->>CE: 일일/월간 비용 조회
        CE-->>CR: 비용 데이터 응답
        CR-->>L: 비용 정보 반환
        
        L->>ER: 환율 정보 조회 요청
        ER->>CA: USD/KRW 환율 조회
        CA-->>ER: 환율 정보 응답
        ER-->>L: 환율 정보 반환
        
        L->>CG: 차트 생성 요청
        CG-->>L: 차트 이미지 생성
        
        L->>SU: Slack 메시지 전송 요청
        SU->>SC: 비용 리포트 + 차트 전송
        SC-->>SU: 전송 완료 응답
        SU-->>L: 전송 결과 반환
        
        L-->>EB: 성공 응답
    else 주말/공휴일인 경우
        L-->>EB: 리포트 전송 안함 응답
    end
```

## 🔧 개발 가이드

### 로컬 개발

```bash
# 가상환경 생성
uv venv
source .venv/bin/activate

# 의존성 설치
uv sync

# 환경 변수 로드
source .env

# 로컬 테스트
python src/lambda_function.py
```

### 테스트

#### 테스트 환경 설정

```bash
# 개발 의존성 설치
uv sync --extra dev

# 또는 pip 사용
pip install -e ".[dev]"
```

#### 테스트 실행

```bash
# 모든 테스트 실행 (권장)
./run_tests.sh

# 단위 테스트만 실행
./run_tests.sh -u

# 통합 테스트만 실행
./run_tests.sh -i

# 상세한 출력과 함께 실행
./run_tests.sh -v

# 커버리지 리포트 생성
./run_tests.sh -c

# 직접 pytest 사용
pytest tests/ -v --cov=src --cov-report=html
```

#### 테스트 구조

```
tests/
├── conftest.py              # pytest 설정 및 공통 fixture
├── test_holiday_checker.py  # 공휴일 확인 모듈 테스트
├── test_exchange_rate.py    # 환율 변환 모듈 테스트
├── test_lambda_function.py  # Lambda 메인 함수 테스트
└── test_integration.py      # 전체 시스템 통합 테스트
```

#### 테스트 종류

1. **단위 테스트** (`test_holiday_checker.py`, `test_exchange_rate.py`)
   - 개별 함수/모듈의 동작 검증
   - Mock을 사용한 외부 API 의존성 제거
   - 다양한 입력값과 에러 상황 테스트

2. **통합 테스트** (`test_lambda_function.py`, `test_integration.py`)
   - 전체 시스템 워크플로우 검증
   - 모듈 간 상호작용 테스트
   - 실제 API 호출 시뮬레이션

#### 테스트 커버리지

```bash
# HTML 커버리지 리포트 생성
./run_tests.sh -c

# 브라우저에서 리포트 확인
open htmlcov/index.html
```

#### 테스트 마커 사용

```bash
# 특정 마커로 테스트 실행
pytest -m unit          # 단위 테스트만
pytest -m integration   # 통합 테스트만
pytest -m "not slow"    # 느린 테스트 제외
```

### 로깅

CloudWatch Logs에서 다음 정보를 확인할 수 있습니다:
- Lambda 함수 실행 로그
- API 호출 결과
- 에러 및 예외 정보

## 📊 비용 최적화

- **Lambda 메모리**: 512MB (차트 생성에 최적화)
- **타임아웃**: 5분 (API 호출 시간 고려)
- **예상 월 비용**: $0.50 미만

## 🔒 보안 고려사항

- 모든 API 키는 환경 변수로 관리
- `.env` 파일은 Git에서 제외
- IAM 역할은 최소 권한 원칙 적용
- 로그에서 민감 정보 자동 마스킹

## 🐛 문제 해결

### 일반적인 문제

1. **환경 변수 누락**
   ```bash
   python setup_env.py validate
   ```

2. **Slack 연결 실패**
   - Bot Token 유효성 확인
   - 채널에 봇 초대 확인
   - 권한 스코프 확인

3. **AWS 비용 조회 실패**
   - IAM 권한 확인
   - Cost Explorer API 활성화 확인

4. **공휴일 API 오류**
   - API 키 유효성 확인
   - 일일 호출 한도 확인

### 로그 확인

```bash
# CloudWatch Logs 확인
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/aws-cost-slack-reporter"

# 최근 로그 조회
aws logs tail /aws/lambda/aws-cost-slack-reporter --follow
```

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

---

⭐ 이 프로젝트가 도움이 되었다면 스타를 눌러주세요! 