import os
import time
import random
from web3 import Web3
from eth_hash.auto import keccak

# --- بخش ۱: تنظیمات اصلی ---
OG_SWAP_AMOUNT = 0.01
DEX_ROUTER_ADDRESS = "0x171931f5670037173B9db13ab83186adAb350cF2"
EUCLID_TOKEN_ADDRESS = "0x20329026df239A273F25F4383447342171A40673"
W_OG_ADDRESS = "0xEd28A457a553065123A36e63785Fe6a15286594C" 
FEE_TIER = 3000

# --- بخش ۲: اطلاعات فنی ---
RPC_URL = "https://evmrpc-testnet.0g.ai"
CHAIN_ID = 16601
EXPLORER_URL_TX_FORMAT = "https://chainscan-galileo.0g.ai/tx/{}"
MINIMAL_ERC20_ABI = '''
[
    {"constant": true, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"constant": false, "inputs": [{"name": "_spender", "type": "address"},{"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "success", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
    {"constant": true, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "stateMutability": "view", "type": "function"}
]
'''
DEX_ROUTER_ABI = '''
[
  {"inputs":[{"components":[{"internalType":"address","name":"tokenIn","type":"address"},{"internalType":"address","name":"tokenOut","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMinimum","type":"uint256"},{"internalType":"uint160","name":"sqrtPriceLimitX96","type":"uint160"}],"internalType":"struct ISwapRouter.ExactInputSingleParams","name":"params","type":"tuple"}],"name":"exactInputSingle","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"payable","type":"function"}
]
'''

def perform_round_trip_swap():
    print("--- 🤖 شروع به کار ربات سواپ رفت و برگشتی (نسخه پایدار) ---")

    # ۱. اتصال به شبکه و آماده‌سازی
    try:
        private_key = os.environ.get('MY_PRIVATE_KEY')
        if not private_key: raise ValueError("کلید خصوصی یافت نشد.")
        if not private_key.startswith("0x"): private_key = "0x" + private_key

        w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={'timeout': 120.0}))
        account = w3.eth.account.from_key(private_key)
        
        dex_contract = w3.eth.contract(address=Web3.to_checksum_address(DEX_ROUTER_ADDRESS), abi=DEX_ROUTER_ABI)
        target_token_contract = w3.eth.contract(address=Web3.to_checksum_address(EUCLID_TOKEN_ADDRESS), abi=MINIMAL_ERC20_ABI)
        
        print(f"✅ متصل شد. آدرس: {account.address}")
        print(f" موجودی اولیه: {w3.from_wei(w3.eth.get_balance(account.address), 'ether'):.6f} OG")

    except Exception as e:
        print(f"🚨 خطا در مرحله آماده‌سازی: {e}")
        return

    # ۲. سواپ اول: 0G به EUCLID
    amount_in_wei = w3.to_wei(OG_SWAP_AMOUNT, 'ether')
    amount_received = 0
    
    print(f"\\n--- شروع سواپ ۱: {OG_SWAP_AMOUNT} OG به EUCLID ---")
    try:
        params = (
            Web3.to_checksum_address(W_OG_ADDRESS),
            Web3.to_checksum_address(EUCLID_TOKEN_ADDRESS), # <<-- اصلاح شد
            FEE_TIER,
            account.address,
            int(time.time()) + 600,
            amount_in_wei,
            0,
            0
        )
        nonce = w3.eth.get_transaction_count(account.address)
        tx = dex_contract.functions.exactInputSingle(params).build_transaction({
            'from': account.address,
            'value': amount_in_wei,
            'gasPrice': w3.eth.gas_price,
            'nonce': nonce,
            'chainId': CHAIN_ID
        })
        tx['gas'] = w3.eth.estimate_gas(tx)

        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"  تراکنش سواپ ۱ ارسال شد: {tx_hash.hex()}")
        
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        if receipt.status != 1: raise Exception(f"تراکنش سواپ ۱ ناموفق بود (reverted). رسید: {receipt}")
        
        print("  ✅ سواپ ۱ با موفقیت انجام شد.")

        TRANSFER_TOPIC = keccak(text="Transfer(address,address,uint256)").hex()
        for log in receipt['logs']:
            if len(log['topics']) > 2 and log['topics'][0].hex() == TRANSFER_TOPIC and Web3.to_checksum_address('0x' + log['topics'][2].hex()[-40:]) == account.address:
                amount_received = int(log['data'].hex(), 16)
                break
        
        if amount_received <= 0: raise Exception("هیچ توکن EUCLIDی دریافت نشد یا لاگ آن پیدا نشد.")
        
        token_decimals = target_token_contract.functions.decimals().call()
        print(f"  مقدار دقیق {amount_received / (10**token_decimals):.6f} EUCLID دریافت شد.")

    except Exception as e:
        print(f"🚨 خطا در سواپ ۱: {e}")
        return

    # ۳. انتظار به مدت ۱۰ دقیقه
    print("\\n--- انتظار به مدت ۱۰ دقیقه... ---")
    time.sleep(600)

    # ۴. سواپ دوم: EUCLID به 0G
    print(f"\\n--- شروع سواپ ۲: {amount_received / (10**token_decimals):.6f} EUCLID به OG ---")
    try:
        # مرحله الف: Approve
        nonce = w3.eth.get_transaction_count(account.address)
        approve_tx = target_token_contract.functions.approve(dex_contract.address, amount_received).build_transaction({
            'from': account.address, 'nonce': nonce, 'gasPrice': w3.eth.gas_price, 'chainId': CHAIN_ID
        })
        approve_tx['gas'] = w3.eth.estimate_gas(approve_tx)

        signed_approve_tx = account.sign_transaction(approve_tx)
        approve_tx_hash = w3.eth.send_raw_transaction(signed_approve_tx.raw_transaction)
        print(f"  تراکنش Approve ارسال شد: {approve_tx_hash.hex()}")
        w3.eth.wait_for_transaction_receipt(approve_tx_hash, timeout=300)
        print("  ✅ توکن با موفقیت Approve شد. ۱۰ ثانیه تاخیر...")
        time.sleep(10)
        
        # مرحله ب: خود سواپ
        params_reverse = (
            Web3.to_checksum_address(EUCLID_TOKEN_ADDRESS), # <<-- اصلاح شد
            Web3.to_checksum_address(W_OG_ADDRESS),
            FEE_TIER,
            account.address,
            int(time.time()) + 600,
            amount_received,
            0,
            0
        )
        nonce = w3.eth.get_transaction_count(account.address)
        reverse_tx = dex_contract.functions.exactInputSingle(params_reverse).build_transaction({
            'from': account.address, 'gasPrice': w3.eth.gas_price, 'nonce': nonce, 'chainId': CHAIN_ID
        })
        reverse_tx['gas'] = w3.eth.estimate_gas(reverse_tx)

        signed_reverse_tx = account.sign_transaction(reverse_tx)
        reverse_tx_hash = w3.eth.send_raw_transaction(signed_reverse_tx.raw_transaction)
        print(f"  تراکنش سواپ ۲ ارسال شد: {reverse_tx_hash.hex()}")
        receipt_reverse = w3.eth.wait_for_transaction_receipt(reverse_tx_hash, timeout=300)
        if receipt_reverse.status != 1: raise Exception(f"تراکنش سواپ ۲ ناموفق بود (reverted). رسید: {receipt_reverse}")

        print("  ✅ سواپ ۲ (معکوس) با موفقیت انجام شد.")

    except Exception as e:
        print(f"🚨 خطا در سواپ ۲: {e}")
        return
    
    print(f"\\n--- ✅ روتین سواپ رفت و برگشتی با موفقیت کامل شد. ---")


if __name__ == "__main__":
    perform_round_trip_swap()
