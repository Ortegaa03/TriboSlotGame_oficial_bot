import asyncio
from web3 import Web3
from eth_account import Account
from config import RPC_URL, PRIVATE_KEY, CONTRACT_ADDRESS, CONTRACT_ABI, CHAIN_ID, PRIZES

# Initialize Web3
w3 = None
account = None
contract = None

def init_web3():
    """Initialize Web3 connection"""
    global w3, account, contract
    
    if not RPC_URL or not PRIVATE_KEY or not CONTRACT_ADDRESS:
        print("[v0] Warning: Web3 not configured. Set RPC_URL, PRIVATE_KEY, and CONTRACT_ADDRESS environment variables.")
        return False
    
    try:
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        account = Account.from_key(PRIVATE_KEY)
        contract = w3.eth.contract(
            address=w3.to_checksum_address(CONTRACT_ADDRESS),
            abi=CONTRACT_ABI
        )
        print(f"[v0] Web3 initialized. Bot wallet: {account.address}")
        print(f"[v0] Contract address: {CONTRACT_ADDRESS}")
        print(f"[v0] Chain ID: {CHAIN_ID}")
        return True
    except Exception as e:
        print(f"[v0] Error initializing Web3: {e}")
        import traceback
        print(f"[v0] Traceback: {traceback.format_exc()}")
        return False

def validate_address(addr):
    """Validate Ethereum address"""
    if not w3:
        return None
    try:
        return w3.to_checksum_address(addr)
    except:
        return None

def get_prize_by_name(prize_name):
    """Get prize configuration by name"""
    for prize in PRIZES:
        if prize['name'] == prize_name:
            return prize
    return None

async def process_claim(prize_name, wallet_address, bot, chat_id):
    """
    Process blockchain claim for a prize
    Returns: (success: bool, message: str, tx_hash: str or None)
    """
    print(f"[v0] === Starting process_claim ===")
    print(f"[v0] Prize: {prize_name}")
    print(f"[v0] Wallet: {wallet_address}")
    print(f"[v0] Chat ID: {chat_id}")
    
    if not w3 or not account or not contract:
        print(f"[v0] Web3 not initialized: w3={w3 is not None}, account={account is not None}, contract={contract is not None}")
        return False, "Web3 not configured. Please contact admin.", None
    
    prize = get_prize_by_name(prize_name)
    if not prize:
        print(f"[v0] Prize not found: {prize_name}")
        return False, "Invalid prize.", None
    
    print(f"[v0] Prize found: {prize}")
    
    wallet = validate_address(wallet_address)
    if not wallet:
        print(f"[v0] Invalid wallet address: {wallet_address}")
        return False, "Invalid wallet address.", None
    
    print(f"[v0] Wallet validated: {wallet}")
    
    try:
        token_address = w3.to_checksum_address(prize['token'])
        amount = int(prize['amount'])
        
        print(f"[v0] Token address: {token_address}")
        print(f"[v0] Amount: {amount}")
        
        # Check bot balance
        eth_balance = w3.eth.get_balance(account.address)
        print(f"[v0] Bot ETH balance: {w3.from_wei(eth_balance, 'ether')} ETH")
        
        if eth_balance == 0:
            return False, "Bot has no ETH for gas. Please contact admin to fund the bot wallet.", None
        
        # Check contract token balance
        try:
            contract_balance = contract.functions.getBalance(token_address).call()
            print(f"[v0] Contract token balance: {contract_balance}")
            
            if contract_balance < amount:
                return False, f"Insufficient token balance in contract. Please contact admin.", None
        except Exception as e:
            print(f"[v0] Error checking contract balance: {e}")
            # Continue anyway, let the transaction fail if needed
        
        nonce = w3.eth.get_transaction_count(account.address)
        gas_price = w3.eth.gas_price
        
        print(f"[v0] Nonce: {nonce}, Gas price: {w3.from_wei(gas_price, 'gwei')} gwei")
        
        # Build transaction function call
        func = contract.functions.claim(token_address, amount, wallet)
        
        # Estimate gas
        try:
            gas_est = func.estimate_gas({'from': account.address})
            print(f"[v0] Gas estimate: {gas_est}")
        except Exception as e:
            print(f"[v0] Gas estimation failed: {e}")
            import traceback
            print(f"[v0] Traceback: {traceback.format_exc()}")
            return False, f"Transaction would fail: {str(e)}", None
        
        tx_cost = gas_est * gas_price
        
        print(f"[v0] Transaction cost: {w3.from_wei(tx_cost, 'ether')} ETH")
        
        if eth_balance < tx_cost:
            return False, f"Insufficient ETH for gas. Bot needs {w3.from_wei(tx_cost, 'ether')} ETH but has {w3.from_wei(eth_balance, 'ether')} ETH.", None
        
        # Build transaction
        print(f"[v0] Building transaction...")
        
        tx = func.build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': int(gas_est * 1.2),
            'gasPrice': gas_price,
            'chainId': CHAIN_ID
        })
        
        print(f"[v0] Transaction built successfully")
        print(f"[v0] Transaction details: {tx}")
        
        # Sign transaction
        print(f"[v0] Signing transaction...")
        signed_tx = account.sign_transaction(tx)
        print(f"[v0] Transaction signed successfully")
        
        # Send raw transaction
        print(f"[v0] Sending transaction...")
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"[v0] Transaction sent! Hash: {tx_hash.hex()}")
        
        # Wait for receipt
        print(f"[v0] Waiting for transaction receipt...")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        print(f"[v0] Transaction receipt received")
        print(f"[v0] Transaction status: {receipt['status']}")
        print(f"[v0] Gas used: {receipt['gasUsed']}")
        
        if receipt['status'] == 1:
            print(f"[v0] Transaction successful!")
            return True, f"Claim successful! Sent {prize['name']} to your wallet.", tx_hash.hex()
        else:
            print(f"[v0] Transaction failed!")
            return False, f"Transaction failed. TxHash: {tx_hash.hex()}", tx_hash.hex()
            
    except Exception as e:
        error_msg = str(e)
        print(f"[v0] Error processing claim: {error_msg}")
        import traceback
        print(f"[v0] Full traceback:")
        print(traceback.format_exc())
        return False, f"Error processing claim: {error_msg}", None
