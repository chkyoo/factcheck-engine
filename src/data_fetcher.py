"""
데이터 수집 모듈
정부 공식 통계 API에서 데이터를 가져옵니다.
"""

import requests
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime


class KOSISFetcher:
    """국가통계포털(KOSIS) 데이터 수집기"""
    
    BASE_URL = "https://kosis.kr/openapi"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: KOSIS API 인증키 (https://kosis.kr/openapi/index/index.jsp 에서 발급)
        """
        self.api_key = api_key
    
    def fetch_rental_stats(self, start_year: int = 2020, end_year: int = 2024) -> pd.DataFrame:
        """
        전월세 거래 통계 수집
        
        Args:
            start_year: 시작 연도
            end_year: 종료 연도
            
        Returns:
            DataFrame with columns: year, jeonse_ratio, monthly_rent_ratio
        """
        # TODO: 실제 KOSIS API 호출 구현
        # 현재는 더미 데이터 반환
        data = {
            'year': [2020, 2021, 2022, 2023, 2024],
            'jeonse_ratio': [55.2, 52.1, 48.3, 43.4, 40.0],
            'monthly_rent_ratio': [44.8, 47.9, 51.7, 56.6, 60.0]
        }
        return pd.DataFrame(data)


class BOKFetcher:
    """한국은행 경제통계시스템(ECOS) 데이터 수집기"""
    
    BASE_URL = "https://ecos.bok.or.kr/api"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: ECOS API 인증키 (https://ecos.bok.or.kr 에서 발급)
        """
        self.api_key = api_key
    
    def fetch_interest_rates(self, start_date: str = "202001", end_date: str = "202412") -> pd.DataFrame:
        """
        주택담보대출 금리 추이 수집
        
        Args:
            start_date: 시작일 (YYYYMM)
            end_date: 종료일 (YYYYMM)
            
        Returns:
            DataFrame with columns: date, mortgage_rate
        """
        # TODO: 실제 ECOS API 호출 구현
        # 현재는 더미 데이터 반환
        data = {
            'date': ['2020-12', '2021-12', '2022-12', '2023-12', '2024-12'],
            'mortgage_rate': [2.75, 3.10, 4.85, 4.50, 4.52]
        }
        return pd.DataFrame(data)
    
    def fetch_household_debt(self, start_year: int = 2020, end_year: int = 2024) -> pd.DataFrame:
        """
        가계부채 잔액 추이 수집
        
        Args:
            start_year: 시작 연도
            end_year: 종료 연도
            
        Returns:
            DataFrame with columns: year, debt_trillion_krw
        """
        # TODO: 실제 ECOS API 호출 구현
        data = {
            'year': [2020, 2021, 2022, 2023, 2024],
            'debt_trillion_krw': [1630, 1765, 1860, 1886, 1927]
        }
        return pd.DataFrame(data)


class NTSFetcher:
    """국세청 통계 수집기"""
    
    def fetch_property_tax_stats(self, start_year: int = 2020, end_year: int = 2024) -> pd.DataFrame:
        """
        종합부동산세 징수액 추이
        
        Args:
            start_year: 시작 연도
            end_year: 종료 연도
            
        Returns:
            DataFrame with columns: year, tax_billion_krw
        """
        # TODO: 국세청 통계연보 크롤링 또는 공공데이터 API 활용
        # 현재는 더미 데이터 (실제 추세 반영)
        data = {
            'year': [2020, 2021, 2022, 2023, 2024],
            'tax_billion_krw': [3300, 6100, 4200, 2800, 2500]  # 2022년 이후 감소 추세
        }
        return pd.DataFrame(data)


if __name__ == "__main__":
    # 테스트 실행
    print("=== 데이터 수집 테스트 ===\n")
    
    kosis = KOSISFetcher()
    rental_data = kosis.fetch_rental_stats()
    print("전월세 거래 비중:")
    print(rental_data)
    print()
    
    bok = BOKFetcher()
    interest_data = bok.fetch_interest_rates()
    print("주택담보대출 금리:")
    print(interest_data)
    print()
    
    debt_data = bok.fetch_household_debt()
    print("가계부채:")
    print(debt_data)
    print()
    
    nts = NTSFetcher()
    tax_data = nts.fetch_property_tax_stats()
    print("종합부동산세:")
    print(tax_data)
