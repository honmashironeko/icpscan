from mitmproxy import http
import json
import sys

def response(flow: http.HTTPFlow) -> None:
    if "hlwicpfwc.miit.gov.cn" in flow.request.pretty_url and "/icpproject_query/api/icpAbbreviateInfo/queryByCondition" in flow.request.path:
        try:
            request_headers = flow.request.headers
            token_value = request_headers.get("token")
            uuid_value = request_headers.get("uuid")
            sign_value = request_headers.get("sign")

            if sign_value and token_value and uuid_value:
                with open("token.txt", "w") as file:
                    file.write(f"{sign_value}\n")
                    file.write(f"{token_value}\n")
                    file.write(f"{uuid_value}")
                print("已写入值到 token.txt 文件")
                sys.exit(0)
            else:
                print("在请求头或响应中未找到签名、令牌或 UUID 值")
        except (json.JSONDecodeError, KeyError) as e:
            print("解析 JSON 或获取值时出现错误:", e)
