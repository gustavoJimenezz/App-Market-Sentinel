"""Tests for text cleaning functions."""

import pytest

from src.modules.text_processing.cleaners import (
    clean_text,
    normalize_whitespace,
    remove_emojis,
    remove_html_tags,
    remove_urls,
)


class TestRemoveHtmlTags:
    def test_simple_tag(self):
        assert remove_html_tags("<b>hello</b>") == "hello"

    def test_nested_tags(self):
        assert remove_html_tags("<div><p>text</p></div>") == "text"

    def test_self_closing_tag(self):
        assert remove_html_tags("before<br/>after") == "beforeafter"

    def test_no_tags(self):
        assert remove_html_tags("plain text") == "plain text"

    def test_malformed_html(self):
        assert remove_html_tags("<b>unclosed") == "unclosed"

    def test_tag_with_attributes(self):
        assert remove_html_tags('<a href="url">link</a>') == "link"

    def test_empty_string(self):
        assert remove_html_tags("") == ""


class TestRemoveUrls:
    def test_http_url(self):
        assert remove_urls("visit http://example.com today") == "visit  today"

    def test_https_url(self):
        assert remove_urls("see https://example.com/path") == "see "

    def test_www_url(self):
        assert remove_urls("go to www.example.com") == "go to "

    def test_multiple_urls(self):
        text = "http://a.com and https://b.com"
        assert remove_urls(text) == " and "

    def test_no_urls(self):
        assert remove_urls("no links here") == "no links here"

    def test_url_with_query_params(self):
        assert remove_urls("check https://x.com/p?q=1&r=2") == "check "


class TestNormalizeWhitespace:
    def test_multiple_spaces(self):
        assert normalize_whitespace("hello   world") == "hello world"

    def test_tabs_and_newlines(self):
        assert normalize_whitespace("hello\t\nworld") == "hello world"

    def test_leading_trailing(self):
        assert normalize_whitespace("  hello  ") == "hello"

    def test_already_normalized(self):
        assert normalize_whitespace("hello world") == "hello world"

    def test_only_whitespace(self):
        assert normalize_whitespace("   ") == ""

    def test_empty_string(self):
        assert normalize_whitespace("") == ""


class TestRemoveEmojis:
    def test_single_emoji(self):
        assert remove_emojis("hello 😀 world") == "hello  world"

    def test_multiple_emojis(self):
        assert remove_emojis("🎉🎊 party") == " party"

    def test_no_emojis(self):
        assert remove_emojis("plain text") == "plain text"

    def test_emoji_only(self):
        assert remove_emojis("😀😃😄") == ""

    def test_mixed_content(self):
        result = remove_emojis("great app! ⭐⭐⭐")
        assert "great app!" in result
        assert "⭐" not in result


class TestCleanText:
    def test_full_pipeline(self):
        text = "<b>Hello</b>  WORLD  http://x.com 😀"
        result = clean_text(text)
        assert result == "hello world"

    def test_preserves_basic_punctuation(self):
        result = clean_text("Great app! Works well.")
        assert result == "great app! works well."

    def test_empty_string(self):
        assert clean_text("") == ""

    def test_html_with_pii_like_content(self):
        text = "<p>Contact us at support</p>"
        result = clean_text(text)
        assert result == "contact us at support"

    def test_complex_real_review(self):
        text = (
            "<p>This app is AMAZING!! 🎉🎉 "
            "Visit https://mysite.com for more.\n\n"
            "   Highly   recommended!!!  </p>"
        )
        result = clean_text(text)
        assert result == "this app is amazing!! visit for more. highly recommended!!!"
