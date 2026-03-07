import requests
import json
from datetime import datetime, timedelta

print("啟動極簡籌碼爬蟲 (X光透視模式)...")

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
                # 尋找任何包含「外」或「foreign」的資料 (忽略大小寫)
                foreign_data = []
                for d in data_list:
                    dict_str = str(d).lower()
                    if "外" in dict_str or "foreign" in dict_str:
                        foreign_data.append(d)
                
                if len(foreign_data) >= 2:
                    foreign_data = sorted(foreign_data, key=lambda x: x.get('date', ''))
                    latest_item = foreign_data[-1]
                    prev_item = foreign_data[-2]
                    
                    # 找出 key 中包含 volume (口數) 且有 net (淨額) 或 oi (未平倉) 的欄位
                    def get_oi_volume(d):
                        for k, v in d.items():
                            if isinstance(v, (int, float)) and 'volume' in k.lower() and ('net' in k.lower() or 'oi' in k.lower()):
                                return v
                        return d.get('long_short_net_oi_volume', d.get('net_oi_volume', 0))

                    latest_oi = get_oi_volume(latest_item)
                    prev_oi = get_oi_volume(prev_item)
                    oi_change = latest_oi - prev_oi
                    latest_date = latest_item.get("date", "未知")
                    
                    return latest_oi, oi_change, latest_date
                else:
                    # 終極透視：直接把最後一筆資料的「所有欄位名稱」印在網頁上！
                    debug_keys = list(data_list[-1].keys())
                    debug_vals = list(data_list[-1].values())
                    return f"找不到! 欄位有:{debug_keys[:3]}", f"值有:{str(debug_vals[:3])[:10]}", "未知"
            else:
                return "API無回傳資料", 0, "未知"
        else:
            return f"API拒絕:{data.get('msg')}", 0, "未知"
            
    except Exception as e:
        return f"程式錯誤:{str(e)[:15]}", 0, "未知"

net_buy = get_institutional_net_buy()
latest_oi, oi_change, data_date = get_foreign_tx_oi()

def format_num(num, is_amount=False):
    # 如果傳進來的是文字(例如 X光的除錯訊息)，直接顯示文字
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
