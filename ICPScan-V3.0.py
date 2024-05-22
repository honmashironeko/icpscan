from urllib3.exceptions import InsecureRequestWarning
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from collections import deque
import concurrent.futures
import pandas as pd
import tldextract
import argparse
import requests
import logging
import aiohttp
import base64
import time
import ssl
import re

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 提取一级域名
def extract_domain(domain):
    return tldextract.extract(domain).registered_domain

def detect_ip_domain(text):
    if not isinstance(text, str):
        raise ValueError("输入必须是字符串类型")
    ip_pattern = r'\b(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
    domain_pattern = r'(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}'
    patterns = (ip_pattern, domain_pattern)
    results = [re.findall(pattern, text) for pattern in patterns]
    return results[0], results[1]

def read_file_line_by_line(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                yield line
    except FileNotFoundError:
        logging.error(f"文件 {file_path} 未找到。")
    except PermissionError:
        logging.error(f"没有权限读取文件 {file_path}。")

def read_file(file_path):
    try:
        return list(read_file_line_by_line(file_path))
    except FileNotFoundError:
        logging.error(f"文件 {file_path} 未找到。")
    except PermissionError:
        logging.error(f"没有权限读取文件 {file_path}。")
# FOFA计算base64
def base64_encode(ip):
    return base64.b64encode(f'is_domain=true && ip="{ip}"'.encode('utf-8')).decode('utf-8')

# FOFA-API查询
def fofa_api(b64,ip):
    url = f"https://fofa.info/api/v1/search/all?&key={key}&qbase64={b64}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = data.get('results')           
            domains = [item[0] for item in results]
            print(f"FOFA反查完毕 IP: {ip}")
            return domains, ip
        else:    
            logging.error(f"FOFA请求失败！错误码: {response.status_code} - {ip}")
    except requests.exceptions.RequestException as e:
        logging.error(f"FOFA请求失败: {e} - {ip}")
# Zoomeye查询
def zoomeye(ip, auth):
    url = f"https://api.zoomeye.org/web/search?query=ip%3A%22{ip}%22&page=1"
    headers = {"API-KEY": auth}
    for _ in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.text
                results = re.findall(r"'site': '(.*?)'", str(data))
                print(f"ZoomEye查询完毕 IP: {ip}")
                return results, ip
            else:
                print(f"ZoomEye请求失败！错误码: {response.status_code} - {ip}")
        except aiohttp.ClientError as e:
            print(f"ZoomEye请求失败: {e} - {ip}")
        except Exception as e:
            print(f"ZoomEye处理异常: {e} - {ip}")

def extract_beian_info(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    td_element = soup.select_one('td.align-middle a[href^="/company/"]')
    if td_element:
        company_name = td_element.get_text()
        return company_name
# 查询备案
def icp_beian(domain, proxyip=None):
    url = "https://www.beianx.cn/search/"+domain
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    proxies = {
        "http": f"socks5://{proxyip}",
        "https": f"socks5://{proxyip}",
    } if proxyip else None
    retry_times = 3
    backoff = 1
    for attempt in range(retry_times):
        try:
            response = requests.post(url, headers=headers, proxies=proxies, timeout=5)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"由于错误而重试: {domain}")
            time.sleep(backoff)
            backoff *= 2
            if attempt < retry_times - 1:
                continue
            else:
                return {"信息": "请求备案站点失败，请检查网络环境或域名"}
        else:
            break
    
    if response.status_code == 200:
        beian_info = extract_beian_info(response.text)
        if isinstance(beian_info, str):
            return beian_info
        else:
            return "Null"
    else:
        return {"信息": "请求备案站点失败，请检查网络环境"}
# 备案查询模块
def beian_query(domains):
    processed_domains = set()
    domains_jg = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5):
        for ip, domain_list in domains.items():
            for domain in domain_list:
                domaindj = extract_domain(domain)
                if domaindj not in processed_domains:
                    try:
                        beian = icp_beian(domaindj)
                        domains_jg[domaindj] = ip, beian
                        print(f"{domaindj}\t\t{beian}")
                    except Exception as e:
                        logging.error(f"备案查询过程中发生异常：{e}")
                    processed_domains.add(domaindj)
    return domains_jg

def main(file_path, zoomeye_auth):
    domains = {}
    df = pd.DataFrame(columns=['IP地址', '域名', '备案信息'])
    try:
        with open(file_path, 'r') as f:
            listdomain = f.read().splitlines()
    except FileNotFoundError as e:
        print(f"文件路径错误：{e}")
        return
    for domain in listdomain:
        iplist, dmlist = detect_ip_domain(domain)
        for dm in dmlist:
            domains.setdefault(' ', []).append(dm)
        for ip in iplist:
            if zoomeye_auth:
                results = (zoomeye(ip, zoomeye_auth))
                extracted_domains, ip = results
                if ip in domains:
                    domains[ip].extend(extracted_domains)
                else:
                    domains[ip] = extracted_domains
            else:
                fofa_base64 = base64_encode(ip)
                try:
                    extracted_domains, ip = fofa_api(fofa_base64,ip)
                    if ip in domains:
                        domains[ip].extend(extracted_domains)
                    else:
                        domains[ip] = extracted_domains
                except:
                    pass
    
    print("\n开始查询备案信息\n")
    domain_info = beian_query(domains)
    for domaindj, (ip, beian) in domain_info.items():
        df = pd.concat([df, pd.DataFrame({'IP地址': [ip], '域名': [domaindj], '备案信息': [beian]})], ignore_index=True)
    df.to_excel('domain_icp_info.xlsx', index=False)
        
def update_module():
    try:
        icpscan_time = "2024-05-06"
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
            ICPScan存在最新更新，请前往以下任意地址获取更新：
            https://pan.quark.cn/s/39b4b5674570#/list/share
            https://github.com/honmashironeko/icpscan/
            https://pan.baidu.com/s/1C9LVC9aiaQeYFSj_2mWH1w?pwd=13r5/
            """
            print(text1)
            input("请输入回车键继续运行工具")
    except Exception as e:
        print(f"更新模块运行过程中发生异常：{e}")
        print(f"""
            检查更新失败，请前往下载地址查看更新：
            https://pan.quark.cn/s/39b4b5674570#/list/share
            https://github.com/honmashironeko/icpscan/
            https://pan.baidu.com/s/1C9LVC9aiaQeYFSj_2mWH1w?pwd=13r5/
              """)
def print_icpscan_banner():
    print("=" * 70)
    print("""
 __     ______     ______   ______     ______     ______     __   __    
/\ \   /\  ___\   /\  == \ /\  ___\   /\  ___\   /\  __ \   /\ "-.\ \   
\ \ \  \ \ \____  \ \  _-/ \ \___  \  \ \ \____  \ \  __ \  \ \ \-.  \  
 \ \_\  \ \_____\  \ \_\    \/\_____\  \ \_____\  \ \_\ \_\  \ \_\\"\_\ 
  \/_/   \/_____/   \/_/     \/_____/   \/_____/   \/_/\/_/   \/_/ \/_/ 
""")
    print("\t\t\t\t\t\t\tVersion:3.0")
    print("\t\t\t\t\t微信公众号:樱花庄的本间白猫")
    print("\t\t\t\t博客地址：https://y.shironekosan.cn")
    print("=" * 70)
    print("\t\tICPScan开始执行")

if __name__ == "__main__":
    update_module()
    print_icpscan_banner()
    parser = argparse.ArgumentParser(description='ICPScan由本间白猫开发,旨在快速反查IP、域名归属')
    parser.add_argument('-f', dest='file_path', required=True, help='指定使用的路径文件 -f url.txt')
    parser.add_argument('-key', dest='fofa_key',required=True, help='指定FOFA的API-KEY认证信息 -key API-KEY')
    parser.add_argument('-zkey', dest='zoomeye_auth', help='指定ZoomEye的API-KEY认证信息 -zkey API-KEY')
    args = parser.parse_args()
    file_path = args.file_path
    zoomeye_auth = args.zoomeye_auth
    global key
    key = args.fofa_key
    main(file_path, zoomeye_auth)