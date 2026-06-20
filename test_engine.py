"""Unit tests for jobhunter_engine.py — no API calls, no network."""

import os
import sys
import hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jobhunter_engine import Job, SearchCache, AdzunaAPISource, JoobleAPISource


def test_relevance_filter_logic():
    query = "dot net developer"
    words = [w for w in query.lower().split() if len(w) > 1]

    # Should keep — at least one word matches
    assert any(w in "senior .net developer".lower() for w in words)
    assert any(w in "DotNet Developer".lower() for w in words)
    assert any(w in "ASP.NET Core Developer".lower() for w in words)
    assert any(w in "C# .NET Engineer".lower() for w in words)

    # Should drop — zero words match
    assert not any(w in "Pediatric Dentist".lower() for w in words)
    assert not any(w in "Hazardous Waste Manager".lower() for w in words)
    assert not any(w in "Staff Nurse".lower() for w in words)
    assert not any(w in "Sales Executive".lower() for w in words)

    print("  PASS: relevance_filter_logic")


def test_job_dict_structure():
    j = Job(title="Python Dev", company="Google",
            link="https://careers.google.com/123", source="Test")
    d = j.to_dict()
    expected_keys = {"title", "company", "link", "email", "phone", "source"}
    assert set(d.keys()) == expected_keys, f"Got keys: {set(d.keys())}"
    assert d["title"] == "Python Dev"
    assert d["company"] == "Google"
    assert d["email"] == "Not available"
    assert d["phone"] == "Not available"
    assert d["source"] == "Test"
    print("  PASS: job_dict_structure")


def test_dedup():
    j1 = Job(title="Python Dev", company="Google",
             link="https://apply.com/1")
    j2 = Job(title="Python Dev", company="Google",
             link="https://apply.com/2")
    j3 = Job(title="Python Dev", company="Microsoft",
             link="https://apply.com/3")
    assert j1.dedup_key() == j2.dedup_key(), "Same title+company should match"
    assert j1.dedup_key() != j3.dedup_key(), "Different company should differ"
    # same title+company regardless of case
    j4 = Job(title="python dev", company="google", link="https://apply.com/4")
    assert j1.dedup_key() == j4.dedup_key(), "Case insensitive dedup"
    print("  PASS: dedup")


def test_cache():
    cache = SearchCache(ttl=1)
    cache.set("key1", [1, 2, 3])
    assert cache.get("key1") == [1, 2, 3]
    assert cache.get("nonexistent") is None
    import time
    time.sleep(1.5)
    assert cache.get("key1") is None, "Cache should expire"
    print("  PASS: cache")


def test_api_graceful_skip():
    # Remove config so sources know they're unavailable
    for var in ["ADZUNA_APP_ID", "ADZUNA_API_KEY", "JOOBLE_API_KEY"]:
        os.environ.pop(var, None)

    a = AdzunaAPISource()
    assert a.search("python") == [], "Adzuna should return [] when not configured"
    assert a.available is False

    j = JoobleAPISource()
    assert j.search("python") == [], "Jooble should return [] when not configured"
    assert j.available is False
    print("  PASS: api_graceful_skip")


def test_email_extraction():
    from jobhunter_engine import extract_emails
    # Excluded by pattern: "example", "domain.com", "@company.com", etc.
    # Use emails that avoid those words
    text = "Contact hr@careers.co or support@real.org for info"
    emails = extract_emails(text)
    assert "hr@careers.co" in emails
    assert "support@real.org" in emails
    assert len(emails) >= 2
    # Excluded patterns should be filtered
    text2 = "Email example@domain.com or info@acmecorp"
    emails2 = extract_emails(text2)
    assert len(emails2) == 0
    print("  PASS: email_extraction")


def test_phone_extraction():
    from jobhunter_engine import extract_phones
    text = "Call (555) 123-4567 or +1 555-987-6543 ext 42"
    phones = extract_phones(text)
    assert len(phones) >= 1
    print("  PASS: phone_extraction")


if __name__ == "__main__":
    print(f"\nRunning {__file__}...\n")
    tests = [
        test_relevance_filter_logic,
        test_job_dict_structure,
        test_dedup,
        test_cache,
        test_api_graceful_skip,
        test_email_extraction,
        test_phone_extraction,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"  FAIL: {t.__name__}: {e}")
    total = len(tests)
    print(f"\n{'='*40}")
    print(f"Result: {passed}/{total} tests passed")
    if passed < total:
        sys.exit(1)
