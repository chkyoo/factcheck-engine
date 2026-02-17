"""
Windows 작업 스케줄러용 배치 파일
매일 오전 9시에 자동 실행
"""

import schedule
import time
from daily_email_reporter import DailyEmailReporter
from datetime import datetime


def job():
    """스케줄된 작업"""
    print(f"\n{'='*70}")
    print(f"스케줄 실행: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")
    
    try:
        reporter = DailyEmailReporter()
        reporter.run_daily_report()
    except Exception as e:
        print(f"❌ 오류 발생: {e}")


def main():
    """메인 스케줄러"""
    print("=" * 70)
    print("팩트체크 엔진 스케줄러 시작")
    print("=" * 70)
    print()
    print("📅 스케줄 설정:")
    print("  • 매일 오전 9:00 - 일일 리포트 발송")
    print()
    print("💡 Ctrl+C를 눌러 종료할 수 있습니다.")
    print("=" * 70)
    print()
    
    # 스케줄 설정
    schedule.every().day.at("09:00").do(job)
    
    # 테스트용: 즉시 한 번 실행
    print("🔍 테스트 실행 중...")
    job()
    
    # 스케줄 실행
    print("\n⏰ 스케줄러 대기 중...")
    while True:
        schedule.run_pending()
        time.sleep(60)  # 1분마다 체크


if __name__ == "__main__":
    main()
