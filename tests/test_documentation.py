"""Keep owned public Markdown file links navigable (not external URLs/anchors)."""
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
COLLECTION = ROOT / "ansible_collections/shanemcd/dr_lab"


class DocumentationTests(unittest.TestCase):
    def test_local_markdown_file_links_resolve(self):
        pages = sorted(set(ROOT.glob("*.md")) | set((ROOT / "docs").rglob("*.md"))
                       | set(COLLECTION.rglob("*.md")))
        checked = 0
        for page in pages:
            # Inline file links only: reference links and generated HTML are not covered.
            for target in re.findall(r"\[[^\]]*\]\(([^\s)]+)\)", page.read_text()):
                link = urlsplit(target)
                if link.scheme or link.netloc or not link.path:
                    continue
                with self.subTest(page=str(page.relative_to(ROOT)), target=target):
                    path = (page.parent / unquote(link.path)).resolve()
                    self.assertTrue(path.is_relative_to(ROOT), "link leaves repository")
                    self.assertTrue(path.exists(), "missing local link target")
                checked += 1
        self.assertGreater(checked, 60)


if __name__ == "__main__":
    unittest.main()
