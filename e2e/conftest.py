import shutil
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from pytest import TempPathFactory, fail, fixture

from gitmentario.models import Comment
from gitmentario.ssg import prepare_comment_markdown

HUGO = shutil.which("hugo")

CONTENT_DIR = PurePosixPath("content")
COMMENTS_DIR = PurePosixPath("comments")
PAGE_ID = "my-post"

PLAIN_MESSAGE = "An ordinary comment with no shortcode in it."
"""Body used to prove a site builds at all, before any test claims more."""

HUGO_CONFIG = """\
baseURL = "https://example.test/"
title = "Gitmentario e2e"
"""

PAGE_LAYOUT = "{{ .Content }}"


@dataclass(frozen=True)
class BuildResult:
    """The outcome of one Hugo run, with everything needed to diagnose it."""

    ok: bool
    output: str

    def describe(self, site: "HugoSite", version: str) -> str:
        """Compose a failure message a reader can act on without rerunning."""
        return (
            f"hugo exited {'0' if self.ok else 'non-zero'}\n"
            f"version: {version}\n"
            f"--- comment file ---\n{site.comment_source()}\n"
            f"--- hugo output ---\n{self.output or '(no output)'}"
        )


class HugoSite:
    """A throwaway Hugo site holding a single comment page."""

    def __init__(self, root: Path) -> None:
        """Create the minimal site skeleton under ``root``."""
        self.root = root
        (root / "content").mkdir(parents=True, exist_ok=True)
        (root / "layouts").mkdir(parents=True, exist_ok=True)
        (root / "hugo.toml").write_text(HUGO_CONFIG)
        (root / "layouts" / "page.html").write_text(PAGE_LAYOUT)
        self.comment_path: Path | None = None

    def write_comment(self, message: str) -> Path:
        """Write a comment through the production path, escaping included."""
        return self._write(*self._render(message))

    def write_unescaped_comment(self, message: str) -> Path:
        """Write the same file with the body left raw.

        This is the negative control: it shows what would reach the repository
        if the escaping were removed, so a passing suite cannot be mistaken for
        Hugo simply not caring.
        """
        file_path, md_content = self._render(message)
        frontmatter, _, _ = md_content.partition("---\n\n")
        return self._write(file_path, f"{frontmatter}---\n\n{message}\n")

    def _render(self, message: str) -> tuple[str, str]:
        comment = Comment(author="Test", message=message, page_id=PAGE_ID)
        return prepare_comment_markdown(comment, CONTENT_DIR, COMMENTS_DIR)

    def _write(self, file_path: str, md_content: str) -> Path:
        target = self.root / file_path
        target.parent.mkdir(parents=True, exist_ok=True)
        # The filename carries a timestamp, so rewriting a comment would other-
        # wise leave the previous one behind and give the site two pages.
        if self.comment_path is not None and self.comment_path != target:
            self.comment_path.unlink(missing_ok=True)
        target.write_text(md_content)
        self.comment_path = target
        return target

    def comment_source(self) -> str:
        """Return the Markdown currently on disk, for failure messages."""
        if self.comment_path is None:
            return "(no comment written)"
        return self.comment_path.read_text()

    def build(self) -> BuildResult:
        """Run Hugo and capture everything it said.

        Deliberately not `--quiet`: that suppresses the error text, which left
        earlier failures reporting only `assert 1 == 0` with an empty stderr.
        Hugo writes diagnostics to either stream depending on version and log
        level, so both are kept.
        """
        completed = subprocess.run(
            [str(HUGO), "--destination", "out"],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )
        output = "\n".join(
            part.strip() for part in (completed.stdout, completed.stderr) if part.strip()
        )
        return BuildResult(ok=completed.returncode == 0, output=output)

    def rendered_comment(self) -> str:
        """Return the HTML Hugo produced for the comment page.

        Located by glob rather than by rebuilding the URL: Hugo derives the slug
        from the filename with rules of its own (it lowercases, among other
        things), and this fixture holds exactly one comment page.
        """
        assert self.comment_path is not None, "write a comment first"
        rendered = [
            path
            for path in self.root.glob("out/**/index.html")
            if "/comments/" in path.as_posix()
        ]
        assert len(rendered) == 1, f"expected one comment page, found {rendered}"
        return rendered[0].read_text()


@fixture(scope="session")
def hugo_version() -> str:
    """Report the Hugo the claims under test were verified against."""
    completed = subprocess.run(
        [str(HUGO), "version"], capture_output=True, text=True, check=True
    )
    return completed.stdout.strip()


@fixture(scope="session")
def hugo_baseline(tmp_path_factory: TempPathFactory, hugo_version: str) -> None:
    """Prove the fixture site builds at all before any test interprets a result.

    Without this, an environment where every build fails still shows the control
    tests as passing, because they only assert that a build fails. Failing here
    turns that into one legible error naming the version and Hugo's own words.
    """
    site = HugoSite(tmp_path_factory.mktemp("hugo-baseline"))
    site.write_comment(PLAIN_MESSAGE)
    result = site.build()
    if not result.ok:
        fail(
            "the e2e fixture site does not build on this Hugo, so no test in "
            "this module can mean anything. Fix this first.\n"
            + result.describe(site, hugo_version),
            pytrace=False,
        )


@fixture
def site(tmp_path: Path, hugo_baseline: None) -> Iterator[HugoSite]:
    """Provide an isolated Hugo site for one test."""
    yield HugoSite(tmp_path)
