# Fact-Check Engine (팩트체크 생성기)

## 목적
뉴스 기사의 통계적 주장을 정부 공식 데이터와 자동 대조하여 반박 자료를 생성하는 도구

## 핵심 기능
1. **데이터 수집기 (Data Fetcher)**
   - KOSIS (국가통계포털) API 연동
   - 한국은행 경제통계 API 연동
   - 국토부 부동산 통계 크롤링

2. **주장 분석기 (Claim Analyzer)**
   - 기사 URL 입력 → 핵심 통계 주장 추출
   - 키워드 매칭 (예: "월세 상승" → 전월세 통계 검색)

3. **반박 생성기 (Rebuttal Generator)**
   - 공식 데이터 vs 기사 주장 비교
   - 차트 자동 생성 (matplotlib)
   - 마크다운 리포트 출력

4. **일일 이메일 리포터**
   - 매일 자동으로 뉴스 모니터링
   - 팩트체크 필요 기사 이메일 발송
   - GitHub Actions로 24/7 자동 실행

## 배포 방법

### 로컬 실행
```bash
python daily_email_reporter.py
```

### GitHub Actions (클라우드)
컴퓨터가 꺼져 있어도 매일 자동 실행!
자세한 내용: [GITHUB_DEPLOY.md](GITHUB_DEPLOY.md)

## 기술 스택
- Python 3.10+
- requests (API 호출)
- pandas (데이터 처리)
- matplotlib (차트 생성)
- beautifulsoup4 (웹 크롤링)
- GitHub Actions (자동화)

## 첫 번째 타겟
"보유세 인상 → 월세 폭등" 주장 검증
- 데이터: 종부세 징수액 추이 vs 월세 거래 비중 추이 (2020-2024)
