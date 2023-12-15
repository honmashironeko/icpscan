import requests
import re
import time
import base64
import argparse
import openpyxl
import urllib3
import concurrent.futures

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

FOFA_LINK_PATTERN = re.compile(r'<a href="([^"]*)" target="_blank">')
ICP_PATTERN_icp_beianx = re.compile(r'<a href="/company/\d+">(.*?)</a>')
ICP_PATTERN_icplishi = re.compile(r'<td><a href="/company/.*?/" target="_blank">(.*?)</a></td>')
ICP_PATTERN_icp_jucha = re.compile(r'"mc":"(.*?)"')

executed_domains = set()
SESSION = requests.Session()
cookie = None  # 全局变量

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}
HEADERSF = {
    'Connection': 'keep-alive',
    'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-User': '?1',
    'Sec-Fetch-Dest': 'document',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'zh-CN,zh;q=0.9'
}

HEADERS1 = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Content-Length": "72"
}


def fofa(b64, ip):
    url = f"https://fofa.info/result?qbase64={b64}"
    try:
        with SESSION.get(url, headers=HEADERSF, timeout=5) as response:
            response.raise_for_status()
            if response.status_code == 200:
                #print(f"{ip} FOFA请求发送成功！")
                links = extract_links(response.text)
                results = extract_domains(links)
                return results, ip
            else:
                print(f"FOFA请求失败！错误码：{response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"FOFA请求失败: {e}\t\t"+ip)
        return [], ip


def icp(domain, ip):
    dot_count = domain.count(".")
    max_retries = max(0, dot_count - 1)  # 最大重试次数为点的数量减一，最小为0
    current_retry = 0
    original_domain = domain  # 备份原始域名

    while current_retry <= max_retries:
        icpba = None
        response_text_beianx = None

        if original_domain in executed_domains: 
            return

        if cookie:
            response_text_beianx = icp_beianx(original_domain)

        if response_text_beianx:
            icpba = icp_ba_beianx(response_text_beianx)
        else:
            response_text_icplishi = icp_icplishi(original_domain)
            if response_text_icplishi:
                icpba = icp_ba_icplishi(response_text_icplishi)
            else:
                response_text_jucha = icp_jucha(original_domain)
                if response_text_jucha:
                    icpba = icp_ba_jucha(response_text_jucha)

        executed_domains.add(original_domain)  # 使用备份的域名进行添加

        if icpba:
            return [icpba, original_domain, ip]
        else:
            index_of_dot = original_domain.find(".")
            if index_of_dot != -1:
                original_domain = original_domain[index_of_dot + 1:]
                current_retry += 1
            else:
                break

    return [icpba, domain, ip] if icpba is not None else [None, domain, ip]





def process_url(url):
    iplist, dmlist = ipdm(url)
    results = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        # 处理 FOFA 结果
        fofa_futures = [executor.submit(fofa, bas64(ip), ip) for ip in iplist]
        for fofa_future in concurrent.futures.as_completed(fofa_futures):
            fofa_results, ip_result = fofa_future.result()
            for fofadm in fofa_results:
                jg = icp(fofadm, ip_result)
                if jg:
                    results.extend(jg)

        # 处理域名结果
        domain_futures = [executor.submit(icp, domain, "") for domain in dmlist]
        for domain_future in concurrent.futures.as_completed(domain_futures):
            jg = domain_future.result()
            if jg:
                results.extend(jg)

    return results

def icp_beianx(domain):
    url = f"https://www.beianx.cn/search/{domain}/"
    HEADERSB = {"Cookie":"acw_sc__v2="+cookie}
    try:
        with requests.get(url, headers=HEADERSB, verify=False,timeout=5) as response:
            response.raise_for_status()
            if "0x4818" in response.text:
                print("beianx提供的cookie无效，请检查")
            else:
                if "没有查询到记录" in response.text:
                    return None
                else:
                    return response.text
    except requests.exceptions.RequestException as e:
        print(f"ICP请求失败: {e}")
        return None

def icp_icplishi(domain):
    url = f"https://icplishi.com/{domain}/"
    try:
        with requests.get(url, timeout=5) as response:
            response.raise_for_status()
            if response.status_code == 200:
                return response.text
            else:
                print(f"ICP请求失败！错误码：{response.status_code}")
                return None
    except requests.exceptions.RequestException as e:
        #print(f"ICP请求失败: {e}")
        return None

def icp_jucha(domain):
    url = f"https://www.jucha.com/item/search"
    data_jucha = {
        'domain': domain,
        'items[]': 24,
        'type': 1,
        'route': 'beian',
        'is_hide_zonghe': 0,
        'gx': 0
    }
    try:
        with requests.post(url, headers=HEADERS1, data=data_jucha, verify=False, timeout=5) as response:
            response.raise_for_status()
            if response.status_code == 200:
                return response.text
            else:
                print(f"ICP请求失败！错误码：{response.status_code}")
                return None
    except requests.exceptions.RequestException as e:
        print(f"ICP请求失败: {e}")
        return None

def extract_links(response_text):
    return re.findall(FOFA_LINK_PATTERN, response_text)

def icp_ba_beianx(response_text):
    results = re.findall(ICP_PATTERN_icp_beianx, response_text)
    return ' '.join(results) if results else None

def icp_ba_icplishi(response_text):
    results = re.findall(ICP_PATTERN_icplishi, response_text)
    return ' '.join(results) if results else None

def icp_ba_jucha(response_text):
    results = re.findall(ICP_PATTERN_icp_jucha, response_text)
    return ' '.join(results) if results else None

def extract_domains(links):
    domains = []

    for url in links:
        match = re.search(r'^(?:https?://)?([^:/]+)', url)
        if match:
            domain = match.group(1)
            domains.append(domain)
    return domains

def bas64(ip):
    string = f'is_domain=true && ip="{ip}"'
    return base64.b64encode(string.encode('utf-8')).decode('utf-8')

def ipdm(string):
    ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    domain_pattern = r'(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}'
    return re.findall(ip_pattern, string), re.findall(domain_pattern, string)

def xlsx(results, sheet):
    if results:
        ba = results[0]
        ym = results[1]
        ip = results[2]
        ba_str = str(ba) if ba is not None else " "
        ip_str = ''.join(str(b) for b in ip) if ip and any(ip) else " "
        sheet.append([ba_str, str(ym), ip_str])

def create_workbook():
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet['A1'] = '备案主体'
    sheet['B1'] = '主域名'
    sheet['C1'] = 'IP地址'
    return workbook, sheet

def process_file(file_path, sheet):
    workbook, sheet = create_workbook()  # 修改此行
    with open(file_path, 'r') as file:
        urls = file.read().splitlines()
        total_lines = len(urls)

        progress_bar = ProgressBar(total_lines)

        for idx, url in enumerate(urls, start=1):
            results = process_url(url)
            xlsx(results, sheet)
            progress_bar.update()

        progress_bar.finish()

    workbook.save('data.xlsx')


def print_icpscan_banner():
    print("=" * 70)
    print("""
 __     ______     ______   ______     ______     ______     __   __    
/\ \   /\  ___\   /\  == \ /\  ___\   /\  ___\   /\  __ \   /\ "-.\ \   
\ \ \  \ \ \____  \ \  _-/ \ \___  \  \ \ \____  \ \  __ \  \ \ \-.  \  
 \ \_\  \ \_____\  \ \_\    \/\_____\  \ \_____\  \ \_\ \_\  \ \_\\"\_\ 
  \/_/   \/_____/   \/_/     \/_____/   \/_____/   \/_/\/_/   \/_/ \/_/ 
""")
    print("\t\t\t\t\t\t\tVersion:0.5")
    print("\t\t\t\t\t关注微信公众号:樱花庄的本间白猫")
    print("=" * 70)
    print("\t\tIcpScan开始执行")

class ProgressBar:
    def __init__(self, total):
        self.total = total
        self.current = 0

    def update(self, increment=1):
        self.current += increment
        progress = (self.current / self.total) * 100
        self._draw(progress)

    def _draw(self, progress):
        bar_length = 40
        block = int(round(bar_length * progress / 100))
        progress_bar = "=" * block + ">" + "." * (bar_length - block)
        print(f"\r[{progress_bar}] {progress:.2f}%\t\t", end="", flush=True)

    def finish(self):
        print("\n处理完成。")

def main():
    global cookie  # 声明 cookie 为全局变量
    start_time = time.time()  # 记录开始时间
    print_icpscan_banner()
    parser = argparse.ArgumentParser(description='ICPScan由本间白猫开发,旨在快速反查IP、域名归属')
    parser.add_argument('-f', '--file', help='指定使用的路径文件 -f url.txt')
    parser.add_argument('-c', '--cookie', help='指定cookie值 -c your_cookie_value')
    args = parser.parse_args()

    cookie = args.cookie
    sheet = create_workbook()
    process_file(args.file, sheet)
    end_time = time.time()  # 记录结束时间
    elapsed_time = end_time - start_time
    print(f"脚本执行耗时：{elapsed_time:.2f} 秒")

if __name__ == "__main__":
    main()
