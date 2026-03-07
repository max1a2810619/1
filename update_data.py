import requests
import json
from datetime import datetime, timedelta

print("啟動極簡籌碼爬蟲 (VIP 金鑰直連模式)...")

# ==========================================
# 🔑 你的 FinMind 專屬 VIP 通行證已安裝完畢！
# ==========================================
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMy0wNyAxNzo0MzozNCIsInVzZXJfaWQiOiJtYXgxYTIiLCJpcCI6IjI3LjUzLjEyMi4yMjUiLCJleHAiOjE3NzM0ODE0MTR9.H65hXmFH8m4jx2_yxP6roSZisZIuaPX0uOl3bWCdE_Q"

def get_institutional_net_buy():
    """抓取證交所三大法人買賣超 (證交所不會擋國外IP，免金鑰)"""
    try:
        url = "https://www.twse.com.tw/rwd/zh/fund/BFI82U?response=json"
        res = requests.get(url, timeout=10)
        data = res.json()
        total_str = data['data'][-1][3] 
        net_value = float(total_str.replace(',', '')) / 100000000
        print(f"✅ 三大法人買賣超: {net_value:.2f} 億")
        return round(net_value, 2)
    except Exception as e:
        return "法人連線異常"

def get_foreign_tx_oi():
    """使用 VIP 金鑰抓取外資未平倉 (保證不被擋)"""
    if not FINMIND_TOKEN or "把你的金鑰貼在這裡" in FINMIND_TOKEN:
        return "請先填寫Token金鑰", 0, "未知"
        
    print("使用 VIP 通行證連線 FinMind...")
    try:
        url = "https://api.finmindtrade.com/api/v4/data"
        start_date = (datetime.utcnow() - timedelta(days=15)).strftime("%Y-%m-%d")
        params = {
            "dataset": "TaiwanFuturesInstitutionalInvestors",
            "data_id": "TX",
            "start_date": start_date,
            "token": FINMIND_TOKEN # 👈 這裡就是突破封鎖的關鍵！
        }
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        
        if data.get("msg") == "success":
            # 篩選外資
            foreign_data = [item for item in data.get("data", []) if "外資" in str(item.get("name", "")) + str(item.get("investor", ""))]
            
            if len(foreign_data) >= 2:
                foreign_data = sorted(foreign_data, key=lambda x: x.get('date', ''))
                latest = foreign_data[-1]
                prev = foreign_data[-2]
                
                # 安全抓取口數
                latest_oi = latest.get('long_short_net_oi_volume', latest.get('net_oi_volume', 0))
                prev_oi = prev.get('long_short_net_oi_volume', prev.get('net_oi_volume', 0))
                data_date = latest.get('date', '未知日期')
                
                print(f"✅ 成功獲取！最新外資未平倉: {latest_oi}")
                return latest_oi, latest_oi - prev_oi, data_date
            else:
                return "資料筆數不足", 0, "未知"
        else:
            return f"金鑰無效或被拒", 0, "未知"
            
    except Exception as e:
        return "API連線異常", 0, "未知"

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

print(f"🎉 VIP 更新作業結束！")
