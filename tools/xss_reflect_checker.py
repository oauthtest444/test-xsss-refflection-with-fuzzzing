#!/usr/bin/env python3
import sys
import argparse
import re
import time
import urllib.request
import urllib.parse
import urllib.error
import json
from urllib.parse import urlparse, urlunparse

# ================== CONFIG ==================
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
REQUEST_DELAY = 1.3   # Balanced for speed + WAF safety

XSS_CONTENT_TYPES = {
    'text/html', 'image/svg+xml', 'text/xml',
    'application/xml', 'application/xhtml+xml'
}

WEBHOOK_URL = "https://discord.com/api/webhooks/1508123239732350987/Q-oc7dcydk07KJwnsAJSbTpaVeNxHR6HnVkkpf5Q8kkJqMfQYpbu9ZGEaHx80IKm1oZw"

def is_executable_content_type(content_type):
    if not content_type:
        return True
    ct = content_type.lower().split(';')[0].strip()
    return ct in XSS_CONTENT_TYPES

def build_url(base_url, params_str):
    if not params_str.startswith('?'):
        params_str = '?' + params_str.lstrip('?')
    return base_url.rstrip('/') + params_str

def url_encode_value(value):
    return urllib.parse.quote(value, safe='')

def send_to_webhook(vuln_url, base_url):
    try:
        message = {
            "content": f"**🔥 XSS Reflection Found!**",
            "embeds": [{
                "title": "Vulnerable URL",
                "description": f"**Path:** {base_url}\n**Full URL:** [Vulnerable Link]({vuln_url})",
                "color": 0x00ff00,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }]
        }

        data = json.dumps(message).encode('utf-8')
        req = urllib.request.Request(
            WEBHOOK_URL,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': USER_AGENT
            },
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=10):
            pass
    except:
        pass  # Silent fail if webhook fails

def fetch_url(url):
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': USER_AGENT}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            content_type = response.getheader('Content-Type', '')
            status = response.getcode()
            body = response.read().decode('utf-8', errors='ignore')
            return body, content_type, status
    except urllib.error.HTTPError as e:
        return None, e.getheader('Content-Type', ''), e.code
    except Exception:
        return None, '', 0

def main():
    parser = argparse.ArgumentParser(description="XSS Reflection Checker + Discord Webhook")
    parser.add_argument('-l', '--list', default='usefull-path-urls.txt',
                        help='Path list file (default: usefull-path-urls.txt)')
    parser.add_argument('-p', '--params', default='fuzz-params-list.txt',
                        help='Fuzz parameters list file')
    parser.add_argument('-pv', '--payload-value', default='testtt<a>t"\'est',
                        help='XSS Payload')
    parser.add_argument('-o', '--output', default='vulnerable.txt',
                        help='Output file for vulnerable URLs')
    parser.add_argument('-d', '--delay', type=float, default=REQUEST_DELAY,
                        help='Delay between requests (seconds)')
    parser.add_argument('--webhook', action='store_true', help='Enable Discord webhook (enabled by default)')
    args = parser.parse_args()

    payload = args.payload_value
    delay = args.delay

    print(f"[+] XSS Reflection Checker + Webhook Started")
    print(f"    Payload : {payload}")
    print(f"    Delay   : {delay}s")
    print(f"    Output  : {args.output}\n")

    # Load files
    try:
        with open(args.list, 'r', encoding='utf-8', errors='ignore') as f:
            paths = [line.strip() for line in f if line.strip().startswith(('http://', 'https://'))]
    except FileNotFoundError:
        print(f"❌ {args.list} not found!")
        sys.exit(1)

    try:
        with open(args.params, 'r', encoding='utf-8', errors='ignore') as f:
            param_chunks = [line.strip() for line in f if line.strip() and line.startswith('?')]
    except FileNotFoundError:
        print(f"❌ {args.params} not found!")
        sys.exit(1)

    vulnerable = []
    total_checked = 0

    for i, base_url in enumerate(paths, 1):
        print(f"[{i}/{len(paths)}] Checking → {base_url}")

        # First check content-type with clean request
        body, content_type, status = fetch_url(base_url)

        if not is_executable_content_type(content_type):
            print(f"    ⏭️ Skipped (Content-Type: {content_type})")
            time.sleep(delay)
            continue

        print(f"    ✅ Good Content-Type → Testing parameters...")

        for chunk in param_chunks:
            modified_chunk = re.sub(r'=[^&]+', f'={url_encode_value(payload)}', chunk)
            test_url = build_url(base_url, modified_chunk)

            total_checked += 1
            print(f"    → Testing chunk...")

            body, content_type, status = fetch_url(test_url)

            if body and is_executable_content_type(content_type) and payload in body:
                print(f"    🎯 VULNERABLE: {test_url}")
                vulnerable.append(test_url)
                send_to_webhook(test_url, base_url)   # Send to Discord

            time.sleep(delay)

    # Save results
    with open(args.output, 'w', encoding='utf-8') as f:
        for url in vulnerable:
            f.write(url + '\n')

    print(f"\n🎉 Scan Finished!")
    print(f"   Paths checked       : {len(paths)}")
    print(f"   Parameter requests  : {total_checked}")
    print(f"   Vulnerabilities     : {len(vulnerable)}")
    print(f"   Saved in            : {args.output}")

if __name__ == "__main__":
    main()
