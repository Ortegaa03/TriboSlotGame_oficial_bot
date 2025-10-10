"""
Test script to simulate the claim process
This helps verify the claim functionality works correctly
"""
import asyncio
from web3_payment import init_web3, process_claim, validate_address, w3, account, contract
from config import PRIZES, CONTRACT_ADDRESS

class MockBot:
    """Mock bot for testing"""
    async def send_message(self, chat_id, text, parse_mode=None):
        print(f"\n[MOCK BOT] Message to chat {chat_id}:")
        print(f"{text}\n")

async def test_claim():
    """Test the claim process"""
    print("=" * 60)
    print("TESTING CLAIM FUNCTIONALITY")
    print("=" * 60)
    
    # Initialize Web3
    print("\n1. Initializing Web3...")
    if not init_web3():
        print("❌ Failed to initialize Web3. Check your environment variables:")
        print("   - RPC_URL")
        print("   - PRIVATE_KEY")
        print("   - CONTRACT_ADDRESS")
        return
    
    print("✅ Web3 initialized successfully")
    
    # Show connection info
    from web3_payment import w3, account, contract
    print(f"\n   Bot Wallet: {account.address}")
    print(f"   Contract: {CONTRACT_ADDRESS}")
    print(f"   Connected: {w3.is_connected()}")
    
    # Check bot balance
    eth_balance = w3.eth.get_balance(account.address)
    print(f"   Bot ETH Balance: {w3.from_wei(eth_balance, 'ether')} ETH")
    
    # Test wallet validation
    print("\n2. Testing wallet validation...")
    test_wallets = [
        "0x1234567890123456789012345678901234567890",  # Valid format
        "invalid_wallet",  # Invalid
        "0x123",  # Too short
    ]
    
    for wallet in test_wallets:
        result = validate_address(wallet)
        if result:
            print(f"   ✅ Valid: {wallet} -> {result}")
        else:
            print(f"   ❌ Invalid: {wallet}")
    
    # Test prize configuration
    print("\n3. Testing prize configuration...")
    for prize in PRIZES:
        token_addr = w3.to_checksum_address(prize['token'])
        print(f"   - {prize['name']}: {prize['symbol']}")
        print(f"     Token: {token_addr}")
        print(f"     Amount: {prize['amount']}")
        
        # Check contract balance for this token
        try:
            balance = contract.functions.getBalance(token_addr).call()
            print(f"     Contract Balance: {balance}")
        except Exception as e:
            print(f"     ⚠️ Error checking balance: {e}")
    
    # Test claim process
    print("\n4. Testing claim process...")
    print("   ⚠️ WARNING: This will attempt a REAL blockchain transaction!")
    
    # Get test wallet from user
    test_wallet = input("\n   Enter wallet address to test (or press Enter to skip): ").strip()
    
    if not test_wallet:
        print("\n   ⏭️  Skipped real transaction test")
        print("\n✅ All tests completed!")
        return
    
    # Validate wallet
    test_wallet = validate_address(test_wallet)
    if not test_wallet:
        print("   ❌ Invalid wallet address!")
        return
    
    # Select prize
    print("\n   Available prizes:")
    for i, prize in enumerate(PRIZES):
        print(f"   {i+1}. {prize['name']}")
    
    prize_idx = input("\n   Select prize number (1-5): ").strip()
    try:
        prize_idx = int(prize_idx) - 1
        if prize_idx < 0 or prize_idx >= len(PRIZES):
            raise ValueError()
        test_prize = PRIZES[prize_idx]['name']
    except:
        print("   ❌ Invalid prize selection!")
        return
    
    print(f"\n   Prize: {test_prize}")
    print(f"   Wallet: {test_wallet}")
    
    confirm = input("\n   Proceed with REAL transaction? (yes/no): ")
    
    if confirm.lower() != 'yes':
        print("\n   ⏭️  Transaction cancelled")
        print("\n✅ All tests completed!")
        return
    
    print("\n   🔄 Processing claim...")
    
    mock_bot = MockBot()
    success, message, tx_hash = await process_claim(
        test_prize,
        test_wallet,
        mock_bot,
        123456789
    )
    
    print("\n" + "=" * 60)
    print("CLAIM RESULT:")
    print("=" * 60)
    print(f"Success: {success}")
    print(f"Message: {message}")
    if tx_hash:
        print(f"TX Hash: {tx_hash}")
        print(f"Explorer: https://worldchain-mainnet.explorer.alchemy.com/tx/{tx_hash}")
    print("=" * 60)
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    print("\n🧪 Claim Functionality Test Script\n")
    asyncio.run(test_claim())
