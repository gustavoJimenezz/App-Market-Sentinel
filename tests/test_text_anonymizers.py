"""Tests for PII anonymization functions."""

from src.modules.text_processing.anonymizers import (
    anonymize_author_name,
    anonymize_credit_cards,
    anonymize_emails,
    anonymize_phones,
    anonymize_pii,
    anonymize_ssn,
)


class TestAnonymizeEmails:
    def test_simple_email(self):
        assert anonymize_emails("contact john@example.com") == "contact [EMAIL]"

    def test_multiple_emails(self):
        text = "a@b.com and c@d.org"
        assert anonymize_emails(text) == "[EMAIL] and [EMAIL]"

    def test_email_in_sentence(self):
        text = "Send to user.name+tag@domain.co.uk please"
        assert anonymize_emails(text) == "Send to [EMAIL] please"

    def test_no_email(self):
        assert anonymize_emails("no email here") == "no email here"

    def test_empty_string(self):
        assert anonymize_emails("") == ""


class TestAnonymizePhones:
    def test_us_format_with_country(self):
        assert anonymize_phones("call +1-123-456-7890") == "call [PHONE]"

    def test_parenthesis_format(self):
        assert anonymize_phones("call (123) 456-7890") == "call [PHONE]"

    def test_dots_format(self):
        assert anonymize_phones("call 123.456.7890") == "call [PHONE]"

    def test_no_phone(self):
        assert anonymize_phones("no phone here") == "no phone here"

    def test_multiple_phones(self):
        text = "call (123) 456-7890 or +44 20 7946 0958"
        result = anonymize_phones(text)
        assert "[PHONE]" in result
        assert "456-7890" not in result


class TestAnonymizeCreditCards:
    def test_with_spaces(self):
        assert anonymize_credit_cards("card: 4111 1111 1111 1111") == "card: [CREDIT_CARD]"

    def test_with_dashes(self):
        assert anonymize_credit_cards("card: 4111-1111-1111-1111") == "card: [CREDIT_CARD]"

    def test_no_separator(self):
        assert anonymize_credit_cards("card: 4111111111111111") == "card: [CREDIT_CARD]"

    def test_no_credit_card(self):
        assert anonymize_credit_cards("no card here") == "no card here"


class TestAnonymizeSsn:
    def test_standard_format(self):
        assert anonymize_ssn("ssn: 123-45-6789") == "ssn: [SSN]"

    def test_no_ssn(self):
        assert anonymize_ssn("no ssn here") == "no ssn here"

    def test_ssn_in_sentence(self):
        text = "My SSN is 999-88-7777 please help"
        assert anonymize_ssn(text) == "My SSN is [SSN] please help"


class TestAnonymizeAuthorName:
    def test_full_name(self):
        assert anonymize_author_name("John Doe") == "J. D."

    def test_single_name(self):
        assert anonymize_author_name("John") == "J."

    def test_three_names(self):
        assert anonymize_author_name("John Michael Doe") == "J. M. D."

    def test_empty_string(self):
        assert anonymize_author_name("") == ""

    def test_whitespace_only(self):
        assert anonymize_author_name("   ") == ""

    def test_lowercase_name(self):
        assert anonymize_author_name("jane doe") == "J. D."


class TestAnonymizePii:
    def test_email_and_phone(self):
        text = "contact john@test.com or (555) 123-4567"
        result = anonymize_pii(text)
        assert "[EMAIL]" in result
        assert "[PHONE]" in result
        assert "john@test.com" not in result

    def test_credit_card_and_ssn(self):
        text = "card 4111 1111 1111 1111 ssn 123-45-6789"
        result = anonymize_pii(text)
        assert "[CREDIT_CARD]" in result
        assert "[SSN]" in result

    def test_no_pii(self):
        text = "this is a clean review with no personal info"
        assert anonymize_pii(text) == text

    def test_all_pii_types(self):
        text = (
            "Email me at user@mail.com, call (555) 123-4567, "
            "card 4111 1111 1111 1111, ssn 123-45-6789"
        )
        result = anonymize_pii(text)
        assert "[EMAIL]" in result
        assert "[PHONE]" in result
        assert "[CREDIT_CARD]" in result
        assert "[SSN]" in result
