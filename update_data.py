import requests
import json
import csv
from io import StringIO
from datetime import datetime, timedelta

print("啟動極簡籌碼爬蟲 (期交所 CSV 無敵直連模式)...")

def get_institutional_net_buy():
    """抓取證交所三大法人買賣超 (換算為億)"""
    try:
        url = "https://www.twse.com.tw/rwd/zh/fund/BFI82U?response=json"
        res = requests.get(url, timeout=10)
        data = res.json()
        total_str = data['data'][-1][3] 
        net_value = float(total_str.replace(',', '')) / 100000000
        return round(net_value, 2)
    except Exception as e:
        return f"法人API錯誤"

def get_foreign_tx_oi():
    """直接從期交所下載 CSV 報表，最穩定、不被擋"""
    try:
        tw_time = datetime.utcnow() + timedelta(hours=8)
        # 一次抓過去 15 天的報表，確保一定能拿到最近兩個交易日
        start_date = (tw_time - timedelta(days=15)).strftime("%Y/%m/%d")
        end_date = tw_time.strftime("%Y/%m/%d")

        url = "https://www.taifex.com.tw/cht/3/futContractsDateDown"
        payload = {
            "queryStartDate": start_date,
            "queryEndDate": end_date,
            "commodityId": "TXF" # TXF = 台股期貨 (大台)
        }
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.post(url, data=payload, headers=headers, timeout=10)
        
        # 期交所的 CSV 檔案是 Big5 編碼
        text = res.content.decode('big5', errors='ignore')
        
        # 使用 Python 內建的專業 CSV 解析器
        reader = csv.reader(StringIO(text))
        
        foreign_data = []
        for row in reader:
            # row[1]是商品, row[2]是身份, row[13]是多空淨額未平倉口數
            if len(row) >= 14 and "TXF" in row[1] and "外資" in row[2]:
                try:
                    date_str = row[0].strip()
                    # 去除數字裡的千分位逗號並轉成整數
                    oi = int(row[13].replace(',', '')) 
                    foreign_data.append((date_str, oi))
                except:
                    pass
                    
        if len(foreign_data) >= 2:
            # 確保按日期從小到大排序 (舊 -> 新)
            foreign_data = sorted(foreign_data, key=lambda x: x[0])
            latest_date, latest_oi = foreign_data[-1]
            prev_date, prev_oi = foreign_data[-2]
            
            # 計算今天與昨天的差額
            oi_change = latest_oi - prev_oi
            return latest_oi, oi_change, latest_date
        else:
            return f"CSV資料不足", 0, "未知"
            
    except Exception as e:
        return f"CSV解析錯誤", 0, "未知"

# --- 執行抓取 ---
net_buy = get_institutional_net_buy()
latest_oi, oi_change, data_date = get_foreign_tx_oi()

# --- 格式化數據 ---
def format_num(num, is_amount=False):
    if isinstance(num, str): return {"value": num, "color": "gray"} 
    if num is None: return {"value": "--", "color": "gray"}
    
    sign = "+" if num > 0 else ""
    color = "red" if num > 0 else "green" 
    unit = " 億" if is_amount else ""
    formatted_value = f"{sign}{num:,.2f}{unit}" if is_amount else f"{sign}{int(num):,}"
    return {"value": formatted_value, "color": color}

tw_time = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y/%m/%d %H:%M")

output_data = {
    "update_time": tw_time,
    "data_date": data_date if data_date else "未知日期",
    "net_buy": format_num(net_buy, is_amount=True),
    "oi_total": format_num(latest_oi),
    "oi_change": format_num(oi_change)
}

with open("data.js", "w", encoding="utf-8") as f:
    js_content = f"const marketData = {json.dumps(output_data, ensure_ascii=False, indent=4)};"
    f.write(js_content)
