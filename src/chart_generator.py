"""
차트 생성 모듈
데이터를 시각화하여 반박 자료로 활용합니다.
"""

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd
from pathlib import Path
from typing import Optional


# 한글 폰트 설정 (Windows 기준)
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False


class ChartGenerator:
    """팩트체크용 차트 생성기"""
    
    def __init__(self, output_dir: str = "output"):
        """
        Args:
            output_dir: 차트 저장 디렉토리
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def create_tax_vs_rent_chart(
        self,
        tax_data: pd.DataFrame,
        rent_data: pd.DataFrame,
        filename: str = "tax_vs_rent.png"
    ) -> str:
        """
        '세금 감소 vs 월세 증가' 비교 차트 생성
        
        Args:
            tax_data: 종부세 데이터 (columns: year, tax_billion_krw)
            rent_data: 월세 비중 데이터 (columns: year, monthly_rent_ratio)
            filename: 저장할 파일명
            
        Returns:
            저장된 파일 경로
        """
        fig, ax1 = plt.subplots(figsize=(12, 6))
        
        # 왼쪽 Y축: 종부세 (막대 그래프)
        color = 'tab:red'
        ax1.set_xlabel('연도', fontsize=12)
        ax1.set_ylabel('종합부동산세 (조 원)', color=color, fontsize=12)
        bars = ax1.bar(
            tax_data['year'],
            tax_data['tax_billion_krw'] / 1000,  # 조 단위로 변환
            color=color,
            alpha=0.6,
            label='종부세 징수액'
        )
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.set_ylim(0, max(tax_data['tax_billion_krw'] / 1000) * 1.3)
        
        # 오른쪽 Y축: 월세 비중 (선 그래프)
        ax2 = ax1.twinx()
        color = 'tab:blue'
        ax2.set_ylabel('월세 거래 비중 (%)', color=color, fontsize=12)
        line = ax2.plot(
            rent_data['year'],
            rent_data['monthly_rent_ratio'],
            color=color,
            marker='o',
            linewidth=3,
            markersize=8,
            label='월세 비중'
        )
        ax2.tick_params(axis='y', labelcolor=color)
        ax2.set_ylim(30, 70)
        
        # 제목 및 범례
        plt.title(
            '[팩트체크] "세금 때문에 월세 올랐다?" → 데이터는 정반대를 말합니다',
            fontsize=14,
            fontweight='bold',
            pad=20
        )
        
        # 주석 추가
        ax1.text(
            2022, max(tax_data['tax_billion_krw'] / 1000) * 1.15,
            '← 세금은 줄었는데',
            fontsize=11,
            color='red',
            ha='center'
        )
        ax2.text(
            2023, 58,
            '월세는 늘었다 →',
            fontsize=11,
            color='blue',
            ha='center'
        )
        
        fig.tight_layout()
        
        # 저장
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)
    
    def create_interest_vs_rent_chart(
        self,
        interest_data: pd.DataFrame,
        rent_data: pd.DataFrame,
        filename: str = "interest_vs_rent.png"
    ) -> str:
        """
        '금리 상승 vs 월세 증가' 상관관계 차트
        
        Args:
            interest_data: 금리 데이터 (columns: date, mortgage_rate)
            rent_data: 월세 비중 데이터 (columns: year, monthly_rent_ratio)
            filename: 저장할 파일명
            
        Returns:
            저장된 파일 경로
        """
        fig, ax1 = plt.subplots(figsize=(12, 6))
        
        # 연도 추출 (YYYY-MM → YYYY)
        interest_data['year'] = pd.to_datetime(interest_data['date']).dt.year
        
        # 왼쪽 Y축: 금리
        color = 'tab:orange'
        ax1.set_xlabel('연도', fontsize=12)
        ax1.set_ylabel('주택담보대출 금리 (%)', color=color, fontsize=12)
        ax1.plot(
            interest_data['year'],
            interest_data['mortgage_rate'],
            color=color,
            marker='s',
            linewidth=3,
            markersize=8,
            label='주담대 금리'
        )
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.set_ylim(2, 6)
        
        # 오른쪽 Y축: 월세 비중
        ax2 = ax1.twinx()
        color = 'tab:blue'
        ax2.set_ylabel('월세 거래 비중 (%)', color=color, fontsize=12)
        ax2.plot(
            rent_data['year'],
            rent_data['monthly_rent_ratio'],
            color=color,
            marker='o',
            linewidth=3,
            markersize=8,
            label='월세 비중'
        )
        ax2.tick_params(axis='y', labelcolor=color)
        ax2.set_ylim(30, 70)
        
        plt.title(
            '[팩트체크] 진짜 범인은 "금리"입니다',
            fontsize=14,
            fontweight='bold',
            pad=20
        )
        
        fig.tight_layout()
        
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)


if __name__ == "__main__":
    # 테스트 실행
    from data_fetcher import KOSISFetcher, BOKFetcher, NTSFetcher
    
    print("=== 차트 생성 테스트 ===\n")
    
    # 데이터 수집
    kosis = KOSISFetcher()
    bok = BOKFetcher()
    nts = NTSFetcher()
    
    rental_data = kosis.fetch_rental_stats()
    interest_data = bok.fetch_interest_rates()
    tax_data = nts.fetch_property_tax_stats()
    
    # 차트 생성
    generator = ChartGenerator()
    
    chart1 = generator.create_tax_vs_rent_chart(tax_data, rental_data)
    print(f"✅ 차트 1 생성 완료: {chart1}")
    
    chart2 = generator.create_interest_vs_rent_chart(interest_data, rental_data)
    print(f"✅ 차트 2 생성 완료: {chart2}")
