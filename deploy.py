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
        EXPLORER_URL_TX_FORMAT = "https://chainscan-galileo.0g.ai/tx/{}"
        
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
        
        # مسیر import های OpenZeppelin را مشخص می‌کنیم
        compiled_sol = compile_files(
            contract_files,
            output_values=["abi", "bin"],
            import_remappings={
                "@openzeppelin/": "node_modules/@openzeppelin/"
            },
            solc_version='0.8.20'
        )
        print("✅ کامپایل با موفقیت انجام شد.")
        
        # استخراج ABI و بایت‌کد برای هر قرارداد
        simple_storage_abi = compiled_sol["SimpleStorage.sol:SimpleStorage"]['abi']
        simple_storage_bytecode = compiled_sol["SimpleStorage.sol:SimpleStorage"]['bin']
        
        my_nft_abi = compiled_sol["MyNFT.sol:MyNFT"]['abi']
        my_nft_bytecode = compiled_sol["MyNFT.sol:MyNFT"]['bin']

    except Exception as e:
        print(f"🚨 خطا در مرحله کامپایل: {e}")
        return

    # ۳. دیپلوی قرارداد SimpleStorage
    try:
        print("\n--- شروع دیپلوی قرارداد SimpleStorage ---")
        Contract = w3.eth.contract(abi=simple_storage_abi, bytecode=simple_storage_bytecode)
        
        nonce = w3.eth.get_transaction_count(account.address)
        tx_deploy = Contract.constructor().build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gasPrice': w3.eth.gas_price,
            'chainId': CHAIN_ID
        })
        
        signed_tx = account.sign_transaction(tx_deploy)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"  تراکنش دیپلوی SimpleStorage ارسال شد. هش: {tx_hash.hex()}")
        
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        contract_address = tx_receipt.contractAddress
        
        print(f"✅ قرارداد SimpleStorage با موفقیت در آدرس زیر دیپلوی شد:")
        print(f"  {contract_address}")
        print(f"  لینک اکسپلورر: {EXPLORER_URL_TX_FORMAT.format(tx_hash.hex())}")
        
    except Exception as e:
        print(f"🚨 خطا در دیپلوی SimpleStorage: {e}")

    # یک تاخیر کوتاه بین دو دیپلوی
    print("\nتاخیر ۵ ثانیه‌ای قبل از دیپلوی بعدی...")
    time.sleep(5)

    # ۴. دیپلوی قرارداد MyNFT
    try:
        print("\n--- شروع دیپلوی قرارداد MyNFT ---")
        ContractNFT = w3.eth.contract(abi=my_nft_abi, bytecode=my_nft_bytecode)
        
        nonce = w3.eth.get_transaction_count(account.address)
        tx_deploy_nft = ContractNFT.constructor().build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gasPrice': w3.eth.gas_price,
            'chainId': CHAIN_ID
        })
        
        signed_tx_nft = account.sign_transaction(tx_deploy_nft)
        tx_hash_nft = w3.eth.send_raw_transaction(signed_tx_nft.raw_transaction)
        print(f"  تراکنش دیپلوی MyNFT ارسال شد. هش: {tx_hash_nft.hex()}")
        
        tx_receipt_nft = w3.eth.wait_for_transaction_receipt(tx_hash_nft)
        contract_address_nft = tx_receipt_nft.contractAddress
        
        print(f"✅ قرارداد MyNFT با موفقیت در آدرس زیر دیپلوی شد:")
        print(f"  {contract_address_nft}")
        print(f"  لینک اکسپلورر: {EXPLORER_URL_TX_FORMAT.format(tx_hash_nft.hex())}")

    except Exception as e:
        print(f"🚨 خطا در دیپلوی MyNFT: {e}")

    print("\n--- اسکریپت دیپلوی به پایان رسید. ---")


if __name__ == "__main__":
    deploy_contracts()
