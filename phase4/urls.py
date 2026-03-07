"""Phase 4: Build full URL list (funds + blog/help + comparison)."""

from .config import BLOG_HELP_URLS, COMPARISON_CALCULATOR_URLS, FUND_URLS


def get_fund_urls():
    """All fund URLs (Phase 1 + Phase 4 extra)."""
    return list(FUND_URLS)


def get_blog_help_urls():
    """Blog and help pages for deeper explanations."""
    return list(BLOG_HELP_URLS)


def get_comparison_calculator_urls():
    """Comparison and calculator pages (optional)."""
    return list(COMPARISON_CALCULATOR_URLS)


def get_all_urls():
    """Combined list: fund pages, blog/help, comparison/calculator. Order: funds first, then blog/help."""
    seen = set()
    out = []
    for u in get_fund_urls() + get_blog_help_urls() + get_comparison_calculator_urls():
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out
