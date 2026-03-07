import requests
import json
from datetime import datetime, timedelta

print("啟動極簡籌碼爬蟲 (精準定位模式)...")

def get_institutional_net_buy():
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
    try:
        url = "https://api.finmindtrade.com/api/v4/data"
        start_date = (datetime.utcnow() - timedelta(days=15)).strftime("%Y-%m-%d")
        params = {"dataset": "TaiwanFuturesInstitutionalInvestors", "data_id": "TX", "start_date": start_date}
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        
        if data.get("msg") == "success":
            data_list = data.get("data", [])
            if len(data_list) > 0:
                # 只挑出包含「外資」的資料
                foreign_data = [d for d in data_list if "外資" in str(d.get("name", "")) + str(d.get("investor", ""))]
                
                if len(foreign_data) >= 2:
                    # 確保照日期排序
                    foreign_data = sorted(foreign_data, key=lambda x: x.get('date', ''))
                    latest_item = foreign_data[-1]
                    prev_item = foreign_data[-2]
                    
                    # 【關鍵修復】只抓取 volume (口數)，絕對不能抓到 amount (金額)
                    def get_oi_volume(d):
                        return d.get('long_short_net_oi_volume', d.get('net_oi_volume', 0))

                    latest_oi = get_oi_volume(latest_item)
                    prev_oi = get_oi_volume(prev_item)
                    oi_change = latest_oi - prev_oi
                    latest_date = latest_item.get("date", "未知日期")
                    
                    return latest_oi, oi_change, latest_date
                else:
                    return "外資資料天數不足", 0, "未知"
            else:
                return "API無回傳資料", 0, "未知"
        else:
            return f"API拒絕:{data.get('msg')}", 0, "未知"
            
    except Exception as e:
        return f"程式錯誤", 0, "未知"

net_buy = get_institutional_net_buy()
latest_oi, oi_change, data_date = get_foreign_tx_oi()

def format_num(num, is_amount=False):
    # 如果傳進來的是文字(錯誤訊息)，直接讓網頁顯示文字
    if isinstance(num, str): 
        return {"value": num, "color": "gray"} 
    if num is None: 
        return {"value": "--", "color": "gray"}
    
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
