"""
통계 주장 탐지 모듈
기사 본문에서 팩트체크 가능한 통계적 주장을 추출
"""

import re
from typing import List, Dict


class ClaimDetector:
    """통계적 주장 탐지기"""
    
    def __init__(self):
        # 통계 패턴 (숫자 + 단위 + 주장)
        self.stat_patterns = [
            r'(\d+(?:\.\d+)?)\s*배\s*(증가|감소|상승|하락)',
            r'(\d+(?:\.\d+)?)\s*%\s*(증가|감소|상승|하락|돌파)',
            r'(\d+(?:\.\d+)?)\s*조\s*원',
            r'(\d+(?:\.\d+)?)\s*억\s*원',
            r'전년\s*대비\s*(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*명\s*(증가|감소|사망)',
            r'(\d+(?:\.\d+)?)\s*건\s*(증가|감소|발생)',
            r'사상\s*(최대|최고|최저)',
            r'역대\s*(최대|최고|최저)',
        ]
        
        # 인과관계 표현
        self.causal_patterns = [
            r'(.+?)\s*(때문에|탓에)\s*(.+)',
            r'(.+?)\s*(영향으로|여파로)\s*(.+)',
            r'(.+?)\s*(?:가|이)\s*(.+?)\s*(?:초래|유발)',
        ]
        
        # 극단적 표현
        self.extreme_words = [
            '폭증', '급증', '급감', '폭락', '급락',
            '사상 최대', '사상 최고', '역대 최대', '역대 최고',
            '기록적', '전례없는', '유례없는'
        ]
        
        # 불확실 표현 (출처 불명확)
        self.vague_patterns = [
            r'(?:것으로|인|이)\s*알려졌다',
            r'(?:것으로|인|이)\s*보인다',
            r'(?:것으로|인|이)\s*추정된다',
            r'(?:것으로|인|이)\s*전해졌다',
        ]
    
    def detect(self, text: str) -> List[Dict[str, any]]:
        """
        본문에서 통계 주장 추출
        
        Args:
            text: 기사 본문
            
        Returns:
            [
                {
                    'claim': '추출된 주장',
                    'type': 'statistical' | 'causal' | 'extreme',
                    'confidence': 'HIGH' | 'MEDIUM' | 'LOW'
                }
            ]
        """
        claims = []
        
        # 1. 통계적 주장 탐지
        for pattern in self.stat_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                # 주변 문맥 추출 (앞뒤 30자)
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                context = text[start:end].strip()
                
                claims.append({
                    'claim': context,
                    'type': 'statistical',
                    'confidence': 'HIGH',
                    'matched_text': match.group(0)
                })
        
        # 2. 인과관계 주장 탐지
        for pattern in self.causal_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                claims.append({
                    'claim': match.group(0),
                    'type': 'causal',
                    'confidence': 'MEDIUM',
                    'matched_text': match.group(0)
                })
        
        # 3. 극단적 표현 탐지
        for word in self.extreme_words:
            if word in text:
                # 해당 단어 주변 문맥 추출
                idx = text.find(word)
                start = max(0, idx - 30)
                end = min(len(text), idx + len(word) + 30)
                context = text[start:end].strip()
                
                claims.append({
                    'claim': context,
                    'type': 'extreme',
                    'confidence': 'MEDIUM',
                    'matched_text': word
                })
        
        # 중복 제거 (유사한 주장)
        unique_claims = self._deduplicate(claims)
        
        return unique_claims
    
    def _deduplicate(self, claims: List[Dict]) -> List[Dict]:
        """유사한 주장 중복 제거"""
        if not claims:
            return []
        
        unique = []
        seen_texts = set()
        
        for claim in claims:
            # 매칭된 텍스트 기준으로 중복 체크
            matched = claim['matched_text']
            if matched not in seen_texts:
                seen_texts.add(matched)
                unique.append(claim)
        
        return unique
    
    def has_vague_source(self, text: str) -> bool:
        """출처 불명확 표현 포함 여부"""
        for pattern in self.vague_patterns:
            if re.search(pattern, text):
                return True
        return False


if __name__ == "__main__":
    # 테스트
    detector = ClaimDetector()
    
    test_text = """
    의료파업으로 응급실 사망자가 3배 증가한 것으로 알려졌다.
    보건복지부에 따르면 2024년 2월부터 7월까지 응급실 내원 환자 중 
    사망자 수는 22,732명으로 전년 대비 소폭 감소했다.
    그러나 전원 거부 건수는 110,033건으로 전년 대비 88% 급증했다.
    이는 사상 최대 규모다.
    """
    
    print("통계 주장 탐지 테스트")
    print("=" * 60)
    print(f"본문:\n{test_text}\n")
    
    claims = detector.detect(test_text)
    
    print(f"✓ 발견된 주장: {len(claims)}개\n")
    
    for i, claim in enumerate(claims, 1):
        print(f"[주장 {i}] ({claim['type'].upper()})")
        print(f"  내용: {claim['claim'][:80]}...")
        print(f"  신뢰도: {claim['confidence']}")
        print()
    
    # 불확실 표현 체크
    has_vague = detector.has_vague_source(test_text)
    print(f"출처 불명확 표현: {'있음' if has_vague else '없음'}")
