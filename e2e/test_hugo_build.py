from conftest import HUGO, PLAIN_MESSAGE, HugoSite
from pytest import mark

pytestmark = mark.skipif(HUGO is None, reason="hugo is not installed")

UNKNOWN_SHORTCODE = '{{< nosuchshortcode "x" >}}'
UNPAIRED_OPENER = "{{< nosuchshortcode"
PERCENT_SHORTCODE = "{{% nosuchshortcode %}}"


def assert_builds(site: HugoSite, hugo_version: str) -> None:
    """Require a successful build, reporting Hugo’s own words when it is not."""
    result = site.build()
    assert result.ok, result.describe(site, hugo_version)


def assert_build_fails(site: HugoSite, hugo_version: str, message: str) -> None:
    """Require the unescaped body to break a site that otherwise builds.

    Building the plain body first is what stops this passing vacuously: without
    it, a machine where no build succeeds would report every control as green.
    """
    site.write_comment(PLAIN_MESSAGE)
    baseline = site.build()
    assert baseline.ok, (
        "this site does not build even without the body under test, so the "
        "control proves nothing\n" + baseline.describe(site, hugo_version)
    )

    site.write_unescaped_comment(message)
    result = site.build()
    assert not result.ok, (
        f"Hugo built {message!r} without error, so this version no longer fails "
        "on unknown shortcodes. The escaping may no longer be needed, but "
        "verify that before removing it.\n" + result.describe(site, hugo_version)
    )


@mark.parametrize("message", [UNKNOWN_SHORTCODE, UNPAIRED_OPENER, PERCENT_SHORTCODE])
def test_escaped_comment_builds(
    site: HugoSite, hugo_version: str, message: str
) -> None:
    site.write_comment(message)
    assert_builds(site, hugo_version)


@mark.parametrize("message", [UNKNOWN_SHORTCODE, UNPAIRED_OPENER, PERCENT_SHORTCODE])
def test_unescaped_comment_breaks_the_build(
    site: HugoSite, hugo_version: str, message: str
) -> None:
    """One comment would otherwise take the whole site offline."""
    assert_build_fails(site, hugo_version, message)


def test_code_fence_does_not_protect_the_build(
    site: HugoSite, hugo_version: str
) -> None:
    """Hugo expands shortcodes before Markdown, so fences are no shelter.

    This is why Goldmark’s `unsafe = false` is irrelevant to shortcodes.
    """
    assert_build_fails(site, hugo_version, f"```\n{UNKNOWN_SHORTCODE}\n```")


def test_escaped_shortcode_still_reads_as_written(
    site: HugoSite, hugo_version: str
) -> None:
    site.write_comment(f"Look at {UNKNOWN_SHORTCODE} here")
    assert_builds(site, hugo_version)
    html = site.rendered_comment()
    assert "{{&lt; nosuchshortcode" in html
    assert "&gt;}}" in html


def test_escaped_shortcode_in_code_fence_renders_literally(
    site: HugoSite, hugo_version: str
) -> None:
    site.write_comment(f"```\n{UNKNOWN_SHORTCODE}\n```")
    assert_builds(site, hugo_version)
    assert "{{&lt; nosuchshortcode" in site.rendered_comment()


def test_unpaired_opener_in_code_fence_shows_the_character_reference(
    site: HugoSite, hugo_version: str
) -> None:
    """Known cosmetic limit, recorded so it is not mistaken for a regression.

    An unpaired opener has no Hugo literal form, so it is broken with a
    character reference. Those are decoded in prose but not inside a code
    fence, where the reader therefore sees the reference itself. The build is
    safe either way, which is what matters.
    """
    site.write_comment(f"```\n{UNPAIRED_OPENER}\n```")
    assert_builds(site, hugo_version)
    assert "&amp;#123;" in site.rendered_comment()


def test_unpaired_opener_in_prose_reads_as_written(
    site: HugoSite, hugo_version: str
) -> None:
    site.write_comment(f"see {UNPAIRED_OPENER} here")
    assert_builds(site, hugo_version)
    assert "{{&lt; nosuchshortcode" in site.rendered_comment()


def test_ordinary_markdown_is_untouched(site: HugoSite, hugo_version: str) -> None:
    """Escaping must not quietly become general sanitization."""
    site.write_comment("Nice post!\n\n- one\n- two\n\nSee [docs](https://example.test).")
    assert_builds(site, hugo_version)
    html = site.rendered_comment()
    assert "<li>one</li>" in html
    assert 'href="https://example.test"' in html


def test_reports_hugo_version(hugo_version: str) -> None:
    """Surface the version, since the claims depend on Hugo’s behaviour."""
    assert hugo_version.startswith("hugo v")
