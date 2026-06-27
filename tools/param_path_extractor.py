#!/usr/bin/env python3
import sys
import argparse
import re
from urllib.parse import urlparse, parse_qsl, urlunparse
from collections import OrderedDict

def is_valid_url(url):
    return url.startswith(('http://', 'https://'))

def clean_path(url):
    parsed = urlparse(url)
    path = parsed.path or '/'
    if url.endswith('/') and not path.endswith('/'):
        path += '/'
    return urlunparse((parsed.scheme, parsed.netloc, path, '', '', ''))

def main():
    parser = argparse.ArgumentParser(description="Path & Parameter Extractor")
    parser.add_argument('-l', '--list', required=True, help='Input URLs list file')
    parser.add_argument('-pv', '--param-value', default='testtt', help='Value for parameters (default: testtt)')
    parser.add_argument('-cp', '--custom-params', help='Custom parameters file (optional)')
    args = parser.parse_args()

    pv = args.param_value
    input_file = args.list

    print("[+] Starting extraction...")

    # STEP 1: Extract params and ALL paths (even without query)
    all_params = []
    seen_params = set()
    paths = OrderedDict()

    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            url = line.strip()
            if not is_valid_url(url):
                continue

            parsed = urlparse(url)
            clean_url = clean_path(url)

            if clean_url not in paths:
                paths[clean_url] = True

            # Extract parameters if present
            if parsed.query:
                params = parse_qsl(parsed.query, keep_blank_values=True)
                for key, _ in params:
                    if key and key not in seen_params:
                        seen_params.add(key)
                        all_params.append(key)

    # Write files
    with open('all-params.txt', 'w', encoding='utf-8') as f:
        if all_params:
            f.write('?' + '&'.join(f"{k}={pv}" for k in all_params) + '\n')

    with open('all-marge-uniq-params.txt', 'w', encoding='utf-8') as f:
        if all_params:
            f.write('?' + '&'.join(f"{k}={pv}" for k in all_params) + '\n')

    with open('all-paths.txt', 'w', encoding='utf-8') as f:
        for p in paths.keys():
            f.write(p + '\n')

    # Useful paths (with extension whitelist)
    EXT_WHITELIST = {'html', 'htm', 'shtml', 'shtm', 'xhtml', 'xht', 'php', 'asp', 'aspx', 'jsp', 'jspx', 'cfm', 'cfml', 'py', 'pl', 'rb', 'do', 'action', 'dll'}
    useful_paths = []
    for url in paths.keys():
        parsed = urlparse(url)
        ext = parsed.path.split('.')[-1].lower() if '.' in parsed.path else ''
        if not ext or ext in EXT_WHITELIST:
            useful_paths.append(url)

    with open('usefull-path-urls.txt', 'w', encoding='utf-8') as f:
        for p in useful_paths:
            f.write(p + '\n')

    # Merge with custom params
    total_params = set(all_params)
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

    # Fuzz list (50 params per line)
    param_list = sorted(total_params)
    with open('fuzz-params-list.txt', 'w', encoding='utf-8') as f:
        for i in range(0, len(param_list), 50):
            chunk = param_list[i:i+50]
            if chunk:
                f.write('?' + '&'.join(f"{k}={pv}" for k in chunk) + '\n')

    print(f"\n🎉 Done! Total unique paths: {len(paths)} | Parameters: {len(total_params)}")
    print("Generated files:")
    print("   • all-params.txt")
    print("   • all-marge-uniq-params.txt")
    print("   • all-paths.txt")
    print("   • usefull-path-urls.txt")
    print("   • total-uniq-params.txt")
    print("   • fuzz-params-list.txt")

if __name__ == "__main__":
    main()
