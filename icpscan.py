import requests
import re
import time
import tldextract
import base64
import argparse
import openpyxl
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed

FOFA_LINK_PATTERN = re.compile(r'<a href="([^"]*)" target="_blank">')
ICP_PATTERN = re.compile(r'<td><a href="/company/.*?/" target="_blank">(.*?)</a></td>')

MAX_THREADS = 5
processed_icp_domains = {}
SESSION = requests.Session()
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

requests.adapters.DEFAULT_RETRIES = 5
SESSION = requests.Session()
SESSION.keep_alive = False

def fofa(b64, ip):
    url = f"https://fofa.info/result?qbase64={b64}"
    try:
        with SESSION.get(url, headers=HEADERS, timeout=10) as response:
            response.raise_for_status()
            if response.status_code == 200:
                print(f"{ip} FOFA请求发送成功！")
                links = extract_links(response.text)
                domains = extract_main_domain(links)
                icp_results = [icp(domain, ip) for domain in domains]
                return [result for result in icp_results if result is not None]
            else:
                print(f"FOFA请求失败！错误码：{response.status_code}")
    except requests.RequestException as e:
        print(f"FOFA请求失败: {e}")
        return []

def icp(domain, ip):
    if domain in processed_icp_domains:
        return processed_icp_domains[domain]

    url = f"https://icplishi.com/{domain}/"
    try:
        with SESSION.get(url, headers=HEADERS) as response:
            response.raise_for_status()
            if response.status_code == 200:
                icpba = icpbam(response.text)
                result = icpba, domain, ip
                processed_icp_domains[domain] = result
                return result
            else:
                print(f"ICP请求失败！错误码：{response.status_code}")
                processed_icp_domains[domain] = None
                return None, domain, None
    except requests.RequestException as e:
        print(f"ICP请求失败: {e}")
        processed_icp_domains[domain] = None
        return None, domain, None

def process_url(url, processed_domains, sheet, max_threads):
    iplist, dmlist = ipdm(url)
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_threads) as executor:
        # 并发处理FOFA请求
        fofa_futures = {executor.submit(fofa, bas64(ip), ip): ip for ip in iplist}
        for future in concurrent.futures.as_completed(fofa_futures):
            ip = fofa_futures[future]
            fofa_results = future.result()
            if fofa_results:
                results.extend(fofa_results)

        # 并发处理ICP请求
        icp_futures = {executor.submit(icp, ym, None): ym for ym in dmlist}
        for future in concurrent.futures.as_completed(icp_futures):
            icp_result = future.result()
            if icp_result:
                results.append(icp_result)

    return results, processed_domains

def extract_links(response_text):
    return re.findall(FOFA_LINK_PATTERN, response_text)

def icpbam(response_text):
    results = re.findall(ICP_PATTERN, response_text)
    return ' '.join(results) if results else None

def extract_main_domain(urls):
    domains = []
    for url in urls:
        ext = tldextract.extract(url)
        domain = f"{ext.domain}.{ext.suffix}"
        domains.append(domain)
    return domains

def bas64(ip):
    string = f'is_domain=true && ip="{ip}"'
    return base64.b64encode(string.encode('utf-8')).decode('utf-8')

def ipdm(string):
    ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    domain_pattern = r'(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}'
    return re.findall(ip_pattern, string), re.findall(domain_pattern, string)

def xlsx(results, processed_domains, sheet):
    for ba, ym, ip in results:
        if ym not in processed_domains:
            ip_str = str(ba) if ba is not None else " "
            ba_str = ''.join(str(b) for b in ip) if ip and any(ip) else " "
            sheet.append([ip_str, str(ym), ba_str])
            processed_domains.add(ym)

def create_workbook():
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet['A1'] = '备案主体'
    sheet['B1'] = '主域名'
    sheet['C1'] = 'IP地址'
    return workbook, sheet

def process_file(file_path, sheet, max_threads):
    global processed_icp_domains
    processed_icp_domains = {}
    with open(file_path, 'r') as file:
        urls = file.read()
        processed_domains = set()

        for url in urls.splitlines():
            results, _ = process_url(url, processed_domains, sheet, max_threads)
            xlsx(results, processed_domains, sheet)

def print_icpscan_banner():
    print("=" * 70)
    print("""
 __     ______     ______   ______     ______     ______     __   __    
/\ \   /\  ___\   /\  == \ /\  ___\   /\  ___\   /\  __ \   /\ "-.\ \   
\ \ \  \ \ \____  \ \  _-/ \ \___  \  \ \ \____  \ \  __ \  \ \ \-.  \  
 \ \_\  \ \_____\  \ \_\    \/\_____\  \ \_____\  \ \_\ \_\  \ \_\\"\_\ 
  \/_/   \/_____/   \/_/     \/_____/   \/_____/   \/_/\/_/   \/_/ \/_/ 
""")
    print("\t\t\t\t\tVersion:0.3")
    print("\t\t\t\t\t关注微信公众号:樱花庄的本间白猫")
    print("=" * 70)

def main():
    start_time = time.time()  # 记录开始时间
    print_icpscan_banner()
    parser = argparse.ArgumentParser(description='ICPScan由本间白猫开发,旨在快速反查IP、域名归属')
    parser.add_argument('-f', '--file', help='指定使用的路径文件 -f url.txt')
    parser.add_argument('-t', '--threads', type=int, default=MAX_THREADS, help='指定线程数，默认为5')
    args = parser.parse_args()

    workbook, sheet = create_workbook()
    process_file(args.file, sheet, args.threads) 
    workbook.save('data.xlsx')
    print("执行完毕！")
    end_time = time.time()  # 记录结束时间
    elapsed_time = end_time - start_time
    print(f"脚本执行耗时：{elapsed_time:.2f} 秒")

if __name__ == "__main__":
    main()
