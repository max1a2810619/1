import requests
import re
import json
from datetime import datetime, timedelta

print("啟動極簡籌碼爬蟲 (期交所官方直連模式)...")

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

def get_taifex_oi(date_str):
    """直接爬取期交所官方網頁"""
    url = "https://www.taifex.com.tw/cht/3/futContractsDate"
    payload = {
        "queryType": "1",
        "doQuery": "1",
        "queryDate": date_str,
        "commodityId": "TXF" # 鎖定只查臺股期貨
    }
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        res = requests.post(url, data=payload, headers=headers, timeout=10)
        html = res.text
        
        if "外資及陸資" not in html:
            return None # 可能是假日或尚未結算，沒有資料
            
        # 鎖定網頁中「外資」的那一列表格
        match = re.search(r'外資及陸資(.*?)</tr>', html, re.DOTALL)
        if match:
            row_html = match.group(1)
            # 抓出所有格子裡的文字
            tds = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.DOTALL)
            # 清除 HTML 標籤跟千分位逗號
            texts = [re.sub(r'<[^>]+>', '', td).strip().replace(',', '') for td in tds]
            # 轉成純數字 (保留負號)
            nums = [int(x) for x in texts if x.lstrip('-').isdigit()]
            
            # 期交所的表格固定有 12 個數字，倒數第二個絕對是「未平倉淨口數」
            if len(nums) >= 2:
                return nums[-2]
    except Exception as e:
        print(f"期交所抓取錯誤: {e}")
    return None

def get_foreign_tx_oi():
    print("開始連線期交所官方網站...")
    
    tw_time = datetime.utcnow() + timedelta(hours=8)
    oi_history = []
    dates_found = []
    
    # 自動往前推算 10 天，找出最近的「兩個」有開盤的交易日
    for i in range(10):
        check_date = (tw_time - timedelta(days=i)).strftime("%Y/%m/%d")
        oi = get_taifex_oi(check_date)
        
        if oi is not None:
            print(f"🔍 找到 {check_date} 的資料: {oi} 口")
            oi_history.append(oi)
            dates_found.append(check_date)
            
        if len(oi_history) == 2:
            break
            
    if len(oi_history) == 2:
        latest_oi = oi_history[0]
        oi_change = oi_history[0] - oi_history[1]
        data_date = dates_found[0]
        print(f"✅ 計算成功！最新:{latest_oi}, 增減:{oi_change}")
        return latest_oi, oi_change, data_date
    elif len(oi_history) == 1:
        return oi_history[0], 0, dates_found[0]
    else:
        return "找不到交易日資料", 0, "未知"

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

print(f"🎉 官方直連更新作業結束！")
