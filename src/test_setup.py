"""Quick test of API monitor setup"""

import sys
import os

def test_imports():
    """Test package imports"""
    print("Testing package imports...")
    try:
        import requests
        import dotenv
        from web3 import Web3
        print("  ✓ All packages installed\n")
        return True
    except ImportError as e:
        print(f"  ✗ Missing package: {e}\n")
        return False

def test_modules():
    """Test local modules"""
    print("Testing local modules...")
    try:
        import src.config as config
        import src.utils as utils
        print("  ✓ Local modules loaded")
        print(f"    Payment methods: {', '.join(config.ALLOWED_PAYMENT_METHODS)}")
        print(f"    Currencies: {', '.join(config.ALLOWED_CURRENCIES)}")
        print()
        return True
    except Exception as e:
        print(f"  ✗ Module error: {e}\n")
        return False

def test_api():
    """Test API connection"""
    print("Testing Peerlytics API...")
    try:
        import requests
        from src.config import PEERLYTICS_API_URL
        
        response = requests.get(PEERLYTICS_API_URL, timeout=10)
        data = response.json()
        
        deposits = data.get('deposits', {})
        top_deposits = data.get('topDeposits', [])
        
        print("  ✓ API connected successfully")
        print(f"    Available liquidity: ${deposits.get('availableLiquidity', 0):,.2f}")
        print(f"    Active deposits: {deposits.get('active', 0):,}")
        print(f"    Top deposits returned: {len(top_deposits)}")
        print()
        return True
    except Exception as e:
        print(f"  ✗ API error: {e}\n")
        return False

def test_web3():
    """Test Web3 connection"""
    print("Testing Web3 connection...")
    try:
        from web3 import Web3
        from src.config import RPC_URL
        
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        
        if w3.is_connected():
            block = w3.eth.block_number
            print("  ✓ Web3 connected")
            print(f"    Current block: {block:,}")
            print()
            return True
        else:
            print("  ✗ Web3 not connected\n")
            return False
    except Exception as e:
        print(f"  ✗ Web3 error: {e}\n")
        return False

def main():
    print("\n" + "="*60)
    print("ZKP2P API Monitor - Setup Test")
    print("="*60 + "\n")
    
    tests = [
        ("Package Imports", test_imports),
        ("Local Modules", test_modules),
        ("Peerlytics API", test_api),
        ("Web3 RPC", test_web3)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"Test '{name}' crashed: {e}\n")
            results.append((name, False))
    
    # Summary
    print("="*60)
    print("Test Summary")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! Ready to run.")
        print("\nRun: python3 monitor.py\n")
        return 0
    else:
        print("\n✗ Some tests failed. Fix issues before running.\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())