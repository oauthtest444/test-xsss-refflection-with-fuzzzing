#!/usr/bin/env python3
import sys
import argparse
import re
import time
import urllib.request
import urllib.error
from urllib.parse import urlparse, parse_qsl, urlunparse
from collections import OrderedDict

# ================== CONFIG ==================
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
REQUEST_DELAY = 1.5

# Whitelist extensions
EXT_WHITELIST = {
    'html', 'htm', 'shtml', 'shtm', 'xhtml', 'xht',
    'php', 'asp', 'aspx', 'jsp', 'jspx', 'cfm', 'cfml',
    'py', 'pl', 'rb', 'do', 'action', 'dll'
}

# Regex for extracting keys
KEY_REGEX = re.compile(r'["\']?([a-zA-Z0-9_$]+)["\']?\s*:\s*[^,}]+', re.IGNORECASE)
OBJECT_REGEX = re.compile(r'(?:window|data|context|config|payload|params|vars)\s*[=:]\s*\{[\s\S]*?\}', re.IGNORECASE)

def is_valid_url(url):
    return url.startswith(('http://', 'https://'))

def clean_path(url):
    parsed = urlparse(url)
    path = parsed.path or '/'
    if url.endswith('/') and not path.endswith('/'):
        path += '/'
    return urlunparse((parsed.scheme, parsed.netloc, path, '', '', ''))

def fetch_url(url):
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': USER_AGENT}
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            if response.getcode() >= 400:
                return None
            return response.read().decode('utf-8', errors='ignore')
    except Exception:
        return None

def main():
    parser = argparse.ArgumentParser(description="Advanced Path & Parameter Extractor")
    parser.add_argument('-l', '--list', required=True, help='Input URLs list file')
    parser.add_argument('-pv', '--param-value', default='testtt', help='Value for parameters (default: testtt)')
    parser.add_argument('-cp', '--custom-params', help='Custom parameters file (optional)')
    args = parser.parse_args()

    pv = args.param_value
    input_file = args.list

    print("[+] Starting extraction...")

    # STEP 1: Extract params and paths
    all_params = []
    seen_params = set()
    paths = OrderedDict()

    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            url = line.strip()
            if not is_valid_url(url) or '?' not in url:
                continue

            parsed = urlparse(url)
            params = parse_qsl(parsed.query, keep_blank_values=True)
            clean_url = clean_path(url)

            if clean_url not in paths:
                paths[clean_url] = True

            for key, _ in params:
                if key and key not in seen_params:
                    seen_params.add(key)
                    all_params.append(key)

    # Write all-params.txt
    with open('all-params.txt', 'w', encoding='utf-8') as f:
        if all_params:
            f.write('?' + '&'.join(f"{k}={pv}" for k in all_params) + '\n')

    # Write merged unique params
    with open('all-marge-uniq-params.txt', 'w', encoding='utf-8') as f:
        if all_params:
            f.write('?' + '&'.join(f"{k}={pv}" for k in all_params) + '\n')

    # Write all paths
    with open('all-paths.txt', 'w', encoding='utf-8') as f:
        for p in paths.keys():
            f.write(p + '\n')

    # Filter useful paths
    useful_paths = []
    for url in paths.keys():
        parsed = urlparse(url)
        ext = parsed.path.split('.')[-1].lower() if '.' in parsed.path else ''
        if not ext or ext in EXT_WHITELIST:
            useful_paths.append(url)

    with open('usefull-path-urls.txt', 'w', encoding='utf-8') as f:
        for p in useful_paths:
            f.write(p + '\n')

    print(f"    Extracted {len(all_params)} unique params")
    print(f"    Saved {len(useful_paths)} useful paths")

    # STEP 4: Fetch pages and extract parameters from body
    body_params = set()
    print("[+] Fetching pages and extracting parameters from body...")

    for i, url in enumerate(useful_paths, 1):
        print(f"    [{i}/{len(useful_paths)}] Fetching → {url}")
        content = fetch_url(url)

        if content:
            # Extract keys
            for key in KEY_REGEX.findall(content):
                if key:
                    body_params.add(key)

            for match in OBJECT_REGEX.finditer(content):
                for key in KEY_REGEX.findall(match.group(0)):
                    if key:
                        body_params.add(key)

        time.sleep(REQUEST_DELAY)

    with open('all-parameter-from-body.txt', 'w', encoding='utf-8') as f:
        if body_params:
            f.write('?' + '&'.join(f"{k}={pv}" for k in sorted(body_params)) + '\n')

    # STEP 5: Merge everything
    total_params = set(all_params) | body_params

    if args.custom_params:
        try:
            with open(args.custom_params, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        key = line.split('=')[0].strip()
                        if key:
                            total_params.add(key)
        except:
            pass

    with open('total-uniq-params.txt', 'w', encoding='utf-8') as f:
        if total_params:
            f.write('?' + '&'.join(f"{k}={pv}" for k in sorted(total_params)) + '\n')

    # STEP 6: Create fuzz list (50 params per line)
    param_list = sorted(total_params)
    with open('fuzz-params-list.txt', 'w', encoding='utf-8') as f:
        for i in range(0, len(param_list), 50):
            chunk = param_list[i:i+50]
            if chunk:
                f.write('?' + '&'.join(f"{k}={pv}" for k in chunk) + '\n')

    print(f"\n🎉 Done! Total unique parameters: {len(total_params)}")
    print("Generated files:")
    print("   • all-params.txt")
    print("   • all-marge-uniq-params.txt")
    print("   • all-paths.txt")
    print("   • usefull-path-urls.txt")
    print("   • all-parameter-from-body.txt")
    print("   • total-uniq-params.txt")
    print("   • fuzz-params-list.txt")
    
if __name__ == "__main__":
    main()
