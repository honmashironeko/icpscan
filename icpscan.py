import requests
import re
import base64
import argparse
import openpyxl
import time
from concurrent.futures import ThreadPoolExecutor

FOFA_LINK_PATTERN = re.compile(r'<a href="([^"]*)" target="_blank">')
ICP_PATTERN = re.compile(r'<td><a href="/company/.*?/" target="_blank">(.*?)</a></td>')
DOMAIN_PATTERN = re.compile(r'(?<=\.)([a-z]+\.[a-z]+)')

SESSION = requests.Session()
processed_paths = set()

def fofa(b64,ip):
    url = f"https://fofa.info/result?qbase64={b64}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    try:
        with SESSION.get(url, headers=headers, timeout=10) as response:
            response.raise_for_status()
            if response.status_code == 200:
                print(f"{ip} FOFA请求发送成功！")
                links = extract_links(response.text)
                domains = main_domains(links)
                icp_results = [icp(domain, ip) for domain in domains if icp(domain, ip) is not None]
                return icp_results
            else:
                print(f"FOFA请求失败！错误码：{response.status_code}")
    except requests.RequestException as e:
        print(f"FOFA请求失败: {e}")
        return None

def icp(path, ip):
    global processed_paths  # 使用全局变量
    url = f"https://icplishi.com/{path}/"

    # 检查路径是否已处理过，如果是则直接返回
    if path in processed_paths:
        #print(f"路径 {path} 已处理过，跳过...")
        return None, path, None
    # 在处理完成后将路径添加到集合中
    processed_paths.add(path)
    headers = {
        'Host': 'icplishi.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    try:
        time.sleep(0.2)
        with SESSION.get(url, headers=headers) as response:
            response.raise_for_status()
            if response.status_code == 200:
                icpba = icpbam(response.text)
                return icpba, path, ip
            else:
                print(f"ICP请求失败！错误码：{response.status_code}")
                return None, path, None
    except requests.RequestException as e:
        print(f"ICP请求失败: {e}")
        return None, path, None

def icpbam(response_text):
    results = re.findall(ICP_PATTERN, response_text)
    return ' '.join(results) if results else None

def extract_links(response_text):
    return re.findall(FOFA_LINK_PATTERN, response_text)

def main_domains(domains):
    return {re.search(DOMAIN_PATTERN, domain).group() for domain in domains if re.search(DOMAIN_PATTERN, domain)}

def main_domains1(domain):
    match = re.search(DOMAIN_PATTERN, domain)
    return match.group() if match else domain

def bas64(ip):
    string = f'is_domain=true && ip="{ip}"'
    return base64.b64encode(string.encode('utf-8')).decode('utf-8')

def ipdm(string):
    ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    domain_pattern = r'(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}'
    return re.findall(ip_pattern, string), re.findall(domain_pattern, string)

def xlsx(results, processed_domains, sheet):
    for ip, ym, ba in results:
        if ym not in processed_domains:
            ip_str = str(ip) if ip is not None else "N/A"
            ba_str = ''.join(str(b) for b in ba) if ba and any(ba) else "N/A"
            sheet.append([ip_str, str(ym), ba_str])
            processed_domains.add(ym)

def process_url(url,  processed_domains, sheet):
    iplist, dmlist = ipdm(url)
    results = []

    for ip in iplist:
        b64 = bas64(ip)
        icp_results = fofa(b64,ip)
        if icp_results:
            results.extend(icp_results)

    for ym in dmlist:
        ym = main_domains1(ym)
        _, _, ba = icp(ym, None)
        if ba:
            results.append(("N/A", ym, ''.join(ba)))

    return results, processed_domains

def print_icpscan_banner():
    print("=" * 70)
    print("""
 __     ______     ______   ______     ______     ______     __   __    
/\ \   /\  ___\   /\  == \ /\  ___\   /\  ___\   /\  __ \   /\ "-.\ \   
\ \ \  \ \ \____  \ \  _-/ \ \___  \  \ \ \____  \ \  __ \  \ \ \-.  \  
 \ \_\  \ \_____\  \ \_\    \/\_____\  \ \_____\  \ \_\ \_\  \ \_\\"\_\ 
  \/_/   \/_____/   \/_/     \/_____/   \/_____/   \/_/\/_/   \/_/ \/_/ 
""")
    print("\t\t\t\t\t关注微信公众号:樱花庄的本间白猫")
    print("=" * 70)

def main():
    print_icpscan_banner()
    parser = argparse.ArgumentParser(description='ICPScan由本间白猫开发,旨在快速反查IP、域名归属')
    parser.add_argument('-f', '--file', help='指定使用的路径文件 -f url.txt')
    parser.add_argument('-t', '--threads', type=int, default=2, help='指定线程数量,注意不要太大,会少内容 -t 5')
    args = parser.parse_args()

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet['A1'] = '备案主体'
    sheet['B1'] = '主域名'
    sheet['C1'] = 'IP地址'

    with open(args.file, 'r') as file:
        urls = file.read()
        processed_domains = set()

        with ThreadPoolExecutor(max_workers=args.threads) as executor:
            results = executor.map(
                lambda url: process_url(url,processed_domains, sheet),
                urls.splitlines(),
            )

            for result, _ in results:
                xlsx(result, processed_domains, sheet)

    workbook.save('data.xlsx')
    print("执行完毕！")

if __name__ == "__main__":
    main()
