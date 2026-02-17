"""
RSS 모니터링 모듈 (Option A)
주요 언론사 RSS 피드를 수집하고 팩트체크 대상 필터링
"""

import feedparser
import sqlite3
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from article_extractor import ArticleExtractor
from claim_detector import ClaimDetector
from priority_scorer import PriorityScorer


class RSSMonitor:
    """RSS 피드 모니터"""
    
    # 주요 언론사 RSS 피드
    RSS_FEEDS = {
        '구글_정치': 'https://news.google.com/rss/headlines/section/topic/POLITICS?hl=ko&gl=KR&ceid=KR:ko',
        '구글_경제': 'https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko',
        '구글_사회': 'https://news.google.com/rss/headlines/section/topic/NATION?hl=ko&gl=KR&ceid=KR:ko',
    }
    
    # 관심 키워드
    KEYWORDS = [
        '통계', '조사', '발표', '증가', '감소', '상승', '하락',
        '세금', '월세', '전세', '부동산', '응급실', '사망',
        '경제성장률', 'GDP', '부채', '금리', '물가'
    ]
    
    def __init__(self, db_path='data/articles.db'):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        
        self.extractor = ArticleExtractor()
        self.detector = ClaimDetector()
        self.scorer = PriorityScorer()
    
    def _init_db(self):
        """데이터베이스 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                title TEXT,
                source TEXT,
                published_date TEXT,
                collected_date TEXT,
                priority_score INTEGER,
                should_factcheck BOOLEAN,
                analyzed BOOLEAN DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def collect_feeds(self):
        """RSS 피드 수집"""
        print("=" * 70)
        print(f"RSS 피드 수집 시작 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        print()
        
        total_articles = 0
        keyword_matched = 0
        high_priority = 0
        
        # User-Agent 설정 (네이버 차단 방지)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        import requests
        
        for feed_name, feed_url in self.RSS_FEEDS.items():
            print(f"📡 {feed_name} 수집 중...")
            
            try:
                # requests로 먼저 데이터 가져오기
                response = requests.get(feed_url, headers=headers, timeout=10)
                response.raise_for_status()
                
                # feedparser로 파싱
                feed = feedparser.parse(response.text)
                articles = feed.entries
                
                print(f"  ✓ {len(articles)}개 기사 발견")
                total_articles += len(articles)
                
                for entry in articles:
                    # 키워드 필터링
                    title = entry.get('title', '')
                    summary = entry.get('summary', '')
                    
                    if self._has_keyword(title + ' ' + summary):
                        keyword_matched += 1
                        
                        # DB에 저장
                        url = entry.get('link', '')
                        published = entry.get('published', datetime.now().strftime('%Y-%m-%d'))
                        
                        if self._save_article(url, title, feed_name, published):
                            high_priority += 1
                
            except Exception as e:
                print(f"  ❌ 수집 실패: {e}")
            
            print()
        
        print("=" * 70)
        print("수집 완료")
        print(f"  • 총 기사: {total_articles}개")
        print(f"  • 키워드 매칭: {keyword_matched}개")
        print(f"  • 팩트체크 대상: {high_priority}개")
        print("=" * 70)
        print()
    
    def _has_keyword(self, text: str) -> bool:
        """키워드 포함 여부"""
        for keyword in self.KEYWORDS:
            if keyword in text:
                return True
        return False
    
    def _save_article(self, url: str, title: str, source: str, published: str) -> bool:
        """기사 저장 및 우선순위 계산"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 중복 체크
            cursor.execute('SELECT id FROM articles WHERE url = ?', (url,))
            if cursor.fetchone():
                return False
            
            # 간단한 우선순위 계산 (제목만으로)
            # 실제 본문 분석은 나중에 별도로 수행
            score = 0
            if any(kw in title for kw in ['증가', '감소', '폭증', '급증']):
                score += 30
            if any(kw in title for kw in ['통계', '조사', '발표']):
                score += 20
            
            should_factcheck = score >= 30
            
            cursor.execute('''
                INSERT INTO articles (url, title, source, published_date, collected_date, priority_score, should_factcheck)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (url, title, source, published, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), score, should_factcheck))
            
            conn.commit()
            return should_factcheck
            
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def get_pending_articles(self, limit=10):
        """분석 대기 중인 기사 조회"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT url, title, source, priority_score
            FROM articles
            WHERE should_factcheck = 1 AND analyzed = 0
            ORDER BY priority_score DESC
            LIMIT ?
        ''', (limit,))
        
        articles = cursor.fetchall()
        conn.close()
        
        return articles


def main():
    """메인 실행"""
    monitor = RSSMonitor()
    monitor.collect_feeds()
    
    # 대기 중인 기사 표시
    pending = monitor.get_pending_articles()
    
    if pending:
        print()
        print("📋 팩트체크 대기 목록")
        print("-" * 70)
        
        for i, (url, title, source, score) in enumerate(pending, 1):
            print(f"\n[{i}] {title}")
            print(f"    언론사: {source} | 점수: {score}점")
            print(f"    URL: {url}")
        
        print()
        print("-" * 70)


if __name__ == "__main__":
    main()
