import os
import time
from web3 import Web3

def run_single_upload_test():
    """
    این تابع فقط یک بار تراکنش مربوط به آپلود فایل را ارسال و نتیجه را گزارش می‌کند.
    """
    print("--- شروع اسکریپت تست آپلود فایل ---")

    # ۱. خواندن کلید خصوصی و اتصال به شبکه
    try:
        RPC_URL = "https://evmrpc-testnet.0g.ai"
        CHAIN_ID = 16601
        SECRET_NAME_FOR_KEY = 'MY_PRIVATE_KEY'
        
        private_key = os.environ.get(SECRET_NAME_FOR_KEY)
        if not private_key:
            raise ValueError("کلید خصوصی در GitHub Secrets یافت نشد.")
            
        if not private_key.startswith("0x"):
            private_key = "0x" + private_key

        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        if not w3.is_connected():
            raise ConnectionError("اتصال به شبکه برقرار نشد.")
            
        account = w3.eth.account.from_key(private_key)
        print(f"✅ با موفقیت به شبکه متصل شد.")
        print(f"  آدرس حساب: {account.address}")
        
        balance_wei = w3.eth.get_balance(account.address)
        print(f"  موجودی حساب: {w3.from_wei(balance_wei, 'ether')} OG")
        
    except Exception as e:
        print(f"🚨 خطا در مرحله آماده‌سازی: {e}")
        return False

    # ۲. تعریف اطلاعات تراکنش (این اطلاعات ثابت هستند)
    contract_address = "0xbD75117F80b4E22698D0Cd7612d92BDb8eaff628"
    tx_data = "0xef3e12dc000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000004290000000000000000000000000000000000000000000000000000000000000060000000000000000000000000000000000000000000000000000000000000008000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000002677eefba56a5170c5d3f317bfd0b31c6449c3167441f0be0ed3381df308413700000000000000000000000000000000000000000000000000000000000000002a295b903559152821d7bb67048a24f22cee797b581493d715e6d17e5d4b270a70000000000000000000000000000000000000000000000000000000000000000"
    tx_value = 194000000000000  # مقدار 0x2b5e3af16ad در مبنای ۱۰

    # ۳. ساخت و ارسال تراکنش
    try:
        print("\n--- در حال ساخت و ارسال تراکنش تست آپلود ---")
        nonce = w3.eth.get_transaction_count(account.address)
        gas_price = w3.eth.gas_price

        upload_tx = {
            'to': w3.to_checksum_address(contract_address),
            'from': account.address,
            'nonce': nonce,
            'gasPrice': gas_price,
            'chainId': CHAIN_ID,
            'data': tx_data,
            'value': tx_value,
        }
        
        try:
            gas_estimate = w3.eth.estimate_gas(upload_tx)
            upload_tx['gas'] = int(gas_estimate * 1.2)
            print(f"  گس تخمینی: {gas_estimate}, گس نهایی: {upload_tx['gas']}")
        except Exception as e:
            print(f"    خطا در تخمین گس: {e}. استفاده از مقدار پیش‌فرض 500000.")
            upload_tx['gas'] = 500000

        signed_tx = account.sign_transaction(upload_tx)
        
        print("  درحال ارسال تراکنش به شبکه...")
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"  تراکنش ارسال شد. هش: {tx_hash.hex()}")
        
        print("  منتظر تایید تراکنش...")
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        
        if tx_receipt.status == 1:
            print(f"  ✅ تراکنش تست آپلود با موفقیت در بلاک {tx_receipt.blockNumber} تایید شد!")
            return True
        else:
            print(f"  ❌ تراکنش تست آپلود ناموفق بود (Reverted).")
            return False

    except Exception as e:
        print(f"🚨 یک خطای حیاتی در حین ارسال تراکنش رخ داد: {e}")
        return False

if __name__ == "__main__":
    run_single_upload_test()
