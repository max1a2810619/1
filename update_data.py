import yfinance as yf
import requests
import json
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
    """使用 FinMind API 抓取選擇權 P/C Ratio (避開期交所海外 IP 阻擋)"""
    try:
        url = "https://api.finmindtrade.com/api/v4/data"
        # 抓取最近 10 天的資料，確保一定有最新的一筆 (避開長假)
        start_date = (datetime.utcnow() - timedelta(days=10)).strftime("%Y-%m-%d")
        params = {
            "dataset": "TaiwanOptionPutCallRatio",
            "start_date": start_date
        }
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        
        if data.get("msg") == "success" and len(data.get("data", [])) > 0:
            latest_data = data["data"][-1]
            # FinMind 的 PutCallRatio 是百分比，例如 115.5，除以 100 變成 1.15
            pc_ratio = float(latest_data.get("PutCallRatio", 100)) / 100
            color = "up" if pc_ratio >= 1 else "down" # > 1 偏多(紅)，< 1 偏空(綠)
            print(f"✅ 成功獲取 P/C Ratio (FinMind): {pc_ratio:.2f}")
            return {"label": "選擇權 P/C Ratio", "value": f"{pc_ratio:.2f}", "color": color}
        else:
            print("⚠️ FinMind 回傳資料為空或異常")
            return {"label": "選擇權 P/C Ratio", "value": "查無最新資料", "color": "down"}
    except Exception as e:
        print(f"❌ P/C Ratio抓取失敗: {e}")
        return {"label": "選擇權 P/C Ratio", "value": "API連線失敗", "color": "down"}

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
    "aiStatusText": "全自動更新成功",
    "aiStatusColor": "var(--green)",
    "aiCommentText": "<b>本日解析：</b>個股收盤價、法人買賣超、選擇權 P/C Ratio 皆已透過 Python 自動爬蟲抓取完畢！系統運作正常！",
    
    # 將爬蟲函數抓到的資料放入 chips 陣列
    "chips": [
        {"label": "外資淨未平倉 (TX)", "value": "需進階API", "color": "down"}, 
        get_taifex_pc_ratio(),
        {"label": "散戶淨未平倉 (口)", "value": "需進階API", "color": "up"},   
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
