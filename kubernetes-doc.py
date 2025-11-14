# kubernetes-doc.py

import os
import re
import shutil
from urllib.parse import urljoin, urlparse
import requests_html as rh
from playwright.sync_api import sync_playwright  # <-- Added for PDF generation

# Entry point URL for the docs sidebar
BASE_DOMAIN = "https://kubernetes.io/docs/home/"
SITE_ROOT = f"{urlparse(BASE_DOMAIN).scheme}://{urlparse(BASE_DOMAIN).netloc}"

OUT_DIR = "docs"
MERGED_DIR = "merged_docs"
PDF_DIR = "pdf_docs"

# EXACT URLs we never save td-content for
EXCLUDE_URLS = {
  "https://kubernetes.io/docs/",
  "https://kubernetes.io/docs/home/",
}


# ============================================================
# UTILITIES
# ============================================================

def safe_filename(url: str) -> str:
  path = url.replace(SITE_ROOT, "").strip("/")
  name = re.sub(r"[^0-9a-zA-Z\-]+", "_", path)
  if not name:
    name = "index"
  return name + ".html"


def save_page_content(session: rh.HTMLSession, url: str):
  if url in EXCLUDE_URLS:
    print(f"⏭️  Excluded from download: {url}")
    return

  try:
    r = session.get(url)
    div = r.html.find("div.td-content", first=True)
    if div is None:
      print(f"⚠️  No td-content for {url}")
      return

    filename = safe_filename(url)
    path = os.path.join(OUT_DIR, filename)

    with open(path, "w", encoding="utf-8") as f:
      f.write(div.html)

    print(f"💾 Saved: {filename}")

  except Exception as e:
    print(f"❌ Error saving {url}: {e}")


def extract_link_from_li(li_el):
  link_el = None

  for child in li_el.getchildren():
    if child.tag == "a":
      link_el = child
      break
    if child.tag == "label":
      for a in child.iter("a"):
        link_el = a
        break
      if link_el is not None:
        break

  if link_el is None:
    return None, None

  href = (link_el.get("href") or "").strip()
  text = "".join(link_el.itertext()).strip()

  if not href or not text:
    return None, None

  return text, href


def extract_links_ul(session: rh.HTMLSession, ul_el, level=0, seen=None):
  if seen is None:
    seen = set()

  for li_el in ul_el.getchildren():
    if li_el.tag != "li":
      continue

    text, href = extract_link_from_li(li_el)
    if href:
      url = urljoin(SITE_ROOT, href)

      if url not in seen:
        indent = "  " * level
        print(f"{indent}- {text} --> {url}")
        seen.add(url)
        save_page_content(session, url)

    for child in li_el.getchildren():
      if child.tag == "ul":
        extract_links_ul(session, child, level + 1, seen)


# ============================================================
# MERGE DOWNLOADED HTML FILES
# ============================================================

def merge_downloaded_files():
  print("\n📦 Merging HTML files into /merged_docs ...")

  groups = {}

  for filename in os.listdir(OUT_DIR):
    if not filename.endswith(".html"):
      continue

    prefix_removed = filename.replace("docs_", "", 1)
    parts = prefix_removed.split("_", 1)

    if len(parts) < 2:
      continue

    category, remainder = parts
    first_letter = remainder[0].lower()

    group_filename = f"docs_{category}_{first_letter}.html"

    if group_filename not in groups:
      groups[group_filename] = []

    with open(os.path.join(OUT_DIR, filename), "r", encoding="utf-8") as f:
      groups[group_filename].append(f"<hr>\n{f.read()}")

  os.makedirs(MERGED_DIR, exist_ok=True)

  for merged_name, contents in groups.items():
    with open(os.path.join(MERGED_DIR, merged_name), "w", encoding="utf-8") as merged_file:
      merged_file.write("\n".join(contents))

    print(f"🔗 Merged: {merged_name}  ({len(contents)} pages)")


# ============================================================
# PDF GENERATION (Playwright)
# ============================================================

def generate_pdf_from_html(html_path, pdf_path):
  with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()

    page = context.new_page()
    page.goto(f"file://{os.path.abspath(html_path)}", wait_until="load")

    page.pdf(
      path=pdf_path,
      format="A4",
      margin={"top": "20mm", "bottom": "20mm", "left": "15mm", "right": "15mm"},
    )

    page.close()
    browser.close()


def create_pdf_files():
  print("\n🖨 Generating PDFs into /pdf_docs ...")
  os.makedirs(PDF_DIR, exist_ok=True)

  for filename in os.listdir(MERGED_DIR):
    if not filename.endswith(".html"):
      continue

    html_path = os.path.join(MERGED_DIR, filename)
    pdf_name = filename.replace(".html", ".pdf")
    pdf_path = os.path.join(PDF_DIR, pdf_name)

    try:
      print(f"📄 Creating PDF → {pdf_name}")
      generate_pdf_from_html(html_path, pdf_path)
    except Exception as e:
      print(f"❌ Error generating PDF for {filename}: {e}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
  for d in [OUT_DIR, MERGED_DIR, PDF_DIR]:
    if os.path.exists(d):
      shutil.rmtree(d)
      print(f"🧹 Removed '{d}' directory.")
    os.makedirs(d, exist_ok=True)

  session = rh.HTMLSession()
  print(f"Fetching site: {BASE_DOMAIN}")
  r = session.get(BASE_DOMAIN)

  sidebar = r.html.find("div#sidebarnav", first=True)
  if sidebar is None:
    print("❌ Could not find #sidebarnav")
    raise SystemExit(1)

  root_ul_el = None
  for ul in sidebar.element.iter("ul"):
    cls = ul.get("class", "")
    if "td-sidebar-nav__section" in cls.split():
      root_ul_el = ul
      break

  if root_ul_el is None:
    print("❌ Could not find root sidebar <ul>")
    raise SystemExit(1)

  print("📚 Extracting sidebar structure + saving td-content...\n")
  extract_links_ul(session, root_ul_el, level=0, seen=set())

  merge_downloaded_files()
  create_pdf_files()

  print("\n🎉 COMPLETED!")
