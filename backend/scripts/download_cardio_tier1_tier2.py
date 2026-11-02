# -*- coding: utf-8 -*-
import csv
import json
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from pypdf import PdfReader

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "docs/research/cardio-zh-20261027"
DOWNLOAD_DIR = DOCS_DIR / "downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
TEXT_EXTRACTED_DIR = DOCS_DIR / "extracted_texts"
TEXT_EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

with open(DOCS_DIR / "公开全文优先下载_104份.csv", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

# 筛选 23 篇高质量指南、共识、标准
candidates = []
for r in rows:
    code = r["编号"]
    doc_type = r["文献类型"]
    if code in ["CV-007", "CV-025"]:
        continue
    if doc_type in ["指南", "专家共识", "专家建议", "标准/服务规范"]:
        candidates.append(r)

print(f"=== 开始下载并提取 {len(candidates)} 篇高质量心血管指南与共识 ===")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://www.chinagp.net/",
    "Accept": "text/html,application/xhtml+xml,application/xml,application/pdf;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
}

manifest = []

for idx, r in enumerate(candidates, 1):
    code = r["编号"]
    title = r["文献名称"]
    year = r["年份"]
    doc_type = r["文献类型"]
    platform = r.get("发布/刊载平台", "")
    url = r.get("已核实PDF") or r.get("推荐获取链接") or r.get("已核实HTML") or ""
    
    # 确定文件后缀与下载路径
    is_html = "csc.cma.org.cn/art" in url or url.endswith(".html")
    ext = ".html" if is_html else ".pdf"
    clean_title = re.sub(r'[\/:*?"<>|]', '_', title)[:30]
    filename = f"{code}_{clean_title}{ext}"
    dest_path = DOWNLOAD_DIR / filename
    
    print(f"\n[{idx}/{len(candidates)}] 下载: [{code}] 《{title}》...")
    
    downloaded = False
    if dest_path.exists() and dest_path.stat().st_size > 1024:
        print(f"  -> 本地已存在 ({dest_path.stat().st_size} bytes)")
        downloaded = True
    else:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                content = resp.read()
                dest_path.write_bytes(content)
                print(f"  -> 下载成功 ({len(content)} bytes)")
                downloaded = True
        except Exception as e:
            print(f"  -> 下载失败: {e}")
            downloaded = False
            
    # 提取纯文本
    extracted_text = ""
    if downloaded:
        txt_path = TEXT_EXTRACTED_DIR / f"{code}_{clean_title}.txt"
        try:
            if ext == ".pdf":
                reader = PdfReader(str(dest_path))
                pages_text = []
                for p_idx, page in enumerate(reader.pages):
                    t = page.extract_text() or ""
                    if t.strip():
                        pages_text.append(f"--- Page {p_idx+1} ---\n{t}")
                extracted_text = "\n\n".join(pages_text)
            else: # html
                html_raw = dest_path.read_text(encoding="utf-8", errors="ignore")
                # 简单去除 script 和 html 标签
                clean_text = re.sub(r'<script[\s\S]*?</script>', '', html_raw)
                clean_text = re.sub(r'<style[\s\S]*?</style>', '', clean_text)
                clean_text = re.sub(r'<[^>]+>', '\n', clean_text)
                clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text)
                extracted_text = clean_text.strip()
                
            txt_path.write_text(extracted_text, encoding="utf-8")
            print(f"  -> 提取文本: {len(extracted_text)} 字符, 已存至 {txt_path.name}")
        except Exception as e:
            print(f"  -> 提取文本失败: {e}")
            
    manifest.append({
        "code": code,
        "title": title,
        "year": year,
        "doc_type": doc_type,
        "platform": platform,
        "url": url,
        "file": str(dest_path.name),
        "file_size": dest_path.stat().st_size if dest_path.exists() else 0,
        "chars_count": len(extracted_text),
        "text_file": f"{code}_{clean_title}.txt" if extracted_text else ""
    })
    time.sleep(0.5)

# 保存下载清单报告
manifest_path = DOCS_DIR / "download_manifest.json"
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print("\n" + "=" * 60)
print(f"下载提取完成！统计报告已保存至 {manifest_path.name}")
success_docs = [m for m in manifest if m["chars_count"] > 500]
print(f"成功提取正文有效文献: {len(success_docs)} / {len(candidates)} 篇")
