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
from difflib import SequenceMatcher
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
        
        # 1. RSS 수집 (수동 모드 체크)
        manual_url = os.getenv('ARTICLE_URL')
        if manual_url:
            print(f"🔧 수동 검증 모드: {manual_url}")
            # 가짜 RSS 엔트리 생성
            pending_articles = [(manual_url, "수동 입력 기사 (제목 분석 중)", "User Input", 100)]
        else:
            print("📡 1단계: RSS 피드 수집 중...")
            self.rss_monitor.collect_feeds()
            
            # 2. 팩트체크 대상 조회 (더 많은 기사를 가져와서 중복 제거)
            print("🔍 2단계: 팩트체크 대상 분석 중...")
            pending_articles = self.rss_monitor.get_pending_articles(limit=20)
        
        if not pending_articles:
            print("ℹ️  오늘은 팩트체크 대상 기사가 없습니다.")
            self._send_no_articles_email()
            return
        
        # 3. 상세 분석
        print(f"📊 3단계: {len(pending_articles)}개 기사 상세 분석 중...")
        analyzed_articles = []
        
        for url, title, source, score in pending_articles:
            try:
                article = self.extractor.extract(url)
                if not article:
                    print(f"  ⚠️ 본문 추출 실패: {url}")
                    article = {
                        'title': title,
                        'text': '',
                        'source': source,
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'journalist': 'Unknown'
                    }
                
                print(f"  📄 본문 길이: {len(article.get('text', ''))}자 | 기자: {article.get('journalist', 'Unknown')}")
                
                claims = self.detector.detect(article['text'])
                has_vague = self.detector.has_vague_source(article['text'])
                score_result = self.scorer.calculate_score(article, claims, has_vague)
                
                if manual_url or score_result['should_factcheck']:
                    analyzed_articles.append({
                        'url': url,
                        'article': article,
                        'claims': claims,
                        'score': score_result
                    })
                    print(f"  ✓ {article.get('title', title)[:30]}... ({score_result['total_score']}점)")
                
            except Exception as e:
                print(f"  ❌ 분석 실패: {e}")
        
        # 3.5 중복 제거
        if analyzed_articles:
            print(f"\n🗑️ 중복 제거 전: {len(analyzed_articles)}건")
            final_articles = self._deduplicate_articles(analyzed_articles)
            print(f"✨ 중복 제거 후: {len(final_articles)}건")
            
            # 3.6 기자 통계 업데이트 (최종 선정된 기사에 대해서만)
            for item in final_articles:
                journalist = item['article'].get('journalist')
                source = item['article'].get('source')
                if journalist and journalist != 'Unknown':
                    self.rss_monitor.update_journalist_stats(journalist, source)
                    print(f"  📈 기자 통계 업데이트: {journalist} ({source})")
        else:
            final_articles = []

        # 4. 이메일 전송
        if final_articles:
            print(f"\n📧 4단계: 이메일 전송 중... ({len(final_articles)}개 기사)")
            self._send_factcheck_email(final_articles)
            print("✅ 이메일 전송 완료!")
        else:
            print("\nℹ️  상세 분석 결과 팩트체크 대상이 없습니다.")
            self._send_no_articles_email()
    
    def _deduplicate_articles(self, articles):
        """기사 중복 제거 및 관련 기사 그룹화"""
        unique_articles = []
        skip_indices = set()
        
        # 날짜순 정렬 (오래된 기사 우선 = 원본 추정)
        # 날짜 형식이 제각각일 수 있으므로 주의 필요 (여기서는 일단 문자열 정렬)
        sorted_articles = sorted(articles, key=lambda x: x['article']['date'])
        
        for i in range(len(sorted_articles)):
            if i in skip_indices:
                continue
                
            current = sorted_articles[i]
            group = [current]
            
            for j in range(i + 1, len(sorted_articles)):
                if j in skip_indices:
                    continue
                
                compare = sorted_articles[j]
                
                # 제목 유사도 비교
                similarity = SequenceMatcher(None, current['article']['title'], compare['article']['title']).ratio()
                
                if similarity > 0.6:  # 60% 이상 비슷하면 같은 이슈로 간주
                    group.append(compare)
                    skip_indices.add(j)
            
            # 그룹 처리
            selected = group[0]  # 가장 빠른 기사
            selected['related_count'] = len(group) - 1
            # 관련 기사 정보 저장 (언론사, 시간, 기자)
            selected['related_info'] = [
                f"{item['article']['source']} ({item['article'].get('journalist', 'Unknown')})" 
                for item in group[1:]
            ]
            
            unique_articles.append(selected)
            
        # 최대 5개까지만 리포트
        return unique_articles[:5]

    def _add_manual_link_footer(self, html_content):
        """이메일 하단에 수동 검증 링크 추가"""
        footer_link = '''
            <div style="margin-top: 30px; text-align: center; padding: 20px; background: #f9f9f9; border-radius: 10px;">
                <p><strong>직접 기사를 검증하고 싶으신가요?</strong></p>
                <a href="https://github.com/chkyoo/factcheck-engine/actions/workflows/daily-factcheck.yml" 
                   style="background: #2dba4e; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                   👉 수동 검증 하러가기
                </a>
                <p style="font-size: 12px; color: #666; margin-top: 10px;">GitHub Actions > Run workflow 버튼을 눌러 URL을 입력하세요.</p>
            </div>
        '''
        return html_content.replace('</body>', f'{footer_link}</body>')

    def _send_factcheck_email(self, articles):
        """팩트체크 리포트 이메일 전송"""
        html_content = self._generate_html_report(articles)
        html_content = self._add_manual_link_footer(html_content)
        
        msg = MIMEMultipart('alternative')
        
        if os.getenv('ARTICLE_URL'):
            msg['Subject'] = f"🔧 수동 팩트체크 리포트 - {datetime.now().strftime('%Y년 %m월 %d일')}"
            footer_text = "이 리포트는 사용자의 요청에 의해 수동으로 생성되었습니다."
        else:
            msg['Subject'] = f"📊 일일 팩트체크 리포트 - {datetime.now().strftime('%Y년 %m월 %d일')}"
            footer_text = "이 이메일은 팩트체크 엔진에서 자동으로 발송되었습니다."

        msg['From'] = self.sender_email
        msg['To'] = self.recipient_email
        
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        
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
                </div>
            </div>
        </body>
        </html>
        """
        html_content = self._add_manual_link_footer(html_content)
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"📊 일일 팩트체크 리포트 - {datetime.now().strftime('%Y년 %m월 %d일')} (대상 없음)"
        msg['From'] = self.sender_email
        msg['To'] = self.recipient_email
        
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        
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
        # 우수 기자 순위 가져오기
        top_journalists = self.rss_monitor.get_top_journalists(limit=3)
        journalist_table = ""
        
        if top_journalists:
            journalist_rows = ""
            for i, (name, aff, count) in enumerate(top_journalists, 1):
                icon = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else str(i)
                journalist_rows += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">{icon} <strong>{name}</strong> ({aff})</td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;">{count}건</td>
                </tr>
                """
        else:
            journalist_rows = """
            <tr>
                <td colspan="2" style="padding: 15px; text-align: center; color: #666;">
                    🌱 아직 데이터가 충분하지 않습니다.<br>
                    (오늘부터 기자별 통계가 누적되기 시작합니다!)
                </td>
            </tr>
            """
            
        journalist_table = f"""
        <div style="margin: 20px 0; padding: 15px; background: #fff; border: 1px solid #e1e4e8; border-radius: 8px;">
            <h3 style="margin-top: 0; margin-bottom: 15px; color: #24292e;">🏆 이달의 팩트체크 기자 (Hall of Fame)</h3>
            <table style="width: 100%; border-collapse: collapse;">
                {journalist_rows}
            </table>
        </div>
        """

        articles_html = ""
        
        for i, item in enumerate(articles, 1):
            article = item['article']
            claims = item['claims']
            score = item['score']
            
            # 관련 기사 표시
            related_html = ""
            if item.get('related_count', 0) > 0:
                related_sources = ', '.join(item['related_info'])
                related_html = f"""
                <div style="margin-top: 10px; padding: 10px; background: #f1f8ff; border-radius: 5px; font-size: 13px; color: #0366d6;">
                    <strong>🔗 관련 보도 ({item['related_count']}건):</strong> {related_sources} 등
                </div>
                """
            
            # 주장 목록 HTML
            claims_html = ""
            for j, claim in enumerate(claims[:3], 1):  # 최대 3개
                claim_type = {
                    'statistical': '📊 통계',
                    'causal': '🔗 인과관계',
                    'extreme': '⚠️ 극단 표현'
                }.get(claim['type'], claim['type'])
                claims_html += f"<li><strong>[{claim_type}]</strong> {claim['claim'][:100]}...<br><small>신뢰도: {claim['confidence']}</small></li>"
            
            priority_color = {'HIGH': '#e74c3c', 'MEDIUM': '#f39c12', 'LOW': '#95a5a6'}.get(score['priority'], '#95a5a6')
            
            articles_html += f"""
            <div style="border: 1px solid #ddd; border-radius: 10px; padding: 20px; margin-bottom: 20px; background: #f9f9f9;">
                <h3 style="margin-top: 0;">[{i}] {article['title']}</h3>
                <p style="color: #666;">
                    <strong>언론사:</strong> {article['source']} | 
                    <strong>기자:</strong> {article.get('journalist', 'Unknown')} |
                    <strong>발행일:</strong> {article['date']}
                </p>
                {related_html}
                
                <div style="background: white; padding: 15px; border-radius: 5px; margin: 10px 0;">
                    <p style="margin: 5px 0;">
                        <strong>우선순위 점수:</strong> 
                        <span style="color: {priority_color}; font-size: 20px; font-weight: bold;">{score['total_score']}점</span>
                        <span style="background: {priority_color}; color: white; padding: 3px 8px; border-radius: 3px; margin-left: 10px;">{score['priority']}</span>
                    </p>
                    <p style="margin: 5px 0;"><strong>발견된 주장:</strong> {score['claims_count']}개</p>
                </div>
                
                <h4>🔍 주요 주장</h4>
                <ul>{claims_html}</ul>
                <p><a href="{item['url']}" style="background: #3498db; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px; display: inline-block;">원문 보기 →</a></p>
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

                {journalist_table}
                
                <h2>🎯 팩트체크 대상 기사 (최초 보도 우선)</h2>
                {articles_html}
                
                <hr style="margin: 30px 0;">
                
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
