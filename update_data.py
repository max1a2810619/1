import requests
import json
from datetime import datetime, timedelta

print("啟動極簡籌碼爬蟲 (防禦模式)...")

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
        
        if data.get("msg") == "success":
            data_list = data.get("data", [])
            
            if len(data_list) > 0:
                print(f"🔍 欄位結構長這樣: {data_list[0]}") # 印出真實欄位來確認
                
                foreign_data = []
                for item in data_list:
                    # 【修復核心】安全地找名稱欄位，不管是 name 還是 investor 通通拿來比對
                    inv_name = str(item.get("name", "")) + str(item.get("investor", ""))
                    if "外資" in inv_name:
                        foreign_data.append(item)
                
                if len(foreign_data) >= 2:
                    # 確保照日期排序
                    foreign_data = sorted(foreign_data, key=lambda x: x.get('date', ''))
                    latest_item = foreign_data[-1]
                    prev_item = foreign_data[-2]
                    
                    # 【修復核心】安全地找未平倉數值欄位 (預防未來 FinMind 又改名)
                    def get_oi(d):
                        for k in ["net_oi_volume", "open_interest_net", "oi_net", "net_oi"]:
                            if k in d: return d[k]
                        return 0
                        
                    latest_oi = get_oi(latest_item)
                    prev_oi = get_oi(prev_item)
                    data_date = latest_item.get("date", "未知")
                    oi_change = latest_oi - prev_oi
                    
                    print(f"✅ 成功計算外資未平倉! 日期:{data_date}, 最新:{latest_oi}, 增減:{oi_change}")
                    return latest_oi, oi_change, data_date
                else:
                    print("❌ 錯誤：找不到足夠的『外資』資料來計算增減")
            else:
                print("❌ 錯誤：API 雖然回傳 success，但資料陣列是空的！")
        else:
            print(f"❌ 錯誤：FinMind 拒絕連線: {data}")
            
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
