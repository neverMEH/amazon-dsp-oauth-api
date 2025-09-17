#!/usr/bin/env python3
"""
Test which Amazon Advertising API scopes are valid
"""
import webbrowser
from urllib.parse import urlencode

def test_scope(scope_list, description):
    """Test a specific scope configuration"""

    client_id = "amzn1.application-oa2-client.cf1789da23f74ee489e2373e424726af"
    redirect_uri = "https://amazon-dsp-oauth-api-production.up.railway.app/api/v1/auth/amazon/callback"

    params = {
        "client_id": client_id,
        "scope": " ".join(scope_list) if scope_list else "",
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": "test_scope"
    }

    url = f"https://www.amazon.com/ap/oa?{urlencode(params)}"

    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Scopes: {' '.join(scope_list) if scope_list else 'NONE'}")
    print(f"URL: {url}")
    print(f"{'='*60}")

    return url

def main():
    print("Amazon Advertising API Scope Testing")
    print("=" * 60)
    print("This will generate URLs to test different scope combinations.")
    print("Try each URL manually to see which ones work.\n")

    test_cases = [
        # Test 1: No scopes (should work - proves client_id and redirect_uri are valid)
        ([], "No scopes - Basic OAuth test"),

        # Test 2: Single basic scope
        (["advertising::campaign_management"], "Single scope - Campaign Management"),

        # Test 3: Two core scopes
        (["advertising::campaign_management", "advertising::account_management"], "Core scopes only"),

        # Test 4: Add reporting
        (["advertising::campaign_management", "advertising::account_management", "advertising::reporting"], "Core + Reporting"),

        # Test 5: Add DSP
        (["advertising::campaign_management", "advertising::account_management", "advertising::dsp_campaigns"], "Core + DSP"),

        # Test 6: All scopes
        (["advertising::campaign_management", "advertising::account_management", "advertising::dsp_campaigns", "advertising::reporting"], "All scopes"),

        # Test 7: DSP only (to test if DSP scope is the issue)
        (["advertising::dsp_campaigns"], "DSP only"),
    ]

    urls = []
    for scopes, description in test_cases:
        url = test_scope(scopes, description)
        urls.append((description, url))

    print("\n" + "=" * 60)
    print("SUMMARY - Test these URLs manually:")
    print("=" * 60)

    for i, (desc, url) in enumerate(urls, 1):
        print(f"\n{i}. {desc}")
        print(f"   {url[:100]}...")
        print(f"   Copy full URL from above")

    print("\n" + "=" * 60)
    print("WHAT TO LOOK FOR:")
    print("=" * 60)
    print("✅ SUCCESS: You reach Amazon's login page")
    print("❌ FAILURE: You get a 400 error page immediately")
    print("\nThe first failing test will identify the problematic scope.")

if __name__ == "__main__":
    main()