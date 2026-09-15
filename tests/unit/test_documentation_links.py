"""Unit test verifying that all markdown documentation links and references exist."""

import re
from pathlib import Path


def _extract_markdown_links(content: str) -> list[str]:
    """Extract URL/path targets from standard markdown [text](target) links."""
    # Match [text](target), ignoring images ![alt](target) for separate validation or matching both
    pattern = r"\[(?:[^\]]+)\]\(([^)#\s]+)(?:#[^\)]*)?\)"
    return re.findall(pattern, content)


def _extract_wiki_bracket_links(content: str) -> list[str]:
    """Extract targets from wiki [[Target]] or [[Target|Label]] links."""
    pattern = r"\[\[([^\]\|]+)(?:\|[^\]]+)?\]\]"
    return re.findall(pattern, content)


def test_wiki_internal_links_exist():
    """Verify that all wiki cross-references between wiki pages exist."""
    repo_root = Path(__file__).parent.parent.parent
    wiki_dir = repo_root / "docs" / "wiki"
    assert wiki_dir.is_dir(), f"Wiki directory {wiki_dir} not found"

    wiki_files = list(wiki_dir.glob("*.md"))
    assert (
        len(wiki_files) >= 8
    ), f"Expected at least 8 wiki files, found {len(wiki_files)}"

    for md_file in wiki_files:
        content = md_file.read_text(encoding="utf-8")

        # 1. Check [[BracketLinks]]
        bracket_links = _extract_wiki_bracket_links(content)
        for link in bracket_links:
            target_name = link.strip()
            target_file = wiki_dir / f"{target_name}.md"
            assert target_file.is_file(), (
                f"Broken wiki bracket link [[{target_name}]] in {md_file.name}. "
                f"Target {target_file} does not exist."
            )

        # 2. Check standard relative markdown [text](target.md) links
        md_links = _extract_markdown_links(content)
        for link in md_links:
            if link.startswith(("http://", "https://", "mailto:", "ftp://")):
                continue
            # Resolve relative link from current file directory
            target_path = (md_file.parent / link).resolve()
            assert target_path.exists(), (
                f"Broken relative link [{link}] in {md_file.name}. "
                f"Resolved target {target_path} does not exist."
            )


def test_readme_and_developer_docs_links():
    """Verify that root README.md and DEVELOPER.md links to wiki and files exist."""
    repo_root = Path(__file__).parent.parent.parent

    for doc_name in ["README.md", "DEVELOPER.md"]:
        doc_file = repo_root / doc_name
        assert doc_file.is_file(), f"{doc_name} not found"
        content = doc_file.read_text(encoding="utf-8")

        links = _extract_markdown_links(content)
        for link in links:
            if link.startswith(("http://", "https://", "mailto:", "ftp://")):
                continue
            target_path = (doc_file.parent / link).resolve()
            assert target_path.exists(), (
                f"Broken relative link [{link}] in {doc_name}. "
                f"Resolved target {target_path} does not exist."
            )
