from __future__ import annotations

import unittest

from tools.AknetBrowser import DOCUMENT_ROOT, load_aknet_page, resolve_aknet_url


class AknetBrowserTest(unittest.TestCase):
    def test_homepage_and_directory_urls_resolve_inside_document_root(self) -> None:
        self.assertEqual(resolve_aknet_url("/"), DOCUMENT_ROOT / "index.md")
        self.assertEqual(
            resolve_aknet_url("/experiments/"),
            DOCUMENT_ROOT / "experiments" / "index.md",
        )
        self.assertIn("/experiments/", load_aknet_page("/"))

    def test_every_installed_page_uses_the_supported_markdown_dialect(self) -> None:
        for page in DOCUMENT_ROOT.rglob("*.md"):
            relative = page.relative_to(DOCUMENT_ROOT)
            url = "/" if relative == relative.with_name("index.md") and len(relative.parts) == 1 else None
            if url is None:
                url = "/" + str(relative.with_suffix(""))
                if relative.name == "index.md":
                    url = "/" + "/".join(relative.parts[:-1]) + "/"
            with self.subTest(url=url):
                self.assertIsInstance(load_aknet_page(url), str)

    def test_external_and_filesystem_urls_are_rejected(self) -> None:
        for url in ("https://example.com", "/../README", "/%2e%2e/README", "//etc/passwd"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                resolve_aknet_url(url)

    def test_missing_page_error_points_back_to_homepage(self) -> None:
        with self.assertRaisesRegex(ValueError, r"return to /"):
            load_aknet_page("/missing")


if __name__ == "__main__":
    unittest.main()
