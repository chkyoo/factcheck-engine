"""
뉴스 크롤러 모듈 (Option C)
주요 뉴스 사이트를 크롤링하여 팩트체크 대상 자동 발견
"""

import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from article_extractor import ArticleExtractor
from claim_detector import ClaimDetector
from priority_scorer import PriorityScorer


class NewsCrawler:
    """뉴스 크롤러"""
    
    # 크롤링 대상 사이트
    TARGET_SITES = {
        '네이버_뉴스_정치': 'https://news.naver.com/section/100',
        '네이버_뉴스_경제': 'https://news.naver.com/section/101',
    }
    
    def __init__(self, rate_limit=1.0):
        """
        Args:
            rate_limit: 요청 간 대기 시간 (초)
        """
        self.rate_limit = rate_limit
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        self.extractor = ArticleExtractor()
        self.detector = ClaimDetector()
        self.scorer = PriorityScorer()
    
    def crawl_all(self):
        """모든 사이트 크롤링"""
        print("=" * 70)
        print(f"뉴스 크롤링 시작 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        print()
        
        all_articles = []
        
        for site_name, site_url in self.TARGET_SITES.items():
            print(f"🕷️  {site_name} 크롤링 중...")
            
            try:
                articles = self._crawl_naver_section(site_url)
                all_articles.extend(articles)
                print(f"  ✓ {len(articles)}개 기사 URL 수집")
                
            except Exception as e:
                print(f"  ❌ 크롤링 실패: {e}")
            
            # Rate limiting
            time.sleep(self.rate_limit)
            print()
        
        print("=" * 70)
        print(f"총 {len(all_articles)}개 기사 URL 수집 완료")
        print("=" * 70)
        print()
        
        return all_articles
    
    def _crawl_naver_section(self, url: str) -> list:
        """네이버 뉴스 섹션 크롤링"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 기사 링크 추출 (네이버 뉴스 구조에 맞게 조정 필요)
            article_links = []
            
            # 예시: a 태그에서 기사 링크 추출
            for link in soup.find_all('a', href=True):
                href = link['href']
                if 'news.naver.com' in href and '/article/' in href:
                    article_links.append(href)
            
            # 중복 제거
            article_links = list(set(article_links))
            
            return article_links[:20]  # 최대 20개만
            
        except Exception as e:
            print(f"  ⚠️  크롤링 오류: {e}")
            return []
    
    def analyze_articles(self, article_urls: list, max_analyze=5):
        """수집된 기사 분석"""
        print()
        print("📊 기사 분석 시작")
        print("-" * 70)
        print()
        
        high_priority_articles = []
        
        for i, url in enumerate(article_urls[:max_analyze], 1):
            print(f"[{i}/{min(max_analyze, len(article_urls))}] 분석 중...")
            
            try:
                # 기사 추출
                article = self.extractor.extract(url)
                if not article:
                    print(f"  ❌ 추출 실패: {url}")
                    continue
                
                # 주장 탐지
                claims = self.detector.detect(article['text'])
                has_vague = self.detector.has_vague_source(article['text'])
                
                # 우선순위 계산
                score_result = self.scorer.calculate_score(article, claims, has_vague)
                
                print(f"  ✓ {article['title'][:40]}...")
                print(f"    점수: {score_result['total_score']}점 | 우선순위: {score_result['priority']}")
                
                if score_result['should_factcheck']:
                    high_priority_articles.append({
                        'url': url,
                        'article': article,
                        'claims': claims,
                        'score': score_result
                    })
                    print(f"    🎯 팩트체크 대상!")
                
            except Exception as e:
                print(f"  ❌ 분석 실패: {e}")
            
            # Rate limiting
            time.sleep(self.rate_limit)
            print()
        
        print("-" * 70)
        print(f"✅ 분석 완료: {len(high_priority_articles)}개 팩트체크 대상 발견")
        print()
        
        return high_priority_articles


def main():
    """메인 실행"""
    crawler = NewsCrawler(rate_limit=1.0)
    
    # 1. 크롤링
    article_urls = crawler.crawl_all()
    
    if not article_urls:
        print("❌ 수집된 기사가 없습니다.")
        return
    
    # 2. 분석
    high_priority = crawler.analyze_articles(article_urls, max_analyze=5)
    
    # 3. 결과 출력
    if high_priority:
        print()
        print("📋 팩트체크 대상 목록")
        print("=" * 70)
        
        for i, item in enumerate(high_priority, 1):
            article = item['article']
            score = item['score']
            
            print(f"\n[{i}] {article['title']}")
            print(f"    언론사: {article['source']}")
            print(f"    점수: {score['total_score']}점 ({score['priority']})")
            print(f"    주장 수: {score['claims_count']}개")
            print(f"    URL: {item['url']}")
        
        print()
        print("=" * 70)


if __name__ == "__main__":
    main()
