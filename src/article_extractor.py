"""
기사 추출 모듈
URL에서 기사 본문, 제목, 발행일 등을 추출
"""

import trafilatura
import requests
from datetime import datetime
from typing import Dict, Optional


class ArticleExtractor:
    """기사 본문 추출기"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def extract(self, url: str) -> Optional[Dict[str, str]]:
        """
        URL에서 기사 정보 추출
        
        Args:
            url: 기사 URL
            
        Returns:
            {
                'url': 원본 URL,
                'title': 제목,
                'text': 본문,
                'date': 발행일,
                'source': 언론사
            }
        """
        try:
            # HTML 다운로드
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            html = response.text
            
            # Trafilatura로 본문 추출
            text = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=False,
                no_fallback=False
            )
            
            if not text:
                return None
            
            # 메타데이터 추출
            metadata = trafilatura.extract_metadata(html)
            
            return {
                'url': url,
                'title': metadata.title if metadata and metadata.title else 'Unknown',
                'text': text,
                'date': metadata.date if metadata and metadata.date else datetime.now().strftime('%Y-%m-%d'),
                'source': metadata.sitename if metadata and metadata.sitename else self._extract_domain(url),
                'journalist': self._extract_journalist(text)
            }
            
        except Exception as e:
            print(f"❌ 기사 추출 실패 ({url}): {e}")
            return None
    
    def _extract_domain(self, url: str) -> str:
        """URL에서 도메인 추출"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc

    def _extract_journalist(self, text: str) -> str:
        """기자 이름 추출"""
        import re
        # 패턴: "홍길동 기자", "박철수 특파원" (가장 먼저 발견되는 이름)
        match = re.search(r'([가-힣]{2,4})\s*(기자|특파원)', text)
        if match:
            return match.group(1)
        return "Unknown"


if __name__ == "__main__":
    # 테스트
    extractor = ArticleExtractor()
    
    # 예시 URL (실제 뉴스 사이트)
    test_url = "https://www.chosun.com/economy/2024/02/10/example/"
    
    print("기사 추출 테스트")
    print("=" * 60)
    
    result = extractor.extract(test_url)
    
    if result:
        print(f"✓ 제목: {result['title']}")
        print(f"✓ 언론사: {result['source']}")
        print(f"✓ 발행일: {result['date']}")
        print(f"✓ 본문 길이: {len(result['text'])} 글자")
        print()
        print("본문 미리보기:")
        print(result['text'][:200] + "...")
    else:
        print("❌ 추출 실패")
