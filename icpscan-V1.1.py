from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from urllib.parse import urlparse
from selenium import webdriver
import pandas as pd
import tldextract
import argparse
import requests
import urllib3
import asyncio
import aiohttp
import random
import base64
import time
import re
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# 正则匹配类
FOFA_LINK_PATTERN = re.compile(r'<a href="([^"]*)" target="_blank">')


# FOFA请求头
HEADERSF = {
    'Connection': 'keep-alive',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'
}

# 提取一级域名
def extract_domain(domain):
    return tldextract.extract(domain).registered_domain

# 区分IP和域名
def ipdomain(string):
    ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    domain_pattern = r'(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}'
    return re.findall(ip_pattern, string), re.findall(domain_pattern, string)

# 读取文件并分割成列表
def read_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read().splitlines()

# FOFA提取域名
def extract_links(response_text):
    return re.findall(FOFA_LINK_PATTERN, response_text)
def extract_domains(links):
    domains = [urlparse(link).hostname for link in links if urlparse(link).hostname]
    return domains

# FOFA计算base64
def base64_encode(ip):
    return base64.b64encode(f'is_domain=true && ip="{ip}"'.encode('utf-8')).decode('utf-8')

# FOFA异步查询
sem = asyncio.Semaphore(8)
async def fofa_async(b64, ip, retry_count=3):
    async with sem:
        url = f"https://fofa.info/result?qbase64={b64}"
        for _ in range(retry_count):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=HEADERSF, timeout=10, verify_ssl=False) as response:
                        if response.status == 200:
                            text = await response.text()
                            if "资源访问每天限制" in text:
                                print("当前IP已达到查询上限，请更换IP")
                                return "stop"
                            links = extract_links(await response.text())
                            results = extract_domains(links)
                            print(f"FOFA查询完毕 IP: {ip}")
                            return results, ip
                        else:
                            print(f"FOFA请求失败！错误码: {response.status} - {ip}")
            except aiohttp.ClientError as e:
                print(f"FOFA请求失败: {e} - {ip}")

        print(f"多次尝试后无法成功获取结果 - {ip}")
        return [], ip
    
def get_icp_respons(domain, headers, data):
    url = "https://hlwicpfwc.miit.gov.cn/icpproject_query/api/icpAbbreviateInfo/queryByCondition"
    response = requests.post(url, data=data,timeout=10, headers=headers,  verify=False)
    return response

# 查询备案
def icp(domain):
    with open('token.txt', 'r') as file:
        lines = file.readlines()
        sign = lines[0].strip() 
        token = lines[1].strip() 
        uuid = lines[2].strip()
    headers = {
        "Host": "hlwicpfwc.miit.gov.cn",
        "Connection": "keep-alive",
        "Content-Length": "67",
        "sec-ch-ua": "\"Chromium\";v=\"122\", \"Not(A:Brand\";v=\"24\", \"Google Chrome\";v=\"122\"",
        "sec-ch-ua-mobile": "?0",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "uuid": uuid,
        "token": token,
        "sign": sign,
        "sec-ch-ua-platform": "\"Windows\"",
        "Origin": "https://beian.miit.gov.cn",
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://beian.miit.gov.cn/",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cookie": "__jsluid_s=9d110373f211f3aa6b5c11c0ce0f23ea"
    }
    data = '{"pageNum":"","pageSize":"","unitName":"'+ domain +'","serviceType":1}'

    requests.packages.urllib3.disable_warnings()
    response = get_icp_respons(domain, headers, data)
    if "过期" in response.text:
        token_get()
        with open('token.txt', 'r') as file:
            lines = file.readlines()
            sign = lines[0].strip() 
            token = lines[1].strip() 
            uuid = lines[2].strip()
        headers["token"] = token
        headers["uuid"] = uuid
        headers["sign"] = sign
        response = get_icp_respons(domain, headers, data)

    pattern = r'"unitName":"(.*?)"'
    match = re.search(pattern, response.text)
    if match:
        icp_result = match.group(1)
        return icp_result
    else:
        return "没有备案信息"


# 获取token令牌
def token_get():
    cmd = ["start", "cmd", "/k", "mitmdump", "-s", "request_capture.py","-p","18181"]
    os.system(" ".join(cmd))
    proxy = "127.0.0.1:18181"
    
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36"
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(f"user-agent={user_agent}")
    chrome_options.headless = False
    chrome_options.add_argument(f"--proxy-server=http://{proxy}")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--allow-running-insecure-content")
    chromedriver_path = ".\\chromedriver.exe"
    while True:
        try:
            service = Service(chromedriver_path)
            service.start()
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.get("https://beian.miit.gov.cn/#/Integrated/recordQuery")
            time.sleep(random.uniform(2, 5))
            input_element = driver.find_element(By.XPATH, '//*[@id="app"]/div/header/div[3]/div/div[1]/input')
            input_element.send_keys("baidu.com")
            input("请在验证成功后输入回车继续")
            break
        except Exception as e:
            print("Error:", e)
            time.sleep(60)


# 爱站查询权重
def get_aizhan_rank(domaindj):
    pcrank = "0"
    prrank = "0"
    url1 = f"https://rank.aizhan.com/{domaindj}/"
    url2 = f"https://pr.aizhan.com/{domaindj}/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    try:
        response1 = requests.get(url1, headers=headers, timeout=10)
        if response1.status_code == 200:
            pattern = r'id="br_pc_br"><img src="//statics\.aizhan\.com/images/br/(\d+)\.png"'
            result1 = re.search(pattern, response1.text)
            if result1:
                pcrank = result1.group(1)

        response2 = requests.get(url2, headers=headers, timeout=10)
        if response2.status_code == 200:
            pattern = r'<img src="//statics.aizhan.com/images/pr/(\d+).png"'
            result2 = re.search(pattern, response2.text)
            if result2:
                prrank = result2.group(1)
    except:
        print("爱站请求失败，请检查网络")
    return pcrank, prrank
    
# 主函数异步运行
async def main_async(file_path):
    domains = {}
    df = pd.DataFrame(columns=['IP地址', '域名', '备案信息', '百度权重', '谷歌权重'])
    listdomain = read_file(file_path)
    
    stop_flag = False
    tasks = [] 
    for domain in listdomain:
        iplist, dmlist = ipdomain(domain)
        if not stop_flag:
            for ip in iplist:
                fofa_base64 = base64_encode(ip)
                tasks.append(fofa_async(fofa_base64, ip))

    results = await asyncio.gather(*tasks)

    for result in results:
        if result == "stop":
            stop_flag = True
            print("检测到资源访问每天限制，停止所有FOFA函数，进入下一阶段")
            break

        extracted_domains, ip = result
        if ip in domains:
            domains[ip].extend(extracted_domains)
        else:
            domains[ip] = extracted_domains

    for dm in dmlist:
        domains.setdefault(' ', []).append(dm)

    token_get()
    processed_domains = set()
    processed_domains2 = set()
    print("开始查询备案信息和域名权重")
    for ip, domain_list in domains.items():
        for domain in domain_list:
            domaindj = extract_domain(domain)
            if domaindj not in processed_domains:
                beian = icp(domaindj)
                processed_domains.add(domaindj)
                print(f"\n{domaindj} {beian}")
            else:
                beian = "该子域名备案同主域名"
            pc_rank = ' '
            pr_rank = ' '
            if domain not in processed_domains2:
                pcrank, prrank = get_aizhan_rank(domaindj)
                processed_domains2.add(domain)
                pc_rank = pcrank
                pr_rank = prrank
                print(f"{domain} - 百度权重: {pc_rank} 谷歌权重: {pr_rank}")
                df = pd.concat([df, pd.DataFrame({'IP地址': [ip], '域名': [domain], '备案信息': [beian], '百度权重': [pc_rank], '谷歌权重': [pr_rank]})], ignore_index=True)

    df.to_excel('domain_icp_info.xlsx', index=False)

def version_update():
    repo_url = "https://api.github.com/repos/honmashironeko/icpscan"
    if os.path.exists("last_update_time.txt"):
        with open("last_update_time.txt", "r") as file:
            last_update_str = file.read().strip()
    else:
        last_update_str = "2024-03-18 00:00:00"
        with open("last_update_time.txt", "w") as file:
            file.write(last_update_str)

    response = requests.get(repo_url)
    
    if response.status_code == 200:
        repo_data = response.json()
        latest_update_time = repo_data['updated_at'][:19]

        if latest_update_time > last_update_str:
            print("项目有更新，请前往下载！"+"https://github.com/honmashironeko/icpscan")
            print(f"上次更新时间：{last_update_str}")
            print(f"最新更新时间：{latest_update_time}")

            # 保存最新更新时间到文件
            with open("last_update_time.txt", "w") as file:
                file.write(latest_update_time)      
    else:
        print("无法访问该项目")


def print_icpscan_banner():
    print("=" * 70)
    print("""
 __     ______     ______   ______     ______     ______     __   __    
/\ \   /\  ___\   /\  == \ /\  ___\   /\  ___\   /\  __ \   /\ "-.\ \   
\ \ \  \ \ \____  \ \  _-/ \ \___  \  \ \ \____  \ \  __ \  \ \ \-.  \  
 \ \_\  \ \_____\  \ \_\    \/\_____\  \ \_____\  \ \_\ \_\  \ \_\\"\_\ 
  \/_/   \/_____/   \/_/     \/_____/   \/_____/   \/_/\/_/   \/_/ \/_/ 
""")
    print("\t\t\t\t\t\t\tVersion:1.1")
    print("\t\t\t\t\t关注微信公众号:樱花庄的本间白猫")
    print("=" * 70)
    print("\t\tIcpScan开始执行")
if __name__ == "__main__":
    version_update()
    print_icpscan_banner()
    parser = argparse.ArgumentParser(description='ICPScan由本间白猫开发,旨在快速反查IP、域名归属')
    parser.add_argument('-f', dest='file_path', required=True, help='指定使用的路径文件 -f url.txt')
    args = parser.parse_args()
    file_path = args.file_path
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(main_async(file_path))
    loop.run_until_complete(future)