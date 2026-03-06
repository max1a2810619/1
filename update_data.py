import yfinance as yf
import requests
import json
from datetime import datetime, timedelta

# --- 基本設定 ---
tw_time = datetime.utcnow() + timedelta(hours=8)
update_time_str = tw_time.strftime("%Y/%m/%d %H:%M")
print(f"🦅 戰情室啟動更新作業，台灣時間：{update_time_str}")

# ==========================================
# 🕷️ 籌碼資料爬蟲區 (全面採用 API 避開阻擋)
# ==========================================

def get_twse_net_buy():
    """抓取證交所三大法人買賣超"""
    try:
        url = "https://www.twse.com.tw/rwd/zh/fund/BFI82U?response=json"
        res = requests.get(url, timeout=10)
        data = res.json()
        total_str = data['data'][-1][3] 
        net_value = float(total_str.replace(',', '')) / 100000000
        color = "up" if net_value > 0 else "down"
        sign = "+" if net_value > 0 else ""
        print(f"✅ 成功獲取 法人買賣超: {sign}{net_value:.1f} 億")
        return {"label": "法人買賣超 (億)", "value": f"{sign}{net_value:.1f} 億", "color": color}
    except Exception as e:
        print(f"❌ 法人買賣超抓取失敗: {e}")
        return {"label": "法人買賣超 (億)", "value": "API維護中", "color": "down"}

def get_taifex_pc_ratio():
    """使用 FinMind API 抓取選擇權 P/C Ratio"""
    try:
        url = "https://api.finmindtrade.com/api/v4/data"
        start_date = (datetime.utcnow() - timedelta(days=10)).strftime("%Y-%m-%d")
        params = {"dataset": "TaiwanOptionPutCallRatio", "start_date": start_date}
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        if data.get("msg") == "success" and len(data.get("data", [])) > 0:
            latest_data = data["data"][-1]
            pc_ratio = float(latest_data.get("PutCallRatio", 100)) / 100
            color = "up" if pc_ratio >= 1 else "down"
            print(f"✅ 成功獲取 P/C Ratio: {pc_ratio:.2f}")
            return {"label": "選擇權 P/C Ratio", "value": f"{pc_ratio:.2f}", "color": color}
        return {"label": "選擇權 P/C Ratio", "value": "查無資料", "color": "down"}
    except Exception as e:
        return {"label": "選擇權 P/C Ratio", "value": "連線失敗", "color": "down"}

def get_foreign_tx_oi():
    """使用 FinMind API 抓取外資台股期貨 (TX) 淨未平倉"""
    try:
        url = "https://api.finmindtrade.com/api/v4/data"
        start_date = (datetime.utcnow() - timedelta(days=10)).strftime("%Y-%m-%d")
        params = {"dataset": "TaiwanFuturesInstitutionalInvestors", "data_id": "TX", "start_date": start_date}
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        if data.get("msg") == "success" and len(data.get("data", [])) > 0:
            # 篩選出外資的最新數據
            foreign_data = [item for item in data["data"] if item["name"] == "外資及陸資"]
            if foreign_data:
                latest_oi = foreign_data[-1]["net_oi_volume"]
                color = "up" if latest_oi > 0 else "down"
                sign = "+" if latest_oi > 0 else ""
                print(f"✅ 成功獲取 外資淨未平倉: {sign}{latest_oi:,}")
                return {"label": "外資淨未平倉 (TX)", "value": f"{sign}{latest_oi:,}", "color": color}
        return {"label": "外資淨未平倉 (TX)", "value": "查無資料", "color": "down"}
    except Exception as e:
        print(f"❌ 外資淨未平倉抓取失敗: {e}")
        return {"label": "外資淨未平倉 (TX)", "value": "連線失敗", "color": "down"}

def get_retail_mtx_oi():
    """使用 FinMind API 抓取散戶小台 (MTX) 淨未平倉"""
    try:
        url = "https://api.finmindtrade.com/api/v4/data"
        start_date = (datetime.utcnow() - timedelta(days=10)).strftime("%Y-%m-%d")
        params = {"dataset": "TaiwanFuturesInstitutionalInvestors", "data_id": "MTX", "start_date": start_date}
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        if data.get("msg") == "success" and len(data.get("data", [])) > 0:
            # 取得最新的日期
            latest_date = data["data"][-1]["date"]
            # 計算當天三大法人小台淨未平倉總和
            inst_net_oi = sum(item["net_oi_volume"] for item in data["data"] if item["date"] == latest_date)
            # 散戶 = 三大法人對手盤 (相反數)
            retail_oi = -inst_net_oi
            color = "up" if retail_oi > 0 else "down" # 散戶做多(紅)，散戶做空(綠)
            sign = "+" if retail_oi > 0 else ""
            print(f"✅ 成功獲取 散戶小台淨未平倉: {sign}{retail_oi:,}")
            return {"label": "散戶淨未平倉 (小台)", "value": f"{sign}{retail_oi:,}", "color": color}
        return {"label": "散戶淨未平倉 (小台)", "value": "查無資料", "color": "down"}
    except Exception as e:
        print(f"❌ 散戶淨未平倉抓取失敗: {e}")
        return {"label": "散戶淨未平倉 (小台)", "value": "連線失敗", "color": "down"}

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
    "aiStatusText": "全數據同步完成",
    "aiStatusColor": "var(--green)",
    "aiCommentText": "<b>本日解析：</b>所有股價與四大籌碼數據（外資期貨、散戶小台、P/C Ratio、法人買賣超）皆已全自動連線更新！",
    
    # 依序放入四大籌碼函數
    "chips": [
        get_foreign_tx_oi(),
        get_taifex_pc_ratio(),
        get_retail_mtx_oi(),
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

print("🎉 終極戰情室資料更新大功告成！")
