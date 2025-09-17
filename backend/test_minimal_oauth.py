#!/usr/bin/env python3
"""
Test OAuth with minimal scopes to isolate the issue
"""
import webbrowser
from urllib.parse import urlencode

def test_minimal_oauth():
    """Test with minimal scope to see if it's a scope permission issue"""

    # Test configurations
    tests = [
        {
            "name": "Single scope - campaign_management",
            "scope": "advertising::campaign_management"
        },
        {
            "name": "Two critical scopes",
            "scope": "advertising::campaign_management advertising::account_management"
        },
        {
            "name": "All scopes",
            "scope": "advertising::campaign_management advertising::account_management advertising::dsp_campaigns advertising::reporting"
        }
    ]

    base_url = "https://www.amazon.com/ap/oa"
    client_id = "amzn1.application-oa2-client.cf1789da23f74ee489e2373e424726af"
    redirect_uri = "http://localhost:8000/api/v1/auth/amazon/callback"

    print("=" * 80)
    print("Testing Amazon OAuth with Different Scope Configurations")
    print("=" * 80)

    for i, test in enumerate(tests, 1):
        print(f"\n📝 Test {i}: {test['name']}")
        print(f"   Scope: {test['scope']}")

        params = {
            "client_id": client_id,
            "scope": test['scope'],
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": f"test_{i}"
        }

        test_url = f"{base_url}?{urlencode(params)}"

        print(f"\n   Generated URL:")
        print(f"   {test_url}\n")

        response = input(f"   Press Enter to open Test {i} in browser (or 's' to skip): ")
        if response.lower() != 's':
            webbrowser.open(test_url)
            result = input("   Did it work? (y/n/error message): ")
            print(f"   Result: {result}")

    print("\n" + "=" * 80)
    print("📌 Diagnosis:")
    print("  - If only single scope works: App needs approval for additional scopes")
    print("  - If none work: Redirect URI mismatch or client ID issue")
    print("  - If all work: Original implementation had a different issue")
    print("=" * 80)

if __name__ == "__main__":
    test_minimal_oauth()