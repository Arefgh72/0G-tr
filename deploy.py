import os
import json
import time
from web3 import Web3
from solcx import compile_files, install_solc

def deploy_contracts():
    print("--- شروع اسکریپت دیپلوی قراردادها ---")

    # ۱. تنظیمات اولیه و اتصال به شبکه
    try:
        RPC_URL = "https://evmrpc-testnet.0g.ai"
        CHAIN_ID = 16601
        EXPLORER_URL_TX_FORMAT = "https://chainscan-galileo.0g.ai/tx/0x{}"
        EXPLORER_URL_ADDRESS_FORMAT = "https://chainscan-galileo.0g.ai/address/{}"
        
        private_key = os.environ.get('MY_PRIVATE_KEY')
        if not private_key:
            raise ValueError("کلید خصوصی در GitHub Secrets یافت نشد.")
        if not private_key.startswith("0x"):
            private_key = "0x" + private_key

        w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={'timeout': 60.0}))
        account = w3.eth.account.from_key(private_key)
        print(f"✅ با موفقیت به شبکه متصل شد. آدرس شما: {account.address}")

    except Exception as e:
        print(f"🚨 خطا در مرحله آماده‌سازی: {e}")
        return

    # ۲. کامپایل کردن قراردادها
    try:
        print("\n--- در حال نصب و آماده‌سازی کامپایلر سالیدیتی ---")
        install_solc('0.8.20')
        
        contract_files = ["SimpleStorage.sol", "MyNFT.sol"]
        print(f"--- در حال کامپایل کردن فایل‌های: {contract_files} ---")
        
        compiled_sol = compile_files(
            contract_files,
            output_values=["abi", "bin"],
            import_remappings={
                "@openzeppelin/": "node_modules/@openzeppelin/"
            },
            solc_version='0.8.20'
        )
        print("✅ کامپایل با موفقیت انجام شد.")
        
        simple_storage_abi = compiled_sol["SimpleStorage.sol:SimpleStorage"]['abi']
        simple_storage_bytecode = compiled_sol["SimpleStorage.sol:SimpleStorage"]['bin']
        
        my_nft_abi = compiled_sol["MyNFT.sol:MyNFT"]['abi']
        my_nft_bytecode = compiled_sol["MyNFT.sol:MyNFT"]['bin']

    except Exception as e:
        print(f"🚨 خطا در مرحله کامپایل: {e}")
        return

    # ۳. دیپلوی قرارداد SimpleStorage با منطق تلاش مجدد
    print("\n--- شروع دیپلوی قرارداد SimpleStorage ---")
    for attempt in range(3):
        try:
            print(f"  تلاش {attempt + 1}/3 برای دیپلوی SimpleStorage...")
            Contract = w3.eth.contract(abi=simple_storage_abi, bytecode=simple_storage_bytecode)
            
            nonce = w3.eth.get_transaction_count(account.address)
            gas_price = w3.eth.gas_price
            
            # <<-- افزایش قیمت گاز در تلاش‌های مجدد
            if attempt > 0:
                gas_price = int(gas_price * (1.2**attempt))
                print(f"    افزایش قیمت گاز به: {gas_price}")

            tx_deploy = Contract.constructor().build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gasPrice': gas_price,
                'chainId': CHAIN_ID
            })
            
            signed_tx = account.sign_transaction(tx_deploy)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            print(f"  تراکنش دیپلوی SimpleStorage ارسال شد. هش: {tx_hash.hex()}")
            
            tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            contract_address = tx_receipt.contractAddress
            
            print(f"✅ قرارداد SimpleStorage با موفقیت در آدرس زیر دیپلوی شد:")
            print(f"  {contract_address}")
            break # <<-- اگر موفق بود، از حلقه خارج شو
            
        except Exception as e:
            print(f"🚨 خطا در تلاش {attempt + 1} دیپلوی SimpleStorage: {e}")
            if attempt < 2:
                print("   تاخیر ۳ ثانیه‌ای و تلاش مجدد...")
                time.sleep(3)
            else:
                print("   به حداکثر تعداد تلاش برای SimpleStorage رسیدیم.")

    # یک تاخیر کوتاه بین دو دیپلوی
    print("\nتاخیر ۵ ثانیه‌ای قبل از دیپلوی بعدی...")
    time.sleep(5)

    # ۴. دیپلوی قرارداد MyNFT با منطق تلاش مجدد
    print("\n--- شروع دیپلوی قرارداد MyNFT ---")
    for attempt in range(3):
        try:
            print(f"  تلاش {attempt + 1}/3 برای دیپلوی MyNFT...")
            ContractNFT = w3.eth.contract(abi=my_nft_abi, bytecode=my_nft_bytecode)
            
            nonce = w3.eth.get_transaction_count(account.address)
            gas_price = w3.eth.gas_price

            # <<-- افزایش قیمت گاز در تلاش‌های مجدد
            if attempt > 0:
                gas_price = int(gas_price * (1.2**attempt))
                print(f"    افزایش قیمت گاز به: {gas_price}")

            tx_deploy_nft = ContractNFT.constructor().build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gasPrice': gas_price,
                'chainId': CHAIN_ID
            })
            
            signed_tx_nft = account.sign_transaction(tx_deploy_nft)
            tx_hash_nft = w3.eth.send_raw_transaction(signed_tx_nft.raw_transaction)
            print(f"  تراکنش دیپلوی MyNFT ارسال شد. هش: {tx_hash_nft.hex()}")
            
            tx_receipt_nft = w3.eth.wait_for_transaction_receipt(tx_hash_nft, timeout=120)
            contract_address_nft = tx_receipt_nft.contractAddress
            
            print(f"✅ قرارداد MyNFT با موفقیت در آدرس زیر دیپلوی شد:")
            print(f"  {contract_address_nft}")
            break # <<-- اگر موفق بود، از حلقه خارج شو

        except Exception as e:
            print(f"🚨 خطا در تلاش {attempt + 1} دیپلوی MyNFT: {e}")
            if attempt < 2:
                print("   تاخیر ۳ ثانیه‌ای و تلاش مجدد...")
                time.sleep(3)
            else:
                print("   به حداکثر تعداد تلاش برای MyNFT رسیدیم.")

    print("\n--- اسکریپت دیپلوی به پایان رسید. ---")


if __name__ == "__main__":
    deploy_contracts()
