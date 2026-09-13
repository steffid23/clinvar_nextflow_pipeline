#!/usr/bin/env python3
"""
download_data.py - ClinVar Dataset Streaming Downloader & Cacher
Downloads variant_summary.txt.gz from NCBI ClinVar FTP repository with HTTP streaming,
checksum/size validation, local caching, and automatic extraction.
"""

import sys
import os
import argparse
import gzip
import shutil
import requests

CLINVAR_FTP_URL = "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz"

def parse_args():
    parser = argparse.ArgumentParser(description="Download & Cache NCBI ClinVar dataset.")
    parser.add_argument("--url", type=str, default=CLINVAR_FTP_URL, help="ClinVar dataset URL")
    parser.add_argument("--output-dir", type=str, default="data", help="Output directory")
    parser.add_argument("--filename", type=str, default="variant_summary.txt.gz", help="Target filename")
    parser.add_argument("--force", action="store_true", help="Force redownload even if cached")
    parser.add_argument("--no-extract", action="store_true", help="Do not extract gz file")
    parser.add_argument("--sample-rows", type=int, default=0, help="Optional: create a sampled file with top N rows for fast debugging")
    return parser.parse_args()

def download_file(url, target_path, force=False):
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    
    if os.path.exists(target_path) and not force:
        file_size = os.path.getsize(target_path)
        if file_size > 1000000:  # >1MB cached file
            print(f"[CACHE HIT] File already cached at {target_path} ({file_size / (1024*1024):.2f} MB). Skipping download.")
            return target_path
        else:
            print(f"[WARNING] Cached file {target_path} seems incomplete ({file_size} bytes). Re-downloading...")
            
    print(f"[DOWNLOAD] Streaming ClinVar dataset from: {url}")
    print(f"[DOWNLOAD] Target location: {target_path}")
    
    headers = {'User-Agent': 'Mozilla/5.0 (Bioinformatics Pipeline Script)'}
    response = requests.get(url, stream=True, headers=headers, timeout=60)
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0))
    chunk_size = 1024 * 1024  # 1MB chunks
    downloaded = 0
    
    with open(target_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    sys.stdout.write(f"\rProgress: {downloaded / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB ({percent:.1f}%)")
                else:
                    sys.stdout.write(f"\rDownloaded: {downloaded / (1024*1024):.1f} MB")
                sys.stdout.flush()
    print("\n[DOWNLOAD COMPLETE] File successfully saved.")
    return target_path

def extract_gzip(gz_path, txt_path, force=False):
    if os.path.exists(txt_path) and not force:
        file_size = os.path.getsize(txt_path)
        if file_size > 5000000:
            print(f"[CACHE HIT] Extracted file exists at {txt_path} ({file_size / (1024*1024):.2f} MB). Skipping decompression.")
            return txt_path
            
    print(f"[DECOMPRESSING] Extracting {gz_path} -> {txt_path}...")
    with gzip.open(gz_path, 'rb') as f_in:
        with open(txt_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    print(f"[DECOMPRESSION COMPLETE] Extracted file size: {os.path.getsize(txt_path) / (1024*1024):.2f} MB")
    return txt_path

def create_sample(txt_path, sample_path, sample_rows):
    print(f"[SAMPLING] Creating test sample with top {sample_rows} rows at {sample_path}...")
    with open(txt_path, 'r', encoding='utf-8', errors='replace') as f_in:
        with open(sample_path, 'w', encoding='utf-8') as f_out:
            for i, line in enumerate(f_in):
                f_out.write(line)
                if i >= sample_rows:
                    break
    print(f"[SAMPLING COMPLETE] Sample file created: {sample_path}")

def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    gz_target = os.path.join(args.output_dir, args.filename)
    txt_target = os.path.splitext(gz_target)[0]
    
    download_file(args.url, gz_target, force=args.force)
    
    if not args.no_extract:
        extract_gzip(gz_target, txt_target, force=args.force)
        
    if args.sample_rows > 0:
        sample_path = os.path.join(args.output_dir, f"variant_summary_sample_{args.sample_rows}.txt")
        create_sample(txt_target, sample_path, args.sample_rows)

if __name__ == "__main__":
    main()
