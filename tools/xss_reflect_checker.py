#!/usr/bin/env python3
import sys
import argparse
import re
import time
import urllib.request
import urllib.parse
import json

# ================== CONFIG ==================
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
REQUEST_DELAY = 1.4

XSS_CONTENT_TYPES = {'text/html', 'image/svg+xml', 'text/xml', 'application/xml', 'application/xhtml+xml'}

WEBHOOK_URL = "https://discord.com/api/webhooks/1519586108826980383/VWGSRj_pCfaE0tQcOsXpg4JbDZsZW-mj25aD0SjIxjQMkKQmPZDcmn9hOGRN-YTbyGnM"

KEY_REGEX = re.compile(r'["\']?([a-zA-Z0-9_$]+)["\']?\s*:\s*[^,}]+', re.IGNORECASE)
OBJECT_REGEX = re.compile(r'(?:window|data|context|config|payload|params|vars)\s*[=:]\s*\{[\s\S]*?\}', re.IGNORECASE)

def is_executable_content_type(content_type):
    if not content_type:
        return True
    ct = content_type.lower().split(';')[0].strip()
    return ct in XSS_CONTENT_TYPES

def url_encode_value(value):
    return urllib.parse.quote(value, safe='')

def send_to_webhook(vuln_url, base_url):
    try:
        message = {
            "content": "**🔥 Reflected XSS Found!**",
            "embeds": [{
                "title": "Vulnerable URL",
                "description": f"**Path:** {base_url}\n**Full URL:** [Vulnerable Link]({vuln_url})",
                "color": 0x00ff00
            }]
        }
        data = json.dumps(message).encode('utf-8')
        req = urllib.request.Request(WEBHOOK_URL, data=data,
                                     headers={'Content-Type': 'application/json', 'User-Agent': USER_AGENT},
                                     method='POST')
        urllib.request.urlopen(req, timeout=10)
    except:
        pass

def fetch_url(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode('utf-8', errors='ignore'), resp.getheader('Content-Type', ''), resp.getcode()
    except urllib.error.HTTPError as e:
        return None, e.getheader('Content-Type', ''), e.code
    except Exception:
        return None, '', 0

def extract_json_params(html):
    params = set()
    # Extract from objects
    for match in OBJECT_REGEX.finditer(html):
        for key in KEY_REGEX.findall(match.group(0)):
            if key:
                params.add(key)
    # Extract anywhere in HTML
    for key in KEY_REGEX.findall(html):
        if key:
            params.add(key)
    return params

def main():
    parser = argparse.ArgumentParser(description="Advanced XSS Reflection Checker")
    parser.add_argument('-l', '--list', default='usefull-path-urls.txt', help='Path list')
    parser.add_argument('-p', '--params', default='fuzz-params-list.txt', help='Fuzz params list')
    parser.add_argument('-pv', '--payload-value', default='testtt<a>t"\'est', help='Payload')
    parser.add_argument('-o', '--output', default='vulnerable.txt', help='Output file')
    parser.add_argument('-d', '--delay', type=float, default=1.4, help='Delay')
    args = parser.parse_args()

    payload = args.payload_value
    delay = args.delay

    print(f"[+] Advanced XSS Reflection Checker Started | Payload: {payload}")

    # Load paths and param chunks
    with open(args.list, 'r', encoding='utf-8', errors='ignore') as f:
        paths = [line.strip() for line in f if line.strip().startswith(('http://', 'https://'))]

    with open(args.params, 'r', encoding='utf-8', errors='ignore') as f:
        param_chunks = [line.strip() for line in f if line.strip().startswith('?')]

    vulnerable = []

    for base_url in paths:
        print(f"\n[+] Testing path: {base_url}")

        # Initial content-type check
        _, content_type, _ = fetch_url(base_url)
        if not is_executable_content_type(content_type):
            print(f"    ⏭️ Skipped (Content-Type: {content_type})")
            time.sleep(delay)
            continue

        print(f"    ✅ Good Content-Type → Starting Fuzzing...")

        # 1. Fuzz with pre-existing chunks from fuzz-params-list.txt
        for chunk in param_chunks:
            modified = re.sub(r'=[^&]+', f'={url_encode_value(payload)}', chunk)
            test_url = base_url.rstrip('/') + modified
            body, ct, _ = fetch_url(test_url)

            if body and is_executable_content_type(ct) and payload in body:
                print(f"    🎯 VULNERABLE: {test_url}")
                vulnerable.append(test_url)
                send_to_webhook(test_url, base_url)
            time.sleep(delay)

        # 2. Extract JSON parameters from full HTML
        body, ct, _ = fetch_url(base_url)
        if not body or not is_executable_content_type(ct):
            continue

        json_keys = extract_json_params(body)
        if not json_keys:
            continue

        print(f"    🔍 Found {len(json_keys)} JSON parameters → Testing...")

        # === First: Test with ORIGINAL casing ===
        all_keys = sorted(json_keys)
        for i in range(0, len(all_keys), 50):
            chunk_keys = all_keys[i:i+50]
            chunk_str = '?' + '&'.join(f"{k}={url_encode_value(payload)}" for k in chunk_keys)
            test_url = base_url.rstrip('/') + chunk_str

            body2, ct2, _ = fetch_url(test_url)
            if body2 and is_executable_content_type(ct2) and payload in body2:
                print(f"    🎯 VULNERABLE (Original Case): {test_url}")
                vulnerable.append(test_url)
                send_to_webhook(test_url, base_url)
            time.sleep(delay)

        # === Second: Test ONLY Capital-starting parameters in lowercase ===
        capital_keys = [k for k in json_keys if k and k[0].isupper()]
        lower_keys = [k.lower() for k in capital_keys]
        lower_keys = sorted(set(lower_keys))  # remove duplicates

        if lower_keys:
            print(f"    🔄 Testing {len(lower_keys)} lowercase capital params...")
            for i in range(0, len(lower_keys), 50):
                chunk_keys = lower_keys[i:i+50]
                chunk_str = '?' + '&'.join(f"{k}={url_encode_value(payload)}" for k in chunk_keys)
                test_url = base_url.rstrip('/') + chunk_str

                body3, ct3, _ = fetch_url(test_url)
                if body3 and is_executable_content_type(ct3) and payload in body3:
                    print(f"    🎯 VULNERABLE (Lowercase Capital): {test_url}")
                    vulnerable.append(test_url)
                    send_to_webhook(test_url, base_url)
                time.sleep(delay)

    # Save results
    with open(args.output, 'w', encoding='utf-8') as f:
        for url in vulnerable:
            f.write(url + '\n')

    print(f"\n🎉 Scan Finished! Found {len(vulnerable)} vulnerable URLs")

if __name__ == "__main__":
    main()
