import json

try:
    with open('contract_abi.json', 'r') as f:
        abi = json.load(f)
    print("ABI load thành công! Số hàm:", len(abi))
    print("Hàm đầu tiên:", abi[0]['name'] if abi else "Không có hàm")
except json.JSONDecodeError as e:
    print("Lỗi JSON trong file:", str(e))
except FileNotFoundError:
    print("Không tìm thấy file contract_abi.json")