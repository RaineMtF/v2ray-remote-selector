import requests
from bs4 import BeautifulSoup
import yaml
import urllib.parse
import time
import random
import re

def load_config():
    with open('config.yml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_proxies():
    config = load_config()
    
    base_url = "https://www.freeproxy.world/"
    
    # --- 增强型防反爬头部 ---
    headers = {
        'User-Agent': random.choice([
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        ]),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://www.google.com/',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site'
    }

    all_v2ray_configs = []
    session = requests.Session()

    for page in range(1, 11):
        # 构造带有 page 参数的 URL
        current_config = config.copy()
        current_config['page'] = page
        params = urllib.parse.urlencode(current_config)
        target_url = f"{base_url}?{params}"
        
        print(f"正在请求第 {page} 页: {target_url}")

        try:
            response = session.get(target_url, headers=headers, timeout=15)
            response.raise_for_status()
            html_content = response.text
            
            # 随机休眠模拟真人
            time.sleep(random.uniform(0.5, 1.5))
            
        except Exception as e:
            print(f"请求第 {page} 页失败: {e}")
            break

        soup = BeautifulSoup(html_content, 'html.parser')
        
        # --- 宽泛匹配逻辑 ---
        tables = soup.find_all('table')
        
        page_configs = []

        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 4:
                    continue
                    
                try:
                    # 1. IP (第一个 td)
                    ip = cells[0].get_text(strip=True)
                    if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
                        continue

                    # 2. Port (第二个 td)
                    port = cells[1].get_text(strip=True)

                    # 3. Country Code
                    country_code = "Unknown"
                    country_link = cells[2].find('a', href=True)
                    if country_link:
                        match = re.search(r'country=([A-Z]+)', country_link['href'])
                        if match:
                            country_code = match.group(1)

                    # 4. City (第四个 td)
                    city = cells[3].get_text(strip=True)
                    encoded_city = urllib.parse.quote(city)

                    # 拼接格式
                    proxy_str = f"socks://Og@{ip}:{port}#{country_code},%20{encoded_city}"
                    page_configs.append(proxy_str)
                    
                except Exception:
                    continue

        if not page_configs:
            print(f"第 {page} 页未提取到有效数据，停止抓取。")
            break
        
        print(f"第 {page} 页成功抓取 {len(page_configs)} 个代理")
        all_v2ray_configs.extend(page_configs)
        
        # 最后一页之后不需要多余的休眠（如果是第10页也不需要）
        if page < 10:
            time.sleep(random.uniform(1, 2))

    return all_v2ray_configs

def save_to_file(configs):
    with open('all_config.txt', 'w', encoding='utf-8') as f:
        if configs:
            f.write('\n'.join(configs) + '\n')
    print(f"所有任务完成，总计抓取 {len(configs)} 个代理，已保存到 all_config.txt")


if __name__ == "__main__":
    results = get_proxies()
    save_to_file(results)
