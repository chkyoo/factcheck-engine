"""
우선순위 점수 계산 모듈
팩트체크 필요도를 점수화
"""

from typing import Dict, List


class PriorityScorer:
    """팩트체크 우선순위 점수 계산기"""
    
    # 점수 가중치
    WEIGHTS = {
        'statistical_claim': 30,      # 통계 주장 포함
        'causal_claim': 20,            # 인과관계 주장
        'extreme_language': 15,        # 극단적 표현
        'vague_source': 25,            # 출처 불명확
        'political_economic': 10,      # 정치/경제 이슈
    }
    
    THRESHOLD = 30  # 팩트체크 대상 임계값
    
    def __init__(self):
        self.political_keywords = [
            '정부', '정책', '국회', '대통령', '장관',
            '여당', '야당', '선거', '법안'
        ]
        
        self.economic_keywords = [
            '경제', 'GDP', '성장률', '물가', '금리',
            '부채', '세금', '월세', '전세', '주택',
            '실업', '고용', '임금', '소득'
        ]
    
    def calculate_score(
        self, 
        article: Dict[str, str],
        claims: List[Dict[str, any]],
        has_vague_source: bool
    ) -> Dict[str, any]:
        """
        팩트체크 우선순위 점수 계산
        
        Args:
            article: {'title': ..., 'text': ...}
            claims: ClaimDetector.detect() 결과
            has_vague_source: 출처 불명확 여부
            
        Returns:
            {
                'total_score': 총점,
                'breakdown': {항목별 점수},
                'should_factcheck': True/False,
                'priority': 'HIGH' | 'MEDIUM' | 'LOW'
            }
        """
        score = 0
        breakdown = {}
        
        # 1. 통계 주장 포함 여부
        stat_claims = [c for c in claims if c['type'] == 'statistical']
        if stat_claims:
            points = self.WEIGHTS['statistical_claim']
            score += points
            breakdown['statistical_claim'] = points
        
        # 2. 인과관계 주장
        causal_claims = [c for c in claims if c['type'] == 'causal']
        if causal_claims:
            points = self.WEIGHTS['causal_claim']
            score += points
            breakdown['causal_claim'] = points
        
        # 3. 극단적 표현
        extreme_claims = [c for c in claims if c['type'] == 'extreme']
        if extreme_claims:
            points = self.WEIGHTS['extreme_language']
            score += points
            breakdown['extreme_language'] = points
        
        # 4. 출처 불명확
        if has_vague_source:
            points = self.WEIGHTS['vague_source']
            score += points
            breakdown['vague_source'] = points
        
        # 5. 정치/경제 이슈
        text = article.get('text', '') + ' ' + article.get('title', '')
        if self._is_political_or_economic(text):
            points = self.WEIGHTS['political_economic']
            score += points
            breakdown['political_economic'] = points
        
        # 6. 제목 키워드 보너스 (강한 어조)
        title = article.get('title', '')
        if any(kw in title for kw in ['증가', '감소', '폭증', '급증', '하락', '최대', '최저', '역대']):
            points = 20
            score += points
            breakdown['title_keyword'] = points
        
        # 우선순위 판단
        should_factcheck = score >= self.THRESHOLD
        
        if score >= 85:
            priority = 'HIGH'
        elif score >= 70:
            priority = 'MEDIUM'
        else:
            priority = 'LOW'
        
        return {
            'total_score': score,
            'breakdown': breakdown,
            'should_factcheck': should_factcheck,
            'priority': priority,
            'claims_count': len(claims),
            'statistical_claims': len(stat_claims),
            'causal_claims': len(causal_claims),
            'extreme_claims': len(extreme_claims)
        }
    
    def _is_political_or_economic(self, text: str) -> bool:
        """정치/경제 관련 기사 여부"""
        # 정치 키워드 체크
        for keyword in self.political_keywords:
            if keyword in text:
                return True
        
        # 경제 키워드 체크
        for keyword in self.economic_keywords:
            if keyword in text:
                return True
        
        return False


if __name__ == "__main__":
    # 테스트
    scorer = PriorityScorer()
    
    # 테스트 기사
    test_article = {
        'title': '의료파업으로 응급실 사망자 3배 증가',
        'text': '''
        의료파업으로 응급실 사망자가 3배 증가한 것으로 알려졌다.
        보건복지부에 따르면 2024년 2월부터 7월까지 응급실 내원 환자 중 
        사망자 수는 22,732명으로 전년 대비 소폭 감소했다.
        그러나 전원 거부 건수는 110,033건으로 전년 대비 88% 급증했다.
        이는 사상 최대 규모다.
        '''
    }
    
    # 테스트 주장
    test_claims = [
        {'claim': '사망자 3배 증가', 'type': 'statistical', 'confidence': 'HIGH'},
        {'claim': '88% 급증', 'type': 'statistical', 'confidence': 'HIGH'},
        {'claim': '사상 최대', 'type': 'extreme', 'confidence': 'MEDIUM'},
        {'claim': '의료파업으로 사망자 증가', 'type': 'causal', 'confidence': 'MEDIUM'},
    ]
    
    test_vague = True  # "것으로 알려졌다" 포함
    
    print("우선순위 점수 계산 테스트")
    print("=" * 60)
    
    result = scorer.calculate_score(test_article, test_claims, test_vague)
    
    print(f"총점: {result['total_score']}점")
    print(f"팩트체크 필요: {'✅ 예' if result['should_factcheck'] else '❌ 아니오'}")
    print(f"우선순위: {result['priority']}")
    print()
    
    print("점수 세부내역:")
    for category, points in result['breakdown'].items():
        print(f"  • {category}: {points}점")
    print()
    
    print("주장 통계:")
    print(f"  • 총 주장 수: {result['claims_count']}개")
    print(f"  • 통계 주장: {result['statistical_claims']}개")
    print(f"  • 인과관계: {result['causal_claims']}개")
    print(f"  • 극단 표현: {result['extreme_claims']}개")
