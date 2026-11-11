import json
import urllib.error
import urllib.parse
import urllib.request

__all__ = ['fetch', 'fetch_json', 'post_json']

default_timeout = 10
default_headers = {
    'User-Agent': 'TanexScript-web_fetch/1.0',
    'Accept': '*/*'
}

def _check_url(url):
    if not isinstance(url, str) or not url:
        raise TypeError('url 必须是非空字符串')
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ('http', 'https'):
        raise ValueError('只支持 http/https 地址: ' + url)
    if not parts.netloc:
        raise ValueError('地址缺少主机: ' + url)

def _build_headers(extra):
    result = dict(default_headers)
    if not extra:
        return result
    for key, value in extra.items():
        result[str(key)] = str(value)
    return result

def _encode_body(body):
    if isinstance(body, str):
        return body.encode('utf-8')
    if isinstance(body, (bytes, bytearray)):
        return bytes(body)
    if isinstance(body, (dict, list)):
        return json.dumps(body, ensure_ascii = False).encode('utf-8')
    raise TypeError('body 只能是字符串、bytes、list 或 dictionary')

def _request(url, method, body, headers, timeout):
    _check_url(url)
    data = None
    final_headers = _build_headers(headers)
    if body is not None:
        data = _encode_body(body)
        if isinstance(body, (dict, list)):
            final_headers['Content-Type'] = 'application/json; charset=utf-8'
    request = urllib.request.Request(
        url,
        data = data,
        headers = final_headers,
        method = method
    )
    try:
        with urllib.request.urlopen(request, timeout = timeout) as response:
            charset = response.headers.get_content_charset() or 'utf-8'
            return response.read().decode(charset, errors = 'replace')
    except urllib.error.HTTPError as e:
        detail = e.read().decode('utf-8', errors = 'replace')
        raise RuntimeError(
            'HTTP 请求失败: ' + str(e.code) + ' ' + str(e.reason) + ': ' + detail
        )
    except urllib.error.URLError as e:
        raise RuntimeError('网络请求失败: ' + str(e.reason))
    except TimeoutError:
        raise RuntimeError('网络请求超时: ' + url)

def fetch(url, timeout = default_timeout, headers = None):
    return _request(url, 'GET', None, headers, timeout)

def fetch_json(url, timeout = default_timeout, headers = None):
    return json.loads(fetch(url, timeout, headers))

def post_json(url, payload, timeout = default_timeout, headers = None):
    text = _request(url, 'POST', payload, headers, timeout)
    if not text:
        return None
    return json.loads(text)
