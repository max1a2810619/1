import yfinance as yf
import json
from datetime import datetime, timedelta

# 計算台灣時間 (UTC+8)
tw_time = datetime.utcnow() + timedelta(hours=8)
update_time_str = tw_time.strftime("%Y/%m/%d %H:%M")

print(f"啟動更新作業，台灣時間：{update_time_str}")

targets = {
    "3324.TW": {"name": "雙鴻 (3324)", "target": "980", "eps": "28.5", "reason": "AI 水冷板龍頭。目前股價回測月線有守，隨液冷滲透率翻倍，毛利預期將於 Q3 爆發。"},
    "3583.TW": {"name": "辛耘 (3583)", "target": "520", "eps": "16.8", "reason": "台積電 CoWoS 設備直接受惠者。相較漲幅已大的同業，具備更強的籌碼穩定度。"},
    "2383.TW": {"name": "台光電 (2383)", "target": "620", "eps": "32.0", "reason": "AI 伺服器 CCL 板王者。目前本益比回落至歷史低檔，尚未隨指數大漲，具補漲空間。"}
}

stock_picks = []

for ticker, info in targets.items():
    try:
        stock = yf.Ticker(ticker)
        # 抓取最新收盤價
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
        else:
            print(f"⚠️ 無法獲取 {ticker} 的股價資料")
    except Exception as e:
        print(f"❌ 獲取 {ticker} 失敗: {e}")

daily_data = {
    "updateDate": update_time_str,
    "aiStatusText": "最新報價已更新",
    "aiStatusColor": "var(--green)",
    "aiCommentText": "<b>本日解析：</b>個股收盤價已由 Python 爬蟲自動從 Yahoo Finance 抓取更新完畢！籌碼數據目前為靜態展示。",
    "chips": [
        { "label": "外資淨未平倉 (TX)", "value": "- 41,134", "color": "down" },
        { "label": "選擇權 P/C Ratio", "value": "0.88", "color": "down" },
        { "label": "散戶淨未平倉 (口)", "value": "+ 13,282", "color": "up" },
        { "label": "法人買賣超 (億)", "value": "- 458 億", "color": "down" }
    ],
    "ranking": [
        { "rank": 1, "sector": "散熱模組", "stocks": "雙鴻(3324)、奇鋐(3017)", "percent": "+4.5%", "color": "up" },
        { "rank": 2, "sector": "矽光子 CPO", "stocks": "聯亞(3081)、波若威(3163)", "percent": "+3.8%", "color": "up" },
        { "rank": 3, "sector": "半導體設備", "stocks": "弘塑(3131)、辛耘(3583)", "percent": "+2.9%", "color": "up" }
    ],
    "stockPicks": stock_picks
}

# 寫出 data.js
with open("data.js", "w", encoding="utf-8") as f:
    js_content = f"const dailyData = {json.dumps(daily_data, ensure_ascii=False, indent=4)};"
    f.write(js_content)

print("🎉 資料更新完成！")
