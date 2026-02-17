"""
일일 팩트체크 이메일 리포터
매일 자동으로 뉴스를 모니터링하고 팩트체크 결과를 이메일로 전송
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from pathlib import Path
import sys
from datetime import datetime
import os
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent / "src"))

from rss_monitor import RSSMonitor
from article_extractor import ArticleExtractor
from claim_detector import ClaimDetector
from priority_scorer import PriorityScorer

# 환경변수 로드
load_dotenv()


class DailyEmailReporter:
    """일일 팩트체크 이메일 리포터"""
    
    def __init__(self):
        # 환경변수 로드 (.env 파일 또는 GitHub Actions)
        load_dotenv()
        
        # 이메일 설정 (환경변수에서 로드)
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.sender_email = os.getenv('SENDER_EMAIL')
        self.sender_password = os.getenv('SENDER_PASSWORD')
        self.recipient_email = os.getenv('RECIPIENT_EMAIL')
        
        # 모듈 초기화
        self.rss_monitor = RSSMonitor()
        self.extractor = ArticleExtractor()
        self.detector = ClaimDetector()
        self.scorer = PriorityScorer()
    
    def run_daily_report(self):
        """일일 리포트 실행"""
        print("=" * 70)
        print(f"일일 팩트체크 리포트 생성 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        print()
        
        # 1. RSS 피드 수집
        print("📡 1단계: RSS 피드 수집 중...")
        self.rss_monitor.collect_feeds()
        
        # 2. 팩트체크 대상 조회
        print("🔍 2단계: 팩트체크 대상 분석 중...")
        pending_articles = self.rss_monitor.get_pending_articles(limit=10)
        
        if not pending_articles:
            print("ℹ️  오늘은 팩트체크 대상 기사가 없습니다.")
            self._send_no_articles_email()
            return
        
        # 3. 상세 분석
        print(f"📊 3단계: {len(pending_articles)}개 기사 상세 분석 중...")
        analyzed_articles = []
        
        for url, title, source, score in pending_articles[:5]:  # 최대 5개만
            try:
                article = self.extractor.extract(url)
                if not article:
                    print(f"  ⚠️ 본문 추출 실패: {url}")
                    # 실패 시 예외 처리: 제목만으로 분석 진행
                    article = {
                        'title': title,
                        'text': '',  # 본문 없음
                        'source': source,
                        'date': datetime.now().strftime('%Y-%m-%d')
                    }
                    print(f"  ↪️ 제목 기반 분석으로 전환합니다.")
                
                print(f"  📄 본문 길이: {len(article.get('text', ''))}자")
                
                claims = self.detector.detect(article['text'])
                has_vague = self.detector.has_vague_source(article['text'])
                score_result = self.scorer.calculate_score(article, claims, has_vague)
                
                print(f"  📊 점수: {score_result['total_score']} (세부: {score_result['breakdown']})")
                
                if score_result['should_factcheck']:
                    analyzed_articles.append({
                        'url': url,
                        'article': article,
                        'claims': claims,
                        'score': score_result
                    })
                    print(f"  ✓ {title[:50]}... (점수: {score_result['total_score']})")
                
            except Exception as e:
                print(f"  ❌ 분석 실패: {e}")
        
        # 4. 이메일 전송
        if analyzed_articles:
            print(f"\n📧 4단계: 이메일 전송 중... ({len(analyzed_articles)}개 기사)")
            self._send_factcheck_email(analyzed_articles)
            print("✅ 이메일 전송 완료!")
        else:
            print("\nℹ️  상세 분석 결과 팩트체크 대상이 없습니다.")
            self._send_no_articles_email()
    
    def _send_factcheck_email(self, articles):
        """팩트체크 리포트 이메일 전송"""
        # HTML 이메일 생성
        html_content = self._generate_html_report(articles)
        
        # 이메일 메시지 생성
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"📊 일일 팩트체크 리포트 - {datetime.now().strftime('%Y년 %m월 %d일')}"
        msg['From'] = self.sender_email
        msg['To'] = self.recipient_email
        
        # HTML 파트 추가
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        # SMTP 전송
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
        except Exception as e:
            print(f"❌ 이메일 전송 실패: {e}")
            raise
    
    def _send_no_articles_email(self):
        """팩트체크 대상 없음 이메일 전송"""
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Malgun Gothic', Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #f0f0f0; padding: 20px; border-radius: 10px; text-align: center; }}
                .content {{ padding: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 일일 팩트체크 리포트</h1>
                    <p>{datetime.now().strftime('%Y년 %m월 %d일')}</p>
                </div>
                <div class="content">
                    <h2>ℹ️ 오늘의 팩트체크 대상 기사</h2>
                    <p><strong>금일 팩트체크가 필요한 기사가 발견되지 않았습니다.</strong></p>
                    <p>모니터링은 정상적으로 수행되었으며, 우선순위 70점 이상의 기사가 없었습니다.</p>
                    <hr>
                    <p style="color: #666; font-size: 12px;">
                        이 이메일은 팩트체크 엔진에서 자동으로 발송되었습니다.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"📊 일일 팩트체크 리포트 - {datetime.now().strftime('%Y년 %m월 %d일')} (대상 없음)"
        msg['From'] = self.sender_email
        msg['To'] = self.recipient_email
        
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            print("✅ '대상 없음' 알림 이메일 전송 완료")
        except Exception as e:
            print(f"❌ 이메일 전송 실패: {e}")
    
    def _generate_html_report(self, articles):
        """HTML 리포트 생성"""
        articles_html = ""
        
        for i, item in enumerate(articles, 1):
            article = item['article']
            claims = item['claims']
            score = item['score']
            
            # 주장 목록 HTML
            claims_html = ""
            for j, claim in enumerate(claims[:3], 1):  # 최대 3개
                claim_type = {
                    'statistical': '📊 통계',
                    'causal': '🔗 인과관계',
                    'extreme': '⚠️ 극단 표현'
                }.get(claim['type'], claim['type'])
                
                claims_html += f"""
                <li>
                    <strong>[{claim_type}]</strong> {claim['claim'][:100]}...
                    <br><small>신뢰도: {claim['confidence']}</small>
                </li>
                """
            
            # 우선순위 색상
            priority_color = {
                'HIGH': '#e74c3c',
                'MEDIUM': '#f39c12',
                'LOW': '#95a5a6'
            }.get(score['priority'], '#95a5a6')
            
            articles_html += f"""
            <div style="border: 1px solid #ddd; border-radius: 10px; padding: 20px; margin-bottom: 20px; background: #f9f9f9;">
                <h3 style="margin-top: 0;">
                    [{i}] {article['title']}
                </h3>
                
                <p style="color: #666;">
                    <strong>언론사:</strong> {article['source']} | 
                    <strong>발행일:</strong> {article['date']}
                </p>
                
                <div style="background: white; padding: 15px; border-radius: 5px; margin: 10px 0;">
                    <p style="margin: 5px 0;">
                        <strong>우선순위 점수:</strong> 
                        <span style="color: {priority_color}; font-size: 20px; font-weight: bold;">
                            {score['total_score']}점
                        </span>
                        <span style="background: {priority_color}; color: white; padding: 3px 8px; border-radius: 3px; margin-left: 10px;">
                            {score['priority']}
                        </span>
                    </p>
                    
                    <p style="margin: 5px 0;">
                        <strong>발견된 주장:</strong> {score['claims_count']}개
                        (통계: {score['statistical_claims']}, 인과관계: {score['causal_claims']}, 극단: {score['extreme_claims']})
                    </p>
                </div>
                
                <h4>🔍 주요 주장</h4>
                <ul>
                    {claims_html}
                </ul>
                
                <p>
                    <a href="{item['url']}" style="background: #3498db; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        원문 보기 →
                    </a>
                </p>
            </div>
            """
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Malgun Gothic', Arial, sans-serif; line-height: 1.6; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; text-align: center; }}
                .summary {{ background: #f0f0f0; padding: 20px; border-radius: 10px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 일일 팩트체크 리포트</h1>
                    <p>{datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}</p>
                </div>
                
                <div class="summary">
                    <h2>📌 오늘의 요약</h2>
                    <p>
                        <strong>팩트체크 필요 기사:</strong> {len(articles)}건<br>
                        <strong>모니터링 상태:</strong> ✅ 정상
                    </p>
                </div>
                
                <h2>🎯 팩트체크 대상 기사</h2>
                {articles_html}
                
                <hr style="margin: 30px 0;">
                
                <div style="background: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107;">
                    <h3>💡 다음 단계</h3>
                    <ol>
                        <li>각 기사의 주장을 검증 가능한 데이터로 확인</li>
                        <li>정부 공식 통계 조회 (KOSIS, BOK, NTS)</li>
                        <li>데이터 대조 및 차트 생성</li>
                        <li>팩트체크 리포트 작성</li>
                    </ol>
                </div>
                
                <p style="color: #666; font-size: 12px; text-align: center; margin-top: 30px;">
                    이 이메일은 팩트체크 엔진에서 자동으로 발송되었습니다.<br>
                    매일 오전 9시에 전날의 뉴스를 분석하여 전송됩니다.
                </p>
            </div>
        </body>
        </html>
        """
        
        return html


def main():
    """메인 실행"""
    reporter = DailyEmailReporter()
    reporter.run_daily_report()


if __name__ == "__main__":
    main()
