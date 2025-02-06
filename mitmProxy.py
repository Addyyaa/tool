import sys

from mitmproxy import http


def request(flow: http.HTTPFlow) -> None:
    # 检查请求URL是否包含特定字符串
    print(flow.request.headers.get("X-TOKEN"))


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        request(sys.argv[1])
