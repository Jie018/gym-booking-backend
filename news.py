import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import hashlib
import time
from datetime import datetime
from pathlib import Path
import re

class PUSportsMonitor:
    """靜宜大學體育室新聞監控系統（HTML 解析版）"""
    def __init__(self):
        self.base_url = "https://b023.pu.edu.tw"
        self.main_url = "https://b023.pu.edu.tw/p/403-1049-882.php?Lang=zh-tw"
        self.headers = {"User-Agent": "Mozilla/5.0"}
        self.data_dir = Path("pu_sports_data")
        self.data_dir.mkdir(exist_ok=True)
        self.history_file = self.data_dir / "news_history.json"
        self.last_hash = None
        self.news_cache = []

    def fetch_html(self, url):
        try:
            resp = requests.get(url, headers=self.headers, timeout=15)
            resp.raise_for_status()
            resp.encoding = 'utf-8'
            return resp.text
        except Exception as e:
            print(f"❌ 網路錯誤: {e}")
            return None

    def parse_news(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        news_list = []

        # 偵測新聞項目
        items = soup.find_all('div', class_=re.compile(r'(d-item|item|news)', re.I))
        if not items:
            items = soup.find_all('li')  # fallback
        
        for item in items:
            try:
                a_tag = item.find('a', href=True)
                if not a_tag:
                    continue
                title = a_tag.get_text(strip=True)
                href = a_tag['href']
                if href.startswith('/'):
                    url = self.base_url + href
                elif not href.startswith('http'):
                    url = self.base_url + '/' + href
                else:
                    url = href

                # 找日期
                date_match = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', item.get_text())
                date = "未知"
                if date_match:
                    date = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"

                # 判斷類別
                category = "公告"
                if any(k in title for k in ["體育館", "場館"]):
                    category = "體育場館"
                elif any(k in title for k in ["教學", "研習"]):
                    category = "教學研習"
                elif any(k in title for k in ["活動", "訓練", "競賽"]):
                    category = "活動訓練"

                if title and url:
                    news_list.append({
                        "日期": date,
                        "標題": title,
                        "連結": url,
                        "類別": category,
                        "抓取時間": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
            except Exception:
                continue

        # 去重
        seen = set()
        unique_news = []
        for n in news_list:
            if n["連結"] not in seen:
                seen.add(n["連結"])
                unique_news.append(n)

        return unique_news

    def get_hash(self, obj):
        j = json.dumps(obj, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(j.encode("utf-8")).hexdigest()

    def load_history(self):
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    obj = json.load(f)
                    self.last_hash = obj.get("last_hash")
                    self.news_cache = obj.get("news", [])
                    return True
            except Exception as e:
                print(f"⚠️ 載入歷史記錄錯誤: {e}")
        return False

    def save_history(self, news_list, page_hash):
        obj = {
            "last_hash": page_hash,
            "last_update": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "news": news_list
        }
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)

    def detect_new(self, current_news):
        if not self.news_cache:
            return current_news
        old_urls = {n["連結"] for n in self.news_cache}
        return [n for n in current_news if n["連結"] not in old_urls]

    def save_to_files(self, news_list):
        if not news_list:
            return
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        df = pd.DataFrame(news_list)
        csv_file = self.data_dir / f"pu_sports_news_{ts}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        json_file = self.data_dir / f"pu_sports_news_{ts}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(news_list, f, ensure_ascii=False, indent=2)
        print(f"✓ 已儲存: {csv_file.name} / {json_file.name}")

    def display(self, news_list, title="新增消息"):
        if not news_list:
            return
        print(f"\n{'='*70}")
        print(f"📰 {title} (共 {len(news_list)} 則)")
        print(f"{'='*70}")
        for i, n in enumerate(news_list, 1):
            print(f"{i:2d}. [{n['類別']}] {n['日期']} - {n['標題']}")
            print(f"    連結: {n['連結']}")
            print()

    def run_once(self):
        print(f"\n{'='*70}")
        print(f"🔍 開始檢查: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")

        self.load_history()
        html = self.fetch_html(self.main_url)
        if html is None:
            print("❌ 無法取得網頁資料")
            return

        news_list = self.parse_news(html)
        if not news_list:
            print("⚠️ 沒抓到任何新聞，請檢查網站結構")
            debug_file = self.data_dir / f"debug_html_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"📄 HTML已儲存至 {debug_file} 供檢查")
            return

        print(f"✓ 成功解析 {len(news_list)} 則消息")
        page_hash = self.get_hash(news_list)

        if page_hash == self.last_hash:
            print("✓ 資料無變化")
        else:
            new_items = self.detect_new(news_list)
            if new_items:
                self.display(new_items, "新增消息")
            else:
                print("✓ 有更新但無新增項目")

            # 儲存爬蟲原始資料
            self.save_to_files(news_list)
            self.save_history(news_list, page_hash)

            # --- 生成前端可讀 JSON ---
            frontend_news = [
                {
                    "date": n["日期"],
                    "title": n["標題"],
                    "url": n["連結"],
                    "category": n["類別"]
                } for n in news_list
            ]
            frontend_file = Path("data/latest_news.json")  # 前端可讀資料路徑
            frontend_file.parent.mkdir(exist_ok=True)
            with open(frontend_file, "w", encoding="utf-8") as f:
                json.dump(frontend_news, f, ensure_ascii=False, indent=2)
            print(f"✓ 前端 JSON 已更新: {frontend_file}")

        print(f"{'='*70}\n✅ 檢查完成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")

    def run_monitor(self, interval_days=7):
        print(f"{'='*70}")
        print("🤖 靜宜大學體育室新聞監控系統啟動")
        print(f"{'='*70}")
        print(f"⏰ 監控間隔: {interval_days} 天")
        print(f"🔗 網址: {self.main_url}")
        print(f"{'='*70}")
        self.run_once()
        try:
            while True:
                time.sleep(interval_days * 24 * 3600)
                self.run_once()
        except KeyboardInterrupt:
            print("\n✋ 停止監控")

# 主程式
if __name__ == "__main__":
    monitor = PUSportsMonitor()
    print("="*70)
    print("靜宜大學體育室新聞監控系統")
    print("="*70)
    print("1. 執行一次檢查")
    print("2. 每週監控 (預設)")
    print("3. 自訂間隔天數")
    print("="*70)
    choice = input("請選擇 (1-3，Enter=預設2): ").strip()
    if choice == "1":
        monitor.run_once()
    elif choice == "3":
        try:
            days = int(input("請輸入天數: ").strip())
            if days < 1:
                print("❌ 間隔天數必須 > 0")
            else:
                monitor.run_monitor(interval_days=days)
        except ValueError:
            print("❌ 請輸入有效數字")
    else:
        monitor.run_monitor(interval_days=7)
