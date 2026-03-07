import requests
import json
from datetime import datetime, timedelta

print("啟動極簡籌碼爬蟲 (偵探模式)...")

def get_institutional_net_buy():
    """抓取證交所三大法人買賣超 (換算為億)"""
    try:
        url = "https://www.twse.com.tw/rwd/zh/fund/BFI82U?response=json"
        res = requests.get(url, timeout=10)
        data = res.json()
        total_str = data['data'][-1][3] 
        net_value = float(total_str.replace(',', '')) / 100000000
        print(f"✅ 三大法人買賣超抓取成功: {net_value:.2f} 億")
        return round(net_value, 2)
    except Exception as e:
        print(f"❌ 三大法人抓取失敗: {e}")
        return None

def get_foreign_tx_oi():
    """使用 FinMind API 抓取外資台股期貨 (TX) 淨未平倉與增減"""
    print("開始連線 FinMind 抓取外資未平倉...")
    try:
        url = "https://api.finmindtrade.com/api/v4/data"
        start_date = (datetime.utcnow() - timedelta(days=15)).strftime("%Y-%m-%d")
        params = {"dataset": "TaiwanFuturesInstitutionalInvestors", "data_id": "TX", "start_date": start_date}
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        
        print(f"🔍 FinMind 回傳狀態 (msg): {data.get('msg')}")
        
        if data.get("msg") == "success":
            data_list = data.get("data", [])
            print(f"🔍 總共抓到 {len(data_list)} 筆資料")
            
            if len(data_list) > 0:
                # 把 API 裡面出現的所有法人名稱印出來檢查
                names = set([item["name"] for item in data_list])
                print(f"🔍 資料中包含的法人名稱有: {names}")
                
                # 篩選外資資料
                foreign_data = [item for item in data_list if item["name"] == "外資及陸資"]
                
                if len(foreign_data) >= 2:
                    foreign_data = sorted(foreign_data, key=lambda x: x['date'])
                    latest_oi = foreign_data[-1]["net_oi_volume"]
                    prev_oi = foreign_data[-2]["net_oi_volume"]
                    data_date = foreign_data[-1]["date"]
                    oi_change = latest_oi - prev_oi
                    
                    print(f"✅ 成功計算外資未平倉! 日期:{data_date}, 最新:{latest_oi}, 增減:{oi_change}")
                    return latest_oi, oi_change, data_date
                else:
                    print("❌ 錯誤：外資資料筆數不足 2 筆，無法計算昨天與今天的增減。")
            else:
                print("❌ 錯誤：API 雖然回傳 success，但資料陣列是空的！")
        else:
            print(f"❌ 錯誤：FinMind 拒絕連線，詳細訊息: {data}")
            
    except Exception as e:
        print(f"❌ 程式執行發生致命錯誤: {e}")
        
    return None, None, None

# --- 執行抓取 ---
net_buy = get_institutional_net_buy()
latest_oi, oi_change, data_date = get_foreign_tx_oi()

# --- 格式化數據 ---
def format_num(num, is_amount=False):
    if num is None: return {"value": "錯誤", "color": "gray"}
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

print(f"🎉 更新作業結束！")
