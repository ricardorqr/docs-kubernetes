# kubernetes-doc.py

import os
import re
import shutil
from urllib.parse import urljoin, urlparse

import requests_html as rh

# Entry point URL for the docs sidebar
BASE_DOMAIN = "https://kubernetes.io/docs/home/"
SITE_ROOT = f"{urlparse(BASE_DOMAIN).scheme}://{urlparse(BASE_DOMAIN).netloc}"

OUT_DIR = "docs"
MERGED_DIR = "merged_docs"
PDF_DIR = "pdf_docs"

# EXCLUDE: exact URLs that should NOT be downloaded
EXCLUDE_URLS = {
    "https://kubernetes.io/docs/",
    "https://kubernetes.io/docs/home/",
}


def safe_filename(url: str) -> str:
    """
    Convert a URL into a filesystem-safe filename.
    Example:
      https://kubernetes.io/docs/setup/  ->  docs_setup.html
    """
    path = url.replace(SITE_ROOT, "").strip("/")  # e.g. 'docs/setup'
    name = re.sub(r"[^0-9a-zA-Z\-]+", "_", path)
    if not name:
        name = "index"
    return name + ".html"


def save_page_content(session: rh.HTMLSession, url: str):
    """
    Fetch a page and save only <div class='td-content'> into /docs.
    """
    # Skip explicit excluded URLs
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
    """
    Given an lxml <li> element, return (text, href) for the primary link.
    Handles:
      <li><a ...>Text</a></li>
      <li><input ...><label><a ...>Text</a></label>...</li>
    """
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
    """
    Recursively walk the sidebar <ul>/<li> tree.
    ul_el is an lxml <ul> element.
    """
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

                # Download td-content for this URL (unless excluded)
                save_page_content(session, url)

        # Recurse into nested <ul> children
        for child in li_el.getchildren():
            if child.tag == "ul":
                extract_links_ul(session, child, level + 1, seen)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    # Clean output dirs
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

    print("📚 Extracting navigation links + saving td-content...\n")
    extract_links_ul(session, root_ul_el, level=0, seen=set())

    print("\n🎉 DONE — processed sidebar successfully")
