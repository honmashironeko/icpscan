from urllib.parse import urlparse
import pandas as pd
import tldextract
import argparse
import requests
import urllib3
import asyncio
import aiohttp
import base64
import re

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
async def fofa_async(b64, ip, proxyip, retry_count=3):
    async with sem:
        url = f"https://fofa.info/result?qbase64={b64}"
        for _ in range(retry_count):
            try:
                if proxyip:
                    proxies = f"http://{proxyip}"
                else:
                    proxies = None
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=HEADERSF, timeout=10, verify_ssl=False, proxy=proxies) as response:
                        if response.status == 200:
                            text = await response.text()
                            if "资源访问每天限制" in text:
                                print("当前IP已达到查询上限，请更换IP或使用Zoomeye")
                                break
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
    
# Zoomeye异步查询
async def zoomeye_async(ip,auth, retry_count=3):
    async with sem:
        url = f"https://api.zoomeye.org/web/search?query=ip%3A%22{ip}%22&page=1"
        for _ in range(retry_count):
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {
                        "API-KEY": auth
                    }
                    async with session.get(url, headers=headers, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            results = re.findall(r"'site': '(.*?)'", str(data))
                            print(f"ZoomEye查询完毕 IP: {ip}")
                            return results, ip
                        else:
                            print(f"ZoomEye请求失败！错误码: {response.status} - {ip}")
            except aiohttp.ClientError as e:
                print(f"ZoomEye请求失败: {e} - {ip}")

        print(f"多次尝试后无法成功获取结果 - {ip}")
        return [], ip

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

# 查询备案
def icp(domain,proxyip):
    url = "https://api.uutool.cn/beian/icp/"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    data = "domain=" + domain
    session = requests.Session()
    proxies = None
    if proxyip:
        proxies = {
            "http": f"http://{proxyip}",
            "https": f"http://{proxyip}"
        }
        session.proxies.update(proxies)
    response = session.post(url, headers=headers, proxies=proxies, data=data)
    if response.status_code == 200:
        match = response.json()
        if "icp_org" in match:
            icp_result = match['data']['icp_org']
            return icp_result
        if "请求频次过高" in match['error']:
            return "本机IP已超出请求上限，请更换新的IP"
        else:
            return "没有备案信息"
    else:
        print("请求备案站点失败，请检查网络环境")

# 备案查询模块
def beian_scan(domains, df, proxyip):
    processed_domains = set()
    for ip, domain_list in domains.items():
        for domain in domain_list:
            domaindj = extract_domain(domain)
            if domaindj not in processed_domains:
                beian = icp(domaindj,proxyip)
                processed_domains.add(domaindj)
                print(f"{domaindj} {beian}\n")
            else:
                beian = "该子域名备案同主域名"
            pc_rank = ' '
            pr_rank = ' '
            df = pd.concat([df, pd.DataFrame({'IP地址': [ip], '域名': [domain], '备案信息': [beian], '百度权重': [pc_rank], '谷歌权重': [pr_rank]})], ignore_index=True)
    return df
        
# 备案和权重查询模块
def beian_and_rank_scan(domains,df,proxyip):
    processed_domains = set()
    processed_domains2 = set()
    for ip, domain_list in domains.items():
        for domain in domain_list:
            domaindj = extract_domain(domain)
            if domaindj not in processed_domains:
                beian = icp(domaindj,proxyip)
                processed_domains.add(domaindj)
                print(f"{domaindj} {beian}")
            else:
                beian = "该子域名备案同主域名"
            pc_rank = ' '
            pr_rank = ' '
            if domain not in processed_domains2:
                pcrank, prrank = get_aizhan_rank(domaindj)
                processed_domains2.add(domain)
                pc_rank = pcrank
                pr_rank = prrank
                print(f"{domain} - 百度权重: {pc_rank} 谷歌权重: {pr_rank}\n")
                df = pd.concat([df, pd.DataFrame({'IP地址': [ip], '域名': [domain], '备案信息': [beian], '百度权重': [pc_rank], '谷歌权重': [pr_rank]})], ignore_index=True)
    return df
# 主函数异步运行
async def main_async(file_path,zoomeye_auth,proxyip):
    domains = {}
    df = pd.DataFrame(columns=['IP地址', '域名', '备案信息', '百度权重', '谷歌权重'])
    listdomain = read_file(file_path)
    
    tasks = [] 
    for domain in listdomain:
        iplist, dmlist = ipdomain(domain)
        for dm in dmlist:
            domains.setdefault(' ', []).append(dm)
        for ip in iplist:
            if zoomeye_auth:
                tasks.append(zoomeye_async(ip,zoomeye_auth))
            else:
                fofa_base64 = base64_encode(ip)
                tasks.append(fofa_async(fofa_base64, ip, proxyip))

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

    if qz_auth:
        print("\n开始查询备案信息和域名权重\n")
        df = beian_and_rank_scan(domains,df,proxyip)
    else:
        print("\n开始查询备案信息\n")
        df = beian_scan(domains,df,proxyip)
    df.to_excel('domain_icp_info.xlsx', index=False)

def update_module():
    icpscan_time = "2024-04-20"
    url = "https://y.shironekosan.cn/1.html"
    response = requests.get(url)
    pattern = r'<div\s+class="nc-light-gallery"\s+id="image_container">(.*?)</div>'
    matches = re.search(pattern, response.text, re.DOTALL)
    content_array = []
    
    if matches:
        inner_content = matches.group(1)
        p_matches = re.findall(r'<p>(.*?)</p>', inner_content)
        content_array.extend(p_matches)
    if icpscan_time == content_array[3]:
        pass
    else:
        text1 = """
        Icpscan存在最新更新，请前往以下任意地址获取更新：
        https://pan.quark.cn/s/39b4b5674570/
        https://github.com/honmashironeko/icpscan/
        https://pan.baidu.com/s/1C9LVC9aiaQeYFSj_2mWH1w?pwd=13r5/
        """
        print(text1)
        input("请输入回车键继续运行工具")

def print_icpscan_banner():
    print("=" * 70)
    print("""
 __     ______     ______   ______     ______     ______     __   __    
/\ \   /\  ___\   /\  == \ /\  ___\   /\  ___\   /\  __ \   /\ "-.\ \   
\ \ \  \ \ \____  \ \  _-/ \ \___  \  \ \ \____  \ \  __ \  \ \ \-.  \  
 \ \_\  \ \_____\  \ \_\    \/\_____\  \ \_____\  \ \_\ \_\  \ \_\\"\_\ 
  \/_/   \/_____/   \/_/     \/_____/   \/_____/   \/_/\/_/   \/_/ \/_/ 
""")
    print("\t\t\t\t\t\t\tVersion:2.1")
    print("\t\t\t\t\t微信公众号:樱花庄的本间白猫")
    print("\t\t\t\t博客地址：https://y.shironekosan.cn")
    print("=" * 70)
    print("\t\tIcpScan开始执行")

if __name__ == "__main__":
    update_module()
    print_icpscan_banner()
    parser = argparse.ArgumentParser(description='ICPScan由本间白猫开发,旨在快速反查IP、域名归属')
    parser.add_argument('-f', dest='file_path', required=True, help='指定使用的路径文件 -f url.txt')
    parser.add_argument('-qz', dest='qz_auth', action='store_true', help='增加权重查询 -qz')
    parser.add_argument('-key', dest='zoomeye_auth', help='指定ZoomEye的API-KEY认证信息 -key API-KEY')
    parser.add_argument('-p', dest='proxyip', help='指定代理地址 -p 127.0.0.1:8080 或者 -p user:pass@127.0.0.1:8080')
    args = parser.parse_args()
    file_path = args.file_path
    qz_auth = args.qz_auth
    zoomeye_auth = args.zoomeye_auth
    proxyip = args.proxyip
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(main_async(file_path,zoomeye_auth,proxyip))
    loop.run_until_complete(future)