#!/usr/bin/env python3
"""
환경 변수 설정 파일(.env) 생성 스크립트
"""
import os
import shutil
from pathlib import Path

def create_env_file():
    """env.example을 복사하여 .env 파일 생성"""
    example_file = Path("env.example")
    env_file = Path(".env")
    
    if not example_file.exists():
        print("❌ env.example 파일이 존재하지 않습니다.")
        return False
    
    if env_file.exists():
        print("⚠️  .env 파일이 이미 존재합니다.")
        response = input("덮어쓰시겠습니까? (y/N): ")
        if response.lower() != 'y':
            print("취소되었습니다.")
            return False
    
    try:
        shutil.copy2(example_file, env_file)
        print("✅ .env 파일이 성공적으로 생성되었습니다.")
        print("📝 .env 파일을 편집하여 실제 API 키들을 입력하세요.")
        return True
    except Exception as e:
        print(f"❌ .env 파일 생성 실패: {e}")
        return False

def validate_env_file():
    """환경 변수 파일 유효성 검사"""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("❌ .env 파일이 존재하지 않습니다.")
        print("💡 python setup_env.py를 실행하여 .env 파일을 생성하세요.")
        return False
    
    # 필수 환경 변수 목록
    required_vars = [
        'SLACK_BOT_TOKEN',
        'SLACK_CHANNEL', 
        'PUBLIC_DATA_API_KEY',
        'CURRENCY_API_KEY'
    ]
    
    missing_vars = []
    
    with open(env_file, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
        
        for var in required_vars:
            if not any(line.startswith(f"{var}=") for line in lines):
                missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  다음 환경 변수들이 설정되지 않았습니다: {', '.join(missing_vars)}")
        return False
    
    print("✅ 모든 필수 환경 변수가 설정되었습니다.")
    return True

def main():
    """메인 함수"""
    print("🔧 AWS Cost Slack Reporter - 환경 변수 설정")
    print("=" * 50)
    
    if len(os.sys.argv) > 1 and os.sys.argv[1] == "validate":
        validate_env_file()
    else:
        create_env_file()
        print("\n📋 다음 단계:")
        print("1. .env 파일을 편집하여 실제 API 키들을 입력하세요")
        print("2. python setup_env.py validate로 설정을 확인하세요")

if __name__ == "__main__":
    main() 