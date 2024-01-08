import requests
import re
import time
import base64
import argparse
import openpyxl
import urllib3
import os
import asyncio
import aiohttp
import aiofiles
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from concurrent.futures import ThreadPoolExecutor

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

FOFA_LINK_PATTERN = re.compile(r'<a href="([^"]*)" target="_blank">')
ICP_PATTERN_icp_beianx = re.compile(r'<a href="/company/\d+">(.*?)</a>')
ICP_PATTERN_icplishi = re.compile(r'<td><a href="/company/.*?/" target="_blank">(.*?)</a></td>')
ICP_PATTERN_icp_jucha = re.compile(r'"mc":"(.*?)"')

cookie = None
executed_domains = set()

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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'
}

HEADERS1 = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Content-Length": "72"
}

semaphore = asyncio.Semaphore(1)
async def async_fofa(session, b64, ip):
    url = f"https://fofa.info/result?qbase64={b64}"
    try:
        async with semaphore:
            response = await session.get(url, headers=HEADERSF, timeout=10, ssl=False)
            if response.status == 200:
                links = extract_links(await response.text())
                results = extract_domains(links)
                return results, ip
            else:
                print(f"FOFA请求失败！错误码：{response.status}" + ip)
                return [], ip
    except (requests.exceptions.RequestException, asyncio.TimeoutError) as e:
        print(f"FOFA请求失败: {e}\t\t" + ip)
        return [], ip

async def async_icp(session, domain, ip):
    domains_list = []
    domains_list.append(domain)
    parts = domain.split(".")
    while len(parts) > 2:
        parts.pop(0)
        partial_domain = ".".join(parts)
        domains_list.append(partial_domain)
    icpba = None
    response_text = None
    for ym in domains_list:
        if ym in executed_domains:
            return
        executed_domains.add(ym)
        print(ym + "\t开始查询")
        if cookie:
            response_text = await icp_beianx(ym, session)       
        if response_text:
            icpba = icp_ba_beianx(response_text)
        if icpba is not None:
            return [icpba, domain, ip]

    if icpba is None:
        for ym in domains_list:
            response_text = await icp_icplishi(ym, session)
            if response_text:
                icpba = icp_ba_icplishi(response_text)
            if icpba is not None:
                return [icpba, domain, ip]

    if icpba is None:
        for ym in domains_list:
            try:
                response_text = await asyncio.wait_for(icp_jucha(ym, session), timeout=5)
            except asyncio.TimeoutError:
                continue
            if response_text:
                icpba = icp_ba_jucha(response_text)
            if icpba is not None:
                return [icpba, domain, ip]

    return [icpba, domain, ip] if icpba is not None else [None, domain, ip]

async def icp_beianx(domain, session):
    global cookie
    url = f"https://www.beianx.cn/search/{domain}/"
    HEADERSB = {"Cookie": "acw_sc__v2=" + cookie}
    try:
        async with session.get(url, headers=HEADERSB, verify_ssl=False, timeout=5) as response:
            response.raise_for_status()
            if "0x4818" in await response.text():
                print("重新获取cookie")
                cookie = await beianx_cookie(session)
            else:
                if "没有查询到记录" in await response.text():
                    return None
                else:
                    return await response.text()
    except requests.exceptions.RequestException as e:
        print(f"ICP请求失败: {e}")
        return None

async def icp_icplishi(domain, session):
    url = f"https://icplishi.com/{domain}/"
    try:
        async with session.get(url=url, timeout=3) as response:  
            response.raise_for_status()
            if response.status == 200:
                return await response.text()
            else:
                print(f"ICP请求失败！错误码：{response.status}")
                return None
    except asyncio.TimeoutError:
        #print(f"ICP请求超时")
        return None
    except requests.exceptions.RequestException as e:
        print(f"ICP请求失败: {e}")
        return None


async def icp_jucha(domain, session):
    url = f"https://www.jucha.com/item/search"
    data_jucha = {
        'domain': domain,
        'items[]': 24,
        'type': 1,
        'route': 'beian',
        'is_hide_zonghe': 0,
        'gx': 0
    }
    time.sleep(0.1)
    try:
        async with session.post(url, headers=HEADERS1, data=data_jucha, verify_ssl=False, timeout=5) as response:
            response.raise_for_status()
            if response.status == 200:
                return await response.text()
            else:
                print(f"ICP请求失败！错误码：{response.status}")
                return None
    except requests.exceptions.RequestException as e:
        print(f"ICP请求失败: {e}")
        return None

async def beianx_cookie(session):
    url = "https://www.beianx.cn/search"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    chrome_driver_path = os.path.join(script_dir, "chromedriver.exe")
    chrome_service = Service(executable_path=chrome_driver_path)
    
    driver = webdriver.Chrome(service=chrome_service)

    driver.get(url)

    cookies = driver.get_cookies()
    
    acw_sc__v2_value = None
    for cookie in cookies:
        if cookie['name'] == 'acw_sc__v2':
            acw_sc__v2_value = cookie['value']
            break
    print(acw_sc__v2_value)
    driver.quit()
    return acw_sc__v2_value

async def async_process_url(session, url):
    iplist, dmlist = ipdm(url)
    results = []
    fofaym = {}

    for ip in iplist:
        b64 = bas64(ip)
        fofa_results, ip_result = await async_fofa(session, b64, ip)
        for fofadm in fofa_results:
            fofaym[fofadm] = ip_result
        print(ip + "\t存在>>" + str(len(fofaym)) + "<<个域名待测")
    
    fofa_tasks = [async_process_fofa_result(session, fofadm, ip_result) for fofadm, ip_result in fofaym.items()]
    fofa_results = await asyncio.gather(*fofa_tasks)
    results.extend(fofa_results)
    
    icp_tasks = [async_icp(session, domain, "") for domain in dmlist]
    icp_results = await asyncio.gather(*icp_tasks)
    results.extend([result for result in icp_results if result])
    return results

async def async_process_fofa_result(session, fofadm, ip_result):
    jg = await async_icp(session, fofadm, ip_result)
    if jg:
        return jg
    return []

def icp_ba_beianx(response_text):
    results = re.findall(ICP_PATTERN_icp_beianx, response_text)
    return ' '.join(results) if results else None

def icp_ba_icplishi(response_text):
    results = re.findall(ICP_PATTERN_icplishi, response_text)
    return ' '.join(results) if results else None

def icp_ba_jucha(response_text):
    results = re.findall(ICP_PATTERN_icp_jucha, response_text)
    return ' '.join(results) if results else None

def extract_links(response_text):
    return re.findall(FOFA_LINK_PATTERN, response_text)

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
    for result in results:
        if len(result) >= 3:
            ba = result[0]
            ym = result[1]
            ip = result[2]
            ba_str = str(ba) if ba is not None else " "
            ip_str = ''.join(str(b) for b in ip) if ip and any(ip) else " "
            sheet.append([ba_str, str(ym), ip_str])
        else:
            pass

def create_workbook():
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet['A1'] = '备案主体'
    sheet['B1'] = '主域名'
    sheet['C1'] = 'IP地址'
    return workbook, sheet

async def async_process_file(file_path, sheet, session):
    async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
        urls = await file.read()
    urls = urls.splitlines()
    tasks = [async_process_url(session, url) for url in urls]
    all_results = await asyncio.gather(*tasks)
    for results in all_results:
        xlsx(results, sheet)

async def run_async_main(file_path):
    start_time = time.time()
    connector = aiohttp.TCPConnector(limit=20)
    async with aiohttp.ClientSession() as session:
        global cookie
        cookie = await beianx_cookie(session)
        workbook, sheet = create_workbook()
        await async_process_file(file_path, sheet, session)
        workbook.save('data.xlsx')
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"脚本执行耗时：{elapsed_time:.2f} 秒")

def print_icpscan_banner():
    print("=" * 70)
    print("""
 __     ______     ______   ______     ______     ______     __   __    
/\ \   /\  ___\   /\  == \ /\  ___\   /\  ___\   /\  __ \   /\ "-.\ \   
\ \ \  \ \ \____  \ \  _-/ \ \___  \  \ \ \____  \ \  __ \  \ \ \-.  \  
 \ \_\  \ \_____\  \ \_\    \/\_____\  \ \_____\  \ \_\ \_\  \ \_\\"\_\ 
  \/_/   \/_____/   \/_/     \/_____/   \/_____/   \/_/\/_/   \/_/ \/_/ 
""")
    print("\t\t\t\t\t\t\tVersion:0.6")
    print("\t\t\t\t\t关注微信公众号:樱花庄的本间白猫")
    print("=" * 70)
    print("\t\tIcpScan开始执行")

def main():
    print_icpscan_banner()
    parser = argparse.ArgumentParser(description='ICPScan由本间白猫开发,旨在快速反查IP、域名归属')
    parser.add_argument('-f', '--file', help='指定使用的路径文件 -f url.txt')
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_async_main(args.file))

if __name__ == "__main__":
    main()
