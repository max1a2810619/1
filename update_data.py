import requests
import json
from datetime import datetime, timedelta

print("啟動極簡籌碼爬蟲...")

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
        print(f"三大法人抓取失敗: {e}")
        return None

def get_foreign_tx_oi():
    """使用 FinMind API 抓取外資台股期貨 (TX) 淨未平倉與增減"""
    try:
        url = "https://api.finmindtrade.com/api/v4/data"
        # 抓取過去 15 天資料，確保能取到最近「兩個」交易日來算差額
        start_date = (datetime.utcnow() - timedelta(days=15)).strftime("%Y-%m-%d")
        params = {"dataset": "TaiwanFuturesInstitutionalInvestors", "data_id": "TX", "start_date": start_date}
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        
        if data.get("msg") == "success" and len(data.get("data", [])) > 0:
            # 只篩選外資資料
            foreign_data = [item for item in data["data"] if item["name"] == "外資及陸資"]
            
            if len(foreign_data) >= 2:
                # 確保照日期排序
                foreign_data = sorted(foreign_data, key=lambda x: x['date'])
                
                # 取出最新一天 (今天) 和 前一天 (昨天) 的未平倉量
                latest_oi = foreign_data[-1]["net_oi_volume"]
                prev_oi = foreign_data[-2]["net_oi_volume"]
                data_date = foreign_data[-1]["date"] # 資料日期
                
                # 計算增減口數
                oi_change = latest_oi - prev_oi
                
                return latest_oi, oi_change, data_date
    except Exception as e:
        print(f"外資未平倉抓取失敗: {e}")
    return None, None, None

# --- 執行抓取 ---
net_buy = get_institutional_net_buy()
latest_oi, oi_change, data_date = get_foreign_tx_oi()

# --- 格式化數據 ---
# 加上正負號與顏色標籤
def format_num(num, is_amount=False):
    if num is None: return {"value": "錯誤", "color": "gray"}
    sign = "+" if num > 0 else ""
    color = "red" if num > 0 else "green" # 台股紅漲綠跌
    unit = " 億" if is_amount else ""
    # 格式化加上千分位逗號
    formatted_value = f"{sign}{num:,.2f}{unit}" if is_amount else f"{sign}{int(num):,}"
    return {"value": formatted_value, "color": color}

# 台灣現在時間
tw_time = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y/%m/%d %H:%M")

output_data = {
    "update_time": tw_time,
    "data_date": data_date if data_date else "未知日期",
    "net_buy": format_num(net_buy, is_amount=True),
    "oi_total": format_num(latest_oi),
    "oi_change": format_num(oi_change)
}

# --- 寫出 JavaScript 檔案 ---
with open("data.js", "w", encoding="utf-8") as f:
    js_content = f"const marketData = {json.dumps(output_data, ensure_ascii=False, indent=4)};"
    f.write(js_content)

print(f"✅ 更新完成！寫入資料: {output_data}")
