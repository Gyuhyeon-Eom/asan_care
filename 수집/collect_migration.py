"""
행정안전부 지역별 인구이동 현황 API 수집
- 아산시(4420000000) 전입/전출 데이터
- 기간: 2022.10 ~ 현재
"""
import requests
import pandas as pd
import time
from datetime import datetime
from pathlib import Path

# API 설정
BASE_URL = "http://apis.data.go.kr/1741000/ppltnDataStus/selectPpltnDataStus"
SERVICE_KEY = "rIZ7FB29NjENK43w6dtqGHHqgMW1296UI442F4yT09cWOKYLx6D/mZVHI5+7UeDW3Id2iTwQWwVhrnSyhHrnYA=="
ASAN_CODE = "4420000000"

# 출력 경로
OUTPUT_DIR = Path(__file__).parent.parent.parent / "01_데이터" / "원천데이터"


def get_period_ranges(start_ym: str, end_ym: str) -> list:
    """3개월 단위로 기간 분할 (API 제한)"""
    from dateutil.relativedelta import relativedelta
    
    periods = []
    start = datetime.strptime(start_ym, "%Y%m")
    end = datetime.strptime(end_ym, "%Y%m")
    
    current = start
    while current <= end:
        period_end = current + relativedelta(months=2)
        if period_end > end:
            period_end = end
        periods.append((current.strftime("%Y%m"), period_end.strftime("%Y%m")))
        current = period_end + relativedelta(months=1)
    
    return periods


def fetch_migration_data(mvin_cd: str, mvt_cd: str, fr_ym: str, to_ym: str, lv: str = "2") -> list:
    """인구이동 데이터 조회"""
    all_items = []
    page = 1
    
    while True:
        params = {
            "serviceKey": SERVICE_KEY,
            "mvinAdmmCd": mvin_cd,
            "mvtAdmmCd": mvt_cd,
            "srchFrYm": fr_ym,
            "srchToYm": to_ym,
            "lv": lv,
            "type": "json",
            "numOfRows": "100",
            "pageNo": str(page)
        }
        
        try:
            resp = requests.get(BASE_URL, params=params, timeout=30)
            data = resp.json()
            
            head = data.get("Response", {}).get("head", {})
            if head.get("resultCode") != "0":
                print(f"  API Error: {head.get('resultMsg')}")
                break
            
            items = data.get("Response", {}).get("items", {})
            if not items:
                break
                
            item_list = items.get("item", [])
            if isinstance(item_list, dict):
                item_list = [item_list]
            
            if not item_list:
                break
                
            all_items.extend(item_list)
            
            total = int(head.get("totalCount", 0))
            if len(all_items) >= total:
                break
                
            page += 1
            time.sleep(0.3)
            
        except Exception as e:
            print(f"  Error: {e}")
            break
    
    return all_items


def collect_asan_migration():
    """아산시 전입/전출 데이터 수집"""
    # 기간 설정 (2022.10 ~ 2026.02)
    periods = get_period_ranges("202210", "202602")
    
    all_inflow = []  # 전입 (타지역 → 아산)
    all_outflow = []  # 전출 (아산 → 타지역)
    
    print("=== 아산시 인구이동 데이터 수집 시작 ===")
    print(f"수집 기간: 2022.10 ~ 2026.02 ({len(periods)}개 구간)")
    
    for fr_ym, to_ym in periods:
        print(f"\n[{fr_ym} ~ {to_ym}]")
        
        # 전입 데이터 (전국 → 아산)
        print(f"  전입 데이터 수집중...")
        inflow = fetch_migration_data(
            mvin_cd=ASAN_CODE,  # 전입지: 아산
            mvt_cd="0000000000",  # 전출지: 전국 (빈값 또는 전체)
            fr_ym=fr_ym,
            to_ym=to_ym
        )
        # 전국 코드가 안되면 시도별로
        if not inflow:
            print(f"    전국 코드 실패, 개별 시도 수집...")
            sido_codes = ["11", "26", "27", "28", "29", "30", "31", "36", 
                         "41", "42", "43", "44", "45", "46", "47", "48", "50"]
            for sido in sido_codes:
                sido_data = fetch_migration_data(
                    mvin_cd=ASAN_CODE,
                    mvt_cd=f"{sido}00000000",
                    fr_ym=fr_ym,
                    to_ym=to_ym,
                    lv="1"
                )
                inflow.extend(sido_data)
                time.sleep(0.2)
        
        all_inflow.extend(inflow)
        print(f"    전입: {len(inflow)}건")
        
        # 전출 데이터 (아산 → 전국)
        print(f"  전출 데이터 수집중...")
        outflow = fetch_migration_data(
            mvin_cd="0000000000",
            mvt_cd=ASAN_CODE,  # 전출지: 아산
            fr_ym=fr_ym,
            to_ym=to_ym
        )
        if not outflow:
            print(f"    전국 코드 실패, 개별 시도 수집...")
            for sido in sido_codes:
                sido_data = fetch_migration_data(
                    mvin_cd=f"{sido}00000000",
                    mvt_cd=ASAN_CODE,
                    fr_ym=fr_ym,
                    to_ym=to_ym,
                    lv="1"
                )
                outflow.extend(sido_data)
                time.sleep(0.2)
        
        all_outflow.extend(outflow)
        print(f"    전출: {len(outflow)}건")
        
        time.sleep(0.5)
    
    # DataFrame 변환 및 저장
    print("\n=== 데이터 저장 ===")
    
    if all_inflow:
        df_inflow = pd.DataFrame(all_inflow)
        df_inflow["flow_type"] = "inflow"
        inflow_path = OUTPUT_DIR / "asan_migration_inflow.parquet"
        df_inflow.to_parquet(inflow_path, index=False)
        print(f"전입 데이터: {len(df_inflow)}건 → {inflow_path}")
    
    if all_outflow:
        df_outflow = pd.DataFrame(all_outflow)
        df_outflow["flow_type"] = "outflow"
        outflow_path = OUTPUT_DIR / "asan_migration_outflow.parquet"
        df_outflow.to_parquet(outflow_path, index=False)
        print(f"전출 데이터: {len(df_outflow)}건 → {outflow_path}")
    
    # 통합 파일
    if all_inflow or all_outflow:
        df_all = pd.concat([
            pd.DataFrame(all_inflow).assign(flow_type="inflow") if all_inflow else pd.DataFrame(),
            pd.DataFrame(all_outflow).assign(flow_type="outflow") if all_outflow else pd.DataFrame()
        ], ignore_index=True)
        all_path = OUTPUT_DIR / "asan_migration_all.parquet"
        df_all.to_parquet(all_path, index=False)
        print(f"통합 데이터: {len(df_all)}건 → {all_path}")
    
    print("\n=== 수집 완료 ===")


if __name__ == "__main__":
    collect_asan_migration()
