# kubernetes-doc.py

import os
import shutil
from urllib.parse import urljoin, urlparse

import requests_html as rh

BASE_DOMAIN = "https://kubernetes.io/docs/home/"

OUT_DIR = "docs"
MERGED_DIR = "merged_docs"
PDF_DIR = "pdf_docs"


def get_site_root(base_url: str) -> str:
    """Return scheme://host from a full URL."""
    p = urlparse(base_url)
    return f"{p.scheme}://{p.netloc}"


SITE_ROOT = get_site_root(BASE_DOMAIN)


def extract_link_from_li(li_el):
    """
    Given an lxml <li> element, return (text, href) for the primary link in it,
    or (None, None) if no link is found.

    It handles both:
      <li><a ...>Text</a></li>
      <li><input ...><label><a ...>Text</a></label><ul>...</ul></li>
    """
    # Look at direct children only
    link_el = None

    for child in li_el.getchildren():
        # Case 1: direct <a> child
        if child.tag == "a":
            link_el = child
            break

        # Case 2: <label><a> inside
        if child.tag == "label":
            # first <a> anywhere under this label
            for a in child.iter("a"):
                link_el = a
                break
            if link_el is not None:
                break

    if link_el is None:
        return None, None

    href = (link_el.get("href") or "").strip()
    # Join all text nodes inside the <a>
    text = "".join(link_el.itertext()).strip()

    if not href or not text:
        return None, None

    return text, href


def extract_links_ul(ul_el, level=0, seen=None):
    """
    Recursively walk the sidebar navigation <ul>/<li> tree.

    ul_el is an lxml <ul> element (NOT a requests_html.Element).
    """
    if seen is None:
        seen = set()

    # Iterate only direct <li> children of this <ul>
    for li_el in ul_el.getchildren():
        if li_el.tag != "li":
            continue

        # Get text + href for this li, if any
        text, href = extract_link_from_li(li_el)
        if href:
            url = urljoin(SITE_ROOT, href)
            if url not in seen:
                indent = "  " * level
                print(f"{indent}- {text} --> {url}")
                seen.add(url)

        # Recurse into any direct <ul> children of this <li>
        for child in li_el.getchildren():
            if child.tag == "ul":
                extract_links_ul(child, level + 1, seen)


# ============================================================
# MAIN EXECUTION
# ============================================================

if __name__ == "__main__":
    # 🧹 Clean output dirs
    for d in [OUT_DIR, MERGED_DIR, PDF_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d)
            print(f"🧹 Removed '{d}' directory.")
        os.makedirs(d, exist_ok=True)

    s = rh.HTMLSession()
    print(f"Fetching site: {BASE_DOMAIN}")
    r = s.get(BASE_DOMAIN)

    # Find the sidebar <div id="sidebarnav">
    side_menu = r.html.find("div#sidebarnav", first=True)
    if not side_menu:
        print("❌ Could not find #sidebarnav")
        raise SystemExit(1)

    side_el = side_menu.element  # this is the underlying lxml element

    # Find the first <ul> with class containing "td-sidebar-nav__section"
    root_ul_el = None
    for ul in side_el.iter("ul"):
        cls = ul.get("class", "")
        # Simple class check (no regex to keep it robust)
        if "td-sidebar-nav__section" in cls.split():
            root_ul_el = ul
            break

    if root_ul_el is None:
        print("❌ Could not find root sidebar <ul>")
        raise SystemExit(1)

    print("📚 Extracting navigation links recursively...\n")
    extract_links_ul(root_ul_el, level=0, seen=set())
