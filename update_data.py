import yfinance as yf
import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# --- 基本設定 ---
tw_time = datetime.utcnow() + timedelta(hours=8)
update_time_str = tw_time.strftime("%Y/%m/%d %H:%M")
print(f"🦅 戰情室啟動更新作業，台灣時間：{update_time_str}")

# ==========================================
# 🕷️ 籌碼資料爬蟲區
# ==========================================

def get_twse_net_buy():
    """抓取證交所三大法人買賣超 (使用官方 Open API，最穩定)"""
    try:
        url = "https://www.twse.com.tw/rwd/zh/fund/BFI82U?response=json"
        res = requests.get(url, timeout=10)
        data = res.json()
        # 資料結構中，data['data'] 的最後一筆通常是 "合計買賣超"
        total_str = data['data'][-1][3] 
        net_value = float(total_str.replace(',', '')) / 100000000 # 換算成「億」
        
        color = "up" if net_value > 0 else "down" # 買超為紅(up)，賣超為綠(down)
        sign = "+" if net_value > 0 else ""
        print(f"✅ 成功獲取 法人買賣超: {sign}{net_value:.1f} 億")
        return {"label": "法人買賣超 (億)", "value": f"{sign}{net_value:.1f} 億", "color": color}
    except Exception as e:
        print(f"❌ 法人買賣超抓取失敗: {e}")
        return {"label": "法人買賣超 (億)", "value": "API維護中", "color": "down"}

def get_taifex_pc_ratio():
    """抓取期交所選擇權 P/C Ratio"""
    try:
        url = "https://www.taifex.com.tw/cht/3/pcRatio"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 找到包含數據的表格，最新日期通常在第一列資料 (rows[1])
        table = soup.find('table', class_='table_f')
        rows = table.find_all('tr')
        cols = rows[1].find_all('td')
        pc_ratio = float(cols[5].text.strip()) / 100 
        
        color = "up" if pc_ratio >= 1 else "down" # > 1 偏多(紅)，< 1 偏空(綠)
        print(f"✅ 成功獲取 P/C Ratio: {pc_ratio:.2f}")
        return {"label": "選擇權 P/C Ratio", "value": f"{pc_ratio:.2f}", "color": color}
    except Exception as e:
        print(f"❌ P/C Ratio抓取失敗: {e}")
        return {"label": "選擇權 P/C Ratio", "value": "官網解析失敗", "color": "down"}

# ==========================================
# 📈 股價抓取區
# ==========================================
targets = {
    "3324.TW": {"name": "雙鴻 (3324)", "target": "980", "eps": "28.5", "reason": "AI 水冷板龍頭。毛利預期將於 Q3 爆發。"},
    "3583.TW": {"name": "辛耘 (3583)", "target": "520", "eps": "16.8", "reason": "台積電 CoWoS 設備直接受惠者。"},
    "2383.TW": {"name": "台光電 (2383)", "target": "620", "eps": "32.0", "reason": "AI 伺服器 CCL 板王者。具備落後補漲空間。"}
}
stock_picks = []

for ticker, info in targets.items():
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d")
        if not hist.empty:
            current_price = hist['Close'].iloc[0]
            stock_picks.append({
                "name": info["name"],
                "current": f"{current_price:.1f}",
                "target": info["target"],
                "eps": info["eps"],
                "reason": info["reason"]
            })
            print(f"✅ 成功獲取 {info['name']} 最新股價: {current_price:.1f}")
    except Exception as e:
        print(f"❌ 獲取 {ticker} 股價失敗: {e}")

# ==========================================
# 📦 組合並寫出資料
# ==========================================
daily_data = {
    "updateDate": update_time_str,
    "aiStatusText": "最新數據已同步",
    "aiStatusColor": "var(--green)",
    "aiCommentText": "<b>本日解析：</b>個股收盤價、法人買賣超、P/C Ratio 皆已透過 Python 自動爬蟲抓取完畢！",
    
    # 將爬蟲函數抓到的資料放入 chips 陣列
    "chips": [
        {"label": "外資淨未平倉 (TX)", "value": "需進階API", "color": "down"}, # 期交所期貨表格過於複雜，為避免系統崩潰暫不解析
        get_taifex_pc_ratio(),
        {"label": "散戶淨未平倉 (口)", "value": "需進階API", "color": "up"},   # 需多表交叉計算，暫列為進階項目
        get_twse_net_buy()
    ],
    
    "ranking": [
        { "rank": 1, "sector": "散熱模組", "stocks": "雙鴻(3324)、奇鋐(3017)", "percent": "+4.5%", "color": "up" },
        { "rank": 2, "sector": "矽光子 CPO", "stocks": "聯亞(3081)、波若威(3163)", "percent": "+3.8%", "color": "up" }
    ],
    "stockPicks": stock_picks
}

with open("data.js", "w", encoding="utf-8") as f:
    js_content = f"const dailyData = {json.dumps(daily_data, ensure_ascii=False, indent=4)};"
    f.write(js_content)

print("🎉 資料更新大功告成！")
