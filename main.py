# ۱. وارد کردن (Import) ماژول‌های پایتون
import json
import time
import random
import os
from web3 import Web3
from web3.exceptions import ContractLogicError, TransactionNotFound, TimeExhausted, Web3RPCError
import requests
from eth_hash.auto import keccak
from eth_abi import encode

print("ماژول‌های ضروری پایتون import شدند.")

# --- بخش ۱: تنظیمات شبکه ---
print("--- بخش ۱: تعریف متغیرهای شبکه ---")
TARGET_NETWORK_NAME = "0G Galileo Testnet"
RPC_URL = "https://evmrpc-testnet.0g.ai"
CHAIN_ID = 16601
EXPLORER_URL_TX_FORMAT = "https://chainscan-galileo.0g.ai/tx/{}"
print("--- پایان بخش ۱ ---\n")

# --- بخش ۲: خواندن کلید خصوصی ---
print("--- بخش ۲: خواندن کلید خصوصی ---")
SECRET_NAME_FOR_KEY = 'MY_PRIVATE_KEY'
USER_OWNER_PRIVATE_KEY = ""
try:
    USER_OWNER_PRIVATE_KEY = os.environ.get(SECRET_NAME_FOR_KEY)
    if not USER_OWNER_PRIVATE_KEY:
        raise ValueError(f"کلید خصوصی با نام '{SECRET_NAME_FOR_KEY}' در متغیرهای محیطی (GitHub Secrets) پیدا نشد.")
    if not USER_OWNER_PRIVATE_KEY.startswith("0x"):
        USER_OWNER_PRIVATE_KEY = "0x" + USER_OWNER_PRIVATE_KEY
    print(f"کلید خصوصی با موفقیت از GitHub Secret '{SECRET_NAME_FOR_KEY}' خوانده شد.")
except Exception as e:
    print(f"خطا در خواندن کلید خصوصی: {e}")
    raise
print("--- پایان بخش ۲ ---\n")


# --- بخش ۳: اتصال به شبکه و آماده‌سازی حساب ---
print("--- بخش ۳: اتصال Web3 و آماده‌سازی حساب ---")
w3 = None
user_owner_account = None
try:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }
    w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={'timeout': 60.0, 'headers': headers}))
    
    if not w3.is_connected():
        raise ConnectionError(f"عدم امکان اتصال به RPC URL: {RPC_URL}")
    user_owner_account = w3.eth.account.from_key(USER_OWNER_PRIVATE_KEY)
    print(f"✅ با موفقیت به شبکه {TARGET_NETWORK_NAME} (Chain ID: {w3.eth.chain_id}) متصل شد.")
    print(f"  آدرس حساب شما: {user_owner_account.address}")
    balance_wei = w3.eth.get_balance(user_owner_account.address)
    balance_native = w3.from_wei(balance_wei, 'ether')
    print(f"  موجودی اولیه حساب: {balance_native} توکن بومی شبکه (OG)")
except Exception as e:
    print(f"🚨 خطا در اتصال Web3 یا آماده‌سازی حساب: {e}")
    raise
print("--- پایان بخش ۳ ---\n")


# --- بخش ۴: بارگذاری اطلاعات قراردادها ---
print("--- بخش ۴: بارگذاری اطلاعات قراردادها ---")
DEPLOYMENT_INFO_FILE = 'deployment_output.json'
interact_proxy_instance = None
try:
    with open(DEPLOYMENT_INFO_FILE, 'r') as f:
        deployed_info = json.load(f)
    INTERACT_PROXY_ADDRESS_STR = deployed_info.get('InteractFeeProxy', {}).get('address')
    INTERACT_PROXY_ABI = deployed_info.get('InteractFeeProxy', {}).get('abi')
    if not INTERACT_PROXY_ADDRESS_STR or not INTERACT_PROXY_ABI:
        raise ValueError("آدرس یا ABI برای 'InteractFeeProxy' در فایل deployment_output.json یافت نشد.")
    INTERACT_PROXY_ADDRESS = w3.to_checksum_address(INTERACT_PROXY_ADDRESS_STR)
    interact_proxy_instance = w3.eth.contract(address=INTERACT_PROXY_ADDRESS, abi=INTERACT_PROXY_ABI)
    print(f"  اطلاعات قرارداد InteractFeeProxy با موفقیت از '{DEPLOYMENT_INFO_FILE}' بارگذاری شد.")
except Exception as e_load:
    print(f"  🚨 خطا در بارگذاری فایل '{DEPLOYMENT_INFO_FILE}': {e_load}")
    raise

USDT_TOKEN_ADDRESS_STR = "0x3eC8A8705bE1D5ca90066b37ba62c4183B024ebf"
ETH_TOKEN_ADDRESS_STR = "0x0fe9b43625fa7edd663adcec0728dd635e4abf7c"
BTC_TOKEN_ADDRESS_STR = "0x36f6414FF1df609214dDAbA71c84f18bcf00F67d"
MINIMAL_ERC20_ABI_STR = '''
[
    {"constant": true, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"constant": false, "inputs": [{"name": "_spender", "type": "address"},{"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "success", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
    {"constant": true, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "stateMutability": "view", "type": "function"}
]
'''
MINIMAL_ERC20_ABI = json.loads(MINIMAL_ERC20_ABI_STR)
USDT_TOKEN_ADDRESS = w3.to_checksum_address(USDT_TOKEN_ADDRESS_STR)
usdt_contract = w3.eth.contract(address=USDT_TOKEN_ADDRESS, abi=MINIMAL_ERC20_ABI)
ETH_TOKEN_ADDRESS = w3.to_checksum_address(ETH_TOKEN_ADDRESS_STR)
eth_token_contract = w3.eth.contract(address=ETH_TOKEN_ADDRESS, abi=MINIMAL_ERC20_ABI)
BTC_TOKEN_ADDRESS = w3.to_checksum_address(BTC_TOKEN_ADDRESS_STR)
btc_token_contract = w3.eth.contract(address=BTC_TOKEN_ADDRESS, abi=MINIMAL_ERC20_ABI)

DEX1_ROUTER_ADDRESS_STR = "0xb95B5953FF8ee5D5d9818CdbEfE363ff2191318c"
UPDATED_MINIMAL_DEX_ROUTER_ABI_STR = '''
[
  {"name": "exactInputSingle", "type": "function", "stateMutability": "payable", "inputs": [{"name": "params", "type": "tuple", "components": [{"name": "tokenIn", "type": "address"}, {"name": "tokenOut", "type": "address"}, {"name": "fee", "type": "uint24"}, {"name": "recipient", "type": "address"}, {"name": "deadline", "type": "uint256"}, {"name": "amountIn", "type": "uint256"}, {"name": "amountOutMinimum", "type": "uint256"}, {"name": "sqrtPriceLimitX96", "type": "uint160"}]}], "outputs": [{"name": "amountOut", "type": "uint256"}]},
  {"name": "exactInput", "type": "function", "stateMutability": "payable", "inputs": [{"name": "params", "type": "tuple", "components": [{"name": "path", "type": "bytes"}, {"name": "recipient", "type": "address"}, {"name": "deadline", "type": "uint256"}, {"name": "amountIn", "type": "uint256"}, {"name": "amountOutMinimum", "type": "uint256"}]}], "outputs": [{"name": "amountOut", "type": "uint256"}]}
]
'''
UPDATED_MINIMAL_DEX_ROUTER_ABI = json.loads(UPDATED_MINIMAL_DEX_ROUTER_ABI_STR)
DEX1_ROUTER_ADDRESS = w3.to_checksum_address(DEX1_ROUTER_ADDRESS_STR)
dex1_router_contract_updated = w3.eth.contract(address=DEX1_ROUTER_ADDRESS, abi=UPDATED_MINIMAL_DEX_ROUTER_ABI)
print("--- پایان بخش ۴ ---\n")


# --- بخش ۵: توابع کمکی ---
def send_signed_transaction_with_retry(w3_instance, signed_tx, action_name="تراکنش", timeout_receipt=300, max_rpc_retries=3, rpc_retry_delay_sec=5):
    tx_hash = None
    try:
        tx_hash = w3_instance.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"  {action_name}: تراکنش ارسال شد. هش: {tx_hash.hex()}")
        print(f"  لینک اکسپلورر: {EXPLORER_URL_TX_FORMAT.format(tx_hash.hex())}")
    except Exception as e:
        print(f"    خطا در ارسال تراکنش '{action_name}': {e}")
        return None
    for attempt_receipt in range(max_rpc_retries):
        try:
            print(f"  {action_name}: تلاش {attempt_receipt + 1}/{max_rpc_retries} برای دریافت رسید...")
            tx_receipt = w3_instance.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout_receipt)
            if tx_receipt.status == 1:
                print(f"  {action_name} با موفقیت تایید شد! بلاک: {tx_receipt.blockNumber}")
            else:
                print(f"  {action_name} ناموفق بود (reverted).")
            return tx_receipt
        except (TransactionNotFound, TimeExhausted):
            print(f"  تراکنش پس از {timeout_receipt} ثانیه یافت نشد (تلاش {attempt_receipt + 1}).")
            if attempt_receipt < max_rpc_retries - 1:
                time.sleep(rpc_retry_delay_sec)
        except Exception as e_other_receipt:
            print(f"    خطای پیش‌بینی نشده در دریافت رسید: {e_other_receipt}")
            return None
    return None

def approve_erc20_token(w3_instance, token_contract, spender_address, amount_wei, account, default_gas_approve=100000):
    for attempt in range(3):
        try:
            action_name = f"تایید توکن {token_contract.address[:10]}"
            nonce = w3_instance.eth.get_transaction_count(account.address)
            gas_price = w3_instance.eth.gas_price
            if attempt > 0:
                gas_price = int(gas_price * (1.2**attempt))
                print(f"    افزایش قیمت گاز برای تلاش مجدد: {gas_price}")
            approve_tx_built = token_contract.functions.approve(spender_address, amount_wei).build_transaction({
                'from': account.address, 'nonce': nonce, 'gasPrice': gas_price, 'chainId': CHAIN_ID
            })
            try:
                estimated_gas = w3_instance.eth.estimate_gas(approve_tx_built)
                approve_tx_built['gas'] = int(estimated_gas * 1.2)
            except Exception as e:
                print(f"      خطا در تخمین گاز approve: {e}. استفاده از مقدار پیش فرض.")
                approve_tx_built['gas'] = default_gas_approve
            signed_approve_tx = account.sign_transaction(approve_tx_built)
            receipt = send_signed_transaction_with_retry(w3_instance, signed_approve_tx, action_name)
            if receipt and receipt.status == 1:
                return True
            else:
                print(f"    تلاش {attempt + 1} برای approve ناموفق بود. تلاش مجدد...")
                time.sleep(random.uniform(2, 5))
        except Exception as e:
            print(f"خطای کلی در approve (تلاش {attempt + 1}): {e}")
            time.sleep(random.uniform(2, 5))
    return False

def get_token_balance(w3_instance, token_contract, account_address, token_symbol="توکن"):
    try:
        balance_wei = token_contract.functions.balanceOf(account_address).call()
        decimals = token_contract.functions.decimals().call()
        readable_balance = balance_wei / (10**decimals)
        print(f"  موجودی {token_symbol}: {readable_balance:.6f}")
        return balance_wei
    except Exception:
        return 0

def build_uniswap_v3_path(token_addresses_checksum, fee_tiers_uint24):
    path_bytes = b''
    path_bytes += bytes.fromhex(token_addresses_checksum[0][2:])
    for i in range(len(fee_tiers_uint24)):
        path_bytes += fee_tiers_uint24[i].to_bytes(3, byteorder='big')
        path_bytes += bytes.fromhex(token_addresses_checksum[i+1][2:])
    return path_bytes

INTERACT_FEE_WEI = w3.to_wei(0.001, 'ether')

def attempt_owner_withdrawal(w3_instance, proxy_contract_obj, owner_account_obj, chain_id_val, default_gas_wd=100000):
    action_name = "برداشت کارمزد"
    print(f"\\n    --- {action_name} ---")
    try:
        proxy_balance_wei = w3_instance.eth.get_balance(proxy_contract_obj.address)
        if proxy_balance_wei == 0:
            print("      موجودی برای برداشت وجود ندارد.")
            return False
        nonce = w3_instance.eth.get_transaction_count(owner_account_obj.address)
        gas_price = w3.eth.gas_price
        withdraw_tx_built = proxy_contract_obj.functions.withdrawEther().build_transaction({
            'from': owner_account_obj.address, 'nonce': nonce,
            'chainId': chain_id_val, 'gasPrice': gas_price, 'value': 0
        })
        try:
            estimated_gas = w3_instance.eth.estimate_gas(withdraw_tx_built)
            withdraw_tx_built['gas'] = int(estimated_gas * 1.2)
        except Exception:
            withdraw_tx_built['gas'] = default_gas_wd
        signed_tx_withdraw = owner_account_obj.sign_transaction(withdraw_tx_built)
        receipt = send_signed_transaction_with_retry(w3_instance, signed_tx_withdraw, action_name)
        return receipt is not None and receipt.status == 1
    except Exception as e:
        print(f"      خطای عمومی در برداشت کارمزد: {e}")
        return False

def call_interact_with_fee_function_final(max_overall_tries_for_this_call=5, default_gas_interaction=250000):
    action_name = "تعامل با InteractFeeProxy"
    for overall_attempt_num in range(max_overall_tries_for_this_call):
        print(f"\\n  {action_name}: تلاش کلی شماره {overall_attempt_num + 1}/{max_overall_tries_for_this_call}...")
        try:
            current_nonce = w3.eth.get_transaction_count(user_owner_account.address)
            gas_price = w3.eth.gas_price
            if overall_attempt_num > 0:
                gas_price = int(gas_price * (1.2**overall_attempt_num))
                print(f"    افزایش قیمت گاز برای تلاش مجدد: {gas_price}")
            interact_tx_built = interact_proxy_instance.functions.interactWithFee().build_transaction({
                'from': user_owner_account.address, 'chainId': CHAIN_ID, 
                'gasPrice': gas_price, 'nonce': current_nonce, 'value': INTERACT_FEE_WEI
            })
            try:
                estimated_gas = w3.eth.estimate_gas(interact_tx_built)
                interact_tx_built['gas'] = int(estimated_gas * 1.3)
            except Exception:
                interact_tx_built['gas'] = default_gas_interaction
            signed_tx_interact = user_owner_account.sign_transaction(interact_tx_built)
            receipt = send_signed_transaction_with_retry(w3, signed_tx_interact, action_name)
            if receipt and receipt.status == 1:
                print("  ✅ تراکنش تعامل موفق بود. در حال تلاش برای برداشت کارمزدهای انباشته شده...")
                time.sleep(random.uniform(3, 8))
                withdrawal_success = attempt_owner_withdrawal(w3, interact_proxy_instance, user_owner_account, CHAIN_ID)
                if withdrawal_success:
                    print("  ✅ برداشت کارمزد نیز با موفقیت انجام شد.")
                else:
                    print("  ⚠️ برداشت کارمزد انجام نشد (یا موجودی برای برداشت وجود نداشت).")
                return True
            print(f"    تلاش {overall_attempt_num + 1} ناموفق بود. تلاش مجدد...")
            time.sleep(random.uniform(2, 5))
        except Exception as e_fatal:
            print(f"    خطای بسیار پیش‌بینی نشده در تعامل: {e_fatal}")
            return False
    print(f"  --- {action_name} پس از تمام تلاش‌ها ناموفق بود. ---")
    return False

def _execute_single_swap_stage(token_in_contract_obj, token_out_contract_obj, token_in_addr, token_out_addr, amount_in_wei, swap_type, action_name, fee_tier=None, path=None, default_gas=700000):
    print(f"\\n    -- شروع مرحله سواپ: {action_name} --")
    if not approve_erc20_token(w3, token_in_contract_obj, dex1_router_contract_updated.address, amount_in_wei, user_owner_account):
        print("       تایید توکن ناموفق بود. لغو سواپ.")
        return 0
    time.sleep(random.uniform(3, 8))
    balance_out_before = get_token_balance(w3, token_out_contract_obj, user_owner_account.address)
    for attempt in range(3):
        try:
            nonce = w3.eth.get_transaction_count(user_owner_account.address)
            gas_price = w3.eth.gas_price
            if attempt > 0:
                gas_price = int(gas_price * (1.2**attempt))
                print(f"    افزایش قیمت گاز برای تلاش مجدد سواپ: {gas_price}")
            tx_params = {'from': user_owner_account.address, 'nonce': nonce, 'gasPrice': gas_price, 'chainId': CHAIN_ID, 'value': 0}
            if swap_type == "exactInputSingle":
                params = (token_in_addr, token_out_addr, fee_tier, user_owner_account.address, int(time.time()) + 900, amount_in_wei, 1, 0)
                swap_func = dex1_router_contract_updated.functions.exactInputSingle(params)
            else:
                params = (path, user_owner_account.address, int(time.time()) + 900, amount_in_wei, 1)
                swap_func = dex1_router_contract_updated.functions.exactInput(params)
            swap_tx_built = swap_func.build_transaction(tx_params)
            try:
                estimated_gas = w3.eth.estimate_gas(swap_tx_built)
                swap_tx_built['gas'] = int(estimated_gas * 1.5)
            except Exception:
                swap_tx_built['gas'] = default_gas
            signed_swap_tx = user_owner_account.sign_transaction(swap_tx_built)
            receipt = send_signed_transaction_with_retry(w3, signed_swap_tx, action_name)
            if receipt and receipt.status == 1:
                time.sleep(random.uniform(3, 8))
                balance_out_after = get_token_balance(w3, token_out_contract_obj, user_owner_account.address)
                return balance_out_after - balance_out_before
            else:
                print(f"    تلاش {attempt + 1} برای سواپ ناموفق بود.")
                time.sleep(random.uniform(2, 5))
        except Exception as e:
            print(f"خطای کلی در سواپ (تلاش {attempt + 1}): {e}")
            time.sleep(random.uniform(2, 5))
    return 0

def run_loop_level_1(num_interactions_lvl1=4):
    print(f"\\n========= شروع لوپ سطح ۱ (تعداد تعاملات: {num_interactions_lvl1}) ==========")
    successful_count = 0
    for i in range(num_interactions_lvl1):
        print(f"\\n  --- لوپ سطح ۱: تعامل شماره {i + 1}/{num_interactions_lvl1} ---")
        if call_interact_with_fee_function_final():
            successful_count += 1
        if i < num_interactions_lvl1 - 1:
            time.sleep(random.uniform(10, 30))
    print(f"\\n========= پایان لوپ سطح ۱: {successful_count} موفق از {num_interactions_lvl1} ==========")
    return True

def run_swap_loop(initial_usdt_amount_ether=100.0):
    print(f"\\n🔄===== شروع لوپ سواپ با {initial_usdt_amount_ether} USDT =====")
    amount_in_s1_wei = w3.to_wei(initial_usdt_amount_ether, 'ether')
    if get_token_balance(w3, usdt_contract, user_owner_account.address, "USDT") < amount_in_s1_wei:
        print("موجودی USDT کافی نیست.")
        return False
    received_eth_wei = _execute_single_swap_stage(usdt_contract, eth_token_contract, USDT_TOKEN_ADDRESS, ETH_TOKEN_ADDRESS, amount_in_s1_wei, "exactInputSingle", "سواپ ۱: USDT->ETH", fee_tier=100)
    if received_eth_wei <= 0: return False
    path_s2 = build_uniswap_v3_path([ETH_TOKEN_ADDRESS, USDT_TOKEN_ADDRESS, BTC_TOKEN_ADDRESS], [500, 3000])
    received_btc_wei = _execute_single_swap_stage(eth_token_contract, btc_token_contract, ETH_TOKEN_ADDRESS, BTC_TOKEN_ADDRESS, received_eth_wei, "exactInput", "سواپ ۲: ETH->BTC", path=path_s2)
    if received_btc_wei <= 0: return False
    received_final_usdt = _execute_single_swap_stage(btc_token_contract, usdt_contract, BTC_TOKEN_ADDRESS, USDT_TOKEN_ADDRESS, received_btc_wei, "exactInputSingle", "سواپ ۳: BTC->USDT", fee_tier=500)
    if received_final_usdt <= 0: return False
    print("\\n✅===== لوپ سواپ با موفقیت کامل انجام شد! =====")
    return True

def run_faucet_loop(faucet_gas_limit=100000):
    action_name = "تراکنش فاست USDT"
    print(f"\\n=== شروع {action_name} ===")
    for attempt in range(3):
        try:
            gas_price = w3.eth.gas_price
            if attempt > 0:
                gas_price = int(gas_price * (1.2**attempt))
                print(f"    افزایش قیمت گاز برای فاست: {gas_price}")
            tx_faucet_params = {
                'to': USDT_TOKEN_ADDRESS, 'value': 0, 'gas': faucet_gas_limit, 'gasPrice': gas_price,
                'nonce': w3.eth.get_transaction_count(user_owner_account.address), 'from': user_owner_account.address,
                'chainId': CHAIN_ID, 'data': "0x1249c58b"
            }
            signed_tx_faucet = user_owner_account.sign_transaction(tx_faucet_params)
            w3.eth.send_raw_transaction(signed_tx_faucet.raw_transaction)
            print(f"  {action_name}: تراکنش ارسال شد.")
            print("=== پایان لوپ فاست ===")
            return True
        except Exception as e:
            print(f"    خطا در ارسال تراکنش فاست (تلاش {attempt + 1}): {e}")
            time.sleep(random.uniform(2,5))
    print("=== پایان لوپ فاست (ناموفق) ===")
    return False

def run_loop_level_2(num_interactions_for_lvl1, min_usdt=100.0, max_usdt=1000.0):
    print("\\n🔄=============== شروع اجرای run_loop_level_2 ================")
    run_loop_level_1(num_interactions_for_lvl1)
    time.sleep(random.uniform(3, 8))
    random_usdt_amount = round(random.uniform(min_usdt, max_usdt), 2)
    print(f"    مقدار USDT تصادفی برای سواپ: {random_usdt_amount}")
    swap_success = run_swap_loop(initial_usdt_amount_ether=random_usdt_amount)
    if swap_success:
        print("👍 لوپ سواپ با موفقیت انجام شد.")
    else:
        print("👎 لوپ سواپ ناموفق بود.")
    return swap_success
        
def run_main_loop_level_3(total_main_loops, lvl2_iterations, lvl1_interactions, min_usdt=100.0, max_usdt=1000.0):
    print(f"\\n🚀🚀🚀========= شروع اجرای اصلی برنامه: {total_main_loops} تکرار =========🚀🚀🚀")
    for main_iter in range(total_main_loops):
        print(f"\\n🌌****** شروع تکرار اصلی شماره {main_iter + 1}/{total_main_loops} ******🌌")
        for i_lvl2 in range(lvl2_iterations):
            print(f"\\n    🎯 اجرای run_loop_level_2، شماره {i_lvl2 + 1}/{lvl2_iterations}...")
            run_loop_level_2(lvl1_interactions, min_usdt, max_usdt)
            if i_lvl2 < lvl2_iterations - 1:
                delay = random.uniform(10, 25)
                print(f"    پایان چرخه کاری. استراحت به مدت {delay:.2f} ثانیه...")
                time.sleep(delay)
        run_faucet_loop()
        print(f"  🎉 تکرار اصلی شماره {main_iter + 1} تمام شد.")
        if main_iter < total_main_loops - 1:
            delay = random.uniform(30, 75)
            print(f"    پایان کامل چرخه بزرگ. استراحت طولانی به مدت {delay:.2f} ثانیه...")
            time.sleep(delay)
    print(f"\\n🏁🏁🏁========= پایان کامل برنامه =========🏁🏁🏁")

if __name__ == "__main__":
    print("\\n--- شروع اسکریپت اصلی در محیط GitHub Actions ---")
    try:
        num_main_loop_iterations_to_run = int(os.environ.get('NUM_ITERATIONS', '1'))
        if num_main_loop_iterations_to_run > 0:
            print(f"\\nاسکریپت با {num_main_loop_iterations_to_run} تکرار اجرا خواهد شد.")
            # <<-- تغییرات اصلی برای کاهش تعداد دورها اینجا اعمال شد -->>
            run_main_loop_level_3(
                total_main_loops=num_main_loop_iterations_to_run,
                lvl2_iterations=3,
                lvl1_interactions=4,
                min_usdt=100.0,
                max_usdt=1000.0
            )
        else:
            print("تعداد تکرارها 0 است. برنامه اجرا نمی‌شود.")
    except ValueError:
        print("خطا: تعداد تکرارهای وارد شده یک عدد صحیح نیست.")
    except Exception as e:
        print(f"یک خطای ناشناخته رخ داد: {e}")
    print("\\n--- اجرای کامل اسکریپت به پایان رسید ---")
