import requests
import json
from datetime import datetime, timedelta

print("啟動極簡籌碼爬蟲 (無敵暴力模式)...")

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
                # 找出資料中最新的兩天日期
                dates = sorted(list(set([d.get("date") for d in data_list])))
                if len(dates) >= 2:
                    latest_date = dates[-1]
                    prev_date = dates[-2]
                    
                    # 【暴力破解核心】將每一列資料轉成字串，只要字串裡包含「外資」，就認定是目標！
                    latest_item = next((item for item in data_list if item.get("date") == latest_date and "外資" in str(item)), None)
                    prev_item = next((item for item in data_list if item.get("date") == prev_date and "外資" in str(item)), None)
                    
                    if latest_item and prev_item:
                        # 暴力尋找未平倉數字 (找欄位名稱裡有 net 跟 oi 的)
                        def find_oi(d):
                            for k, v in d.items():
                                if isinstance(v, (int, float)) and 'net' in k.lower() and 'oi' in k.lower():
                                    return v
                            # 備案：硬抓最常見的名字
                            return d.get('long_short_net_oi_volume', d.get('net_oi_volume', 0))

                        latest_oi = find_oi(latest_item)
                        prev_oi = find_oi(prev_item)
                        oi_change = latest_oi - prev_oi
                        return latest_oi, oi_change, latest_date
                    else:
                        # 如果找不到，故意把抓到的所有名稱秀給我們看
                        names = list(set([str(item.get("name", item.get("investor", "未知"))) for item in data_list]))
                        return f"找不到外資，目前有:{names[:3]}", 0, latest_date
                else:
                    return "資料天數不足2天", 0, dates[-1] if dates else "未知"
            else:
                return "API無回傳資料", 0, "未知"
        else:
            return f"API拒絕:{data.get('msg')}", 0, "未知"
            
    except Exception as e:
        # 如果程式死當，把錯誤訊息截斷直接顯示
        return f"例外:{str(e)[:15]}", 0, "未知"

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
