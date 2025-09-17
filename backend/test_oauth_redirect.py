#!/usr/bin/env python3
"""
Test script to verify OAuth redirect URI requirements for Amazon Advertising API
"""
import requests
from urllib.parse import urlencode

def test_oauth_redirect():
    """Test different redirect URI configurations"""

    base_url = "https://www.amazon.com/ap/oa"
    client_id = "amzn1.application-oa2-client.cf1789da23f74ee489e2373e424726af"
    scope = "advertising::campaign_management advertising::account_management"

    # Test different redirect URIs
    test_cases = [
        {
            "name": "HTTP localhost",
            "redirect_uri": "http://localhost:8000/api/v1/auth/amazon/callback",
            "expected": "May fail if Amazon requires HTTPS"
        },
        {
            "name": "HTTPS localhost",
            "redirect_uri": "https://localhost:8000/api/v1/auth/amazon/callback",
            "expected": "Better for production but may need SSL cert"
        },
        {
            "name": "HTTP 127.0.0.1",
            "redirect_uri": "http://127.0.0.1:8000/api/v1/auth/amazon/callback",
            "expected": "Sometimes works better than localhost"
        }
    ]

    print("=" * 80)
    print("Testing Amazon OAuth Redirect URI Configurations")
    print("=" * 80)

    for test in test_cases:
        print(f"\n📝 Test: {test['name']}")
        print(f"   Redirect URI: {test['redirect_uri']}")
        print(f"   Note: {test['expected']}")

        params = {
            "client_id": client_id,
            "scope": scope,
            "response_type": "code",
            "redirect_uri": test['redirect_uri'],
            "state": "test123"
        }

        test_url = f"{base_url}?{urlencode(params)}"

        # Test with HEAD request to check if URL is valid
        try:
            response = requests.head(test_url, allow_redirects=False, timeout=5)
            print(f"   Response Status: {response.status_code}")

            if response.status_code == 302:
                print("   ✅ Redirect detected (expected for OAuth)")
                if 'Location' in response.headers:
                    location = response.headers['Location']
                    if 'error' in location:
                        print(f"   ❌ Error in redirect: {location[:100]}...")
                    else:
                        print(f"   ✅ Redirect location: {location[:100]}...")
            elif response.status_code == 400:
                print("   ❌ 400 Bad Request - Invalid parameters")
            elif response.status_code == 200:
                print("   ⚠️  200 OK - May show login page")
        except Exception as e:
            print(f"   ⚠️  Request failed: {str(e)}")

    print("\n" + "=" * 80)
    print("📌 Key Points for Amazon Advertising API OAuth:")
    print("  1. Redirect URI must EXACTLY match what's registered in your app")
    print("  2. Amazon typically allows http://localhost for development")
    print("  3. For production, use HTTPS with a proper domain")
    print("  4. Some developers report 127.0.0.1 works better than localhost")
    print("=" * 80)

if __name__ == "__main__":
    test_oauth_redirect()