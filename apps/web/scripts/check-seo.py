import argparse
import json
import re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from xml.etree import ElementTree


class PageMetadata(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.meta = {}
        self.canonicals = []
        self.title = ""
        self.heading_count = 0
        self.author_urls = []
        self.links = []
        self.images = []
        self.descriptions = []
        self.schemas = []
        self.language = ""
        self.in_title = False
        self.schema_parts = None
        self.feed(path.read_text(encoding="utf-8"))
        self.close()

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag == "html":
            self.language = attributes.get("lang", "")
        elif tag == "title":
            self.in_title = True
        elif tag == "h1":
            self.heading_count += 1
        elif tag == "meta":
            key = attributes.get("name") or attributes.get("property")
            if key:
                self.meta[key] = attributes.get("content", "")
        elif tag == "link" and "canonical" in attributes.get("rel", "").split():
            self.canonicals.append(attributes.get("href", ""))
        elif tag == "link" and "describedby" in attributes.get("rel", "").split():
            self.descriptions.append(attributes.get("href", ""))
        elif tag == "a" and "author" in attributes.get("rel", "").split():
            self.author_urls.append(attributes.get("href", ""))
            self.links.append(attributes.get("href", ""))
        elif tag == "a" and "href" in attributes:
            self.links.append(attributes["href"])
        elif tag == "img":
            self.images.append(attributes)
        elif tag == "script" and attributes.get("type") == "application/ld+json":
            self.schema_parts = []

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.schema_parts is not None:
            self.schema_parts.append(data)

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        elif tag == "script" and self.schema_parts is not None:
            self.schemas.append(json.loads("".join(self.schema_parts)))
            self.schema_parts = None


def check_site(output_directory):
    home = PageMetadata(output_directory / "index.html")
    assert len(home.canonicals) == 1, "Home must have one canonical URL"
    base_url = home.canonicals[0]
    base = urlsplit(base_url)
    assert base.scheme == "https" and base.hostname not in (
        "localhost", "127.0.0.1", "example.com"
    ), "Build must use a real HTTPS production URL"
    assert base_url.endswith("/"), "Home URL must end in a slash"
    author_id = base_url + "#person"
    website_id = base_url + "#website"
    canonical_urls = set()
    titles = set()
    descriptions = set()
    article_count = 0

    def local_file(url):
        parsed = urlsplit(url)
        assert parsed.scheme == base.scheme and parsed.netloc == base.netloc, url
        assert parsed.path.startswith(base.path), f"URL outside the site: {url}"
        relative = unquote(parsed.path[len(base.path):])
        path = output_directory / relative
        return path / "index.html" if parsed.path.endswith("/") else path

    for path in sorted(output_directory.rglob("*.html")):
        page = PageMetadata(path)
        assert page.language.startswith("es"), f"Missing Spanish language: {path}"
        assert page.heading_count == 1, f"Expected one H1: {path}"
        if "noindex" in page.meta.get("robots", ""):
            assert not page.canonicals, f"Noindex page has a canonical: {path}"
            assert not page.schemas, f"Noindex page has structured data: {path}"
            continue
        assert len(page.canonicals) == 1, f"Expected one canonical: {path}"
        canonical = page.canonicals[0]
        assert local_file(canonical).resolve() == path.resolve(), canonical
        assert canonical not in canonical_urls, f"Duplicate canonical: {canonical}"
        canonical_urls.add(canonical)
        assert page.title.strip() and page.title not in titles, f"Invalid title: {path}"
        titles.add(page.title)
        description = page.meta.get("description", "").strip()
        assert description and description not in descriptions, f"Invalid description: {path}"
        descriptions.add(description)
        assert page.meta.get("og:url") == canonical, f"Open Graph URL mismatch: {path}"
        assert page.meta.get("og:title") == page.title, f"Open Graph title mismatch: {path}"
        assert page.meta.get("twitter:title") == page.title, f"Social title mismatch: {path}"
        assert page.meta.get("og:description") == description, path
        assert local_file(page.meta.get("og:image", "")).is_file(), f"Missing social image: {path}"
        assert page.meta.get("twitter:image") == page.meta["og:image"], path
        assert "max-image-preview:large" in page.meta.get("robots", ""), path
        assert any(urljoin(base_url, url) == base_url + "llms.txt" for url in page.descriptions), f"Missing llms.txt discovery: {path}"
        for href in page.links:
            target = urljoin(canonical, href)
            parsed = urlsplit(target)
            if parsed.netloc == base.netloc and parsed.path.startswith(base.path):
                assert local_file(target).is_file(), f"Broken internal link in {path}: {href}"
        for image in page.images:
            assert "alt" in image, f"Missing image alternative text: {path}"
            assert int(image.get("width", "0")) > 0 and int(image.get("height", "0")) > 0, f"Missing image dimensions: {path}"
            if not urlsplit(image.get("src", "")).path.endswith(".svg"):
                assert image.get("loading") == "lazy" or image.get("fetchpriority") == "high", f"Missing image loading strategy: {path}"
        assert len(page.schemas) == 1, f"Expected one JSON-LD graph: {path}"
        schema = page.schemas[0]
        assert schema.get("@context") == "https://schema.org", path
        nodes = {node["@id"]: node for node in schema["@graph"]}
        person = nodes[author_id]
        assert person["@type"] == "Person", path
        assert person["name"] == page.meta["author"] == home.meta["author"], path
        assert person["url"] == base_url and person["sameAs"], path
        assert nodes[website_id]["url"] == base_url, path
        webpage = nodes[canonical + "#webpage"]
        assert webpage["url"] == canonical and webpage["description"] == description, path
        assert webpage["isPartOf"]["@id"] == website_id, path
        if canonical == base_url:
            assert webpage["@type"] == "ProfilePage", path
            assert webpage["mainEntity"]["@id"] == author_id, path
        for node in nodes.values():
            if node["@type"] == "BlogPosting":
                article_count += 1
                assert node["author"]["@id"] == author_id, path
                assert any(urljoin(base_url, url) == base_url for url in page.author_urls), f"Missing visible author link: {path}"
                assert node["mainEntityOfPage"]["@id"] == webpage["@id"], path
                published = datetime.fromisoformat(node["datePublished"])
                modified = datetime.fromisoformat(node["dateModified"])
                assert modified >= published, f"Invalid article dates: {path}"
                assert node["dateModified"] == page.meta.get("article:modified_time"), path
            elif node["@type"] == "BreadcrumbList":
                items = node["itemListElement"]
                assert [item["position"] for item in items] == list(range(1, len(items) + 1)), path
                assert items[-1]["item"] == canonical, path

    sitemap = ElementTree.parse(output_directory / "sitemap.xml")
    namespace = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    sitemap_urls = set()
    for entry in sitemap.findall("sitemap:url", namespace):
        sitemap_urls.add(entry.findtext("sitemap:loc", namespaces=namespace))
        datetime.fromisoformat(entry.findtext("sitemap:lastmod", namespaces=namespace))
    assert sitemap_urls == canonical_urls, "Sitemap and indexable pages differ"
    robots = (output_directory / "robots.txt").read_text(encoding="utf-8")
    assert f"Sitemap: {base_url}sitemap.xml" in robots, "Missing sitemap declaration"
    for feed_path in ("index.xml", "posts/index.xml"):
        feed = ElementTree.parse(output_directory / feed_path)
        for item in feed.findall("channel/item"):
            assert item.findtext("link") in canonical_urls, f"RSS links to an unknown page: {feed_path}"
    llms = (output_directory / "llms.txt").read_text(encoding="utf-8")
    assert llms.startswith("# " + nodes[website_id]["name"]), "Invalid llms.txt title"
    llms_links = re.findall(r"\[[^\]\n]+\]\((https://[^\s)]+)\)", llms)
    assert llms_links, "llms.txt has no links"
    for url in llms_links:
        assert local_file(url).is_file(), f"Broken llms.txt link: {url}"
    for url in canonical_urls:
        if "/posts/" in urlsplit(url).path and url != base_url + "posts/":
            assert url in llms_links, f"Article missing from llms.txt: {url}"
    humans = (output_directory / "humans.txt").read_text(encoding="utf-8")
    assert home.meta["author"] in humans and base_url in humans, "Invalid humans.txt identity"
    print(f"SEO OK: {len(canonical_urls)} indexable pages, {article_count} articles, valid JSON-LD, sitemap, RSS, local links, llms.txt and humans.txt.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate production SEO output without third-party dependencies.")
    parser.add_argument("output_directory", nargs="?", type=Path, default=Path("apps/web/public"))
    arguments = parser.parse_args()
    check_site(arguments.output_directory)