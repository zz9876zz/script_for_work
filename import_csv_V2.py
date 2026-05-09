import csv
import argparse
from datetime import datetime
import sys
from pathlib import Path

# ==========================================
# Set your Config and Vendor mapping (Dictionary) here
# ==========================================
VENDOR_MAP = {
    'A': 'Samsung',
    'B': 'Micron',
    'C': 'Hynix',    
    'D': 'Kioxia',
    'X3603-SOMB-P1MAIN_P1-B-Main3AV_REL4a': 'Samsung',
    'X3603-SOMB-P1BUMAIN_P1BU-B-REL4aAV': 'Micron'
}
# ==========================================

def load_unit_mapping(map_file):
    mapping = {}
    if not map_file:
        return mapping
        
    try:
        with open(map_file, mode='r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            next(reader, None) 
            
            for row in reader:
                if len(row) >= 2:
                    sn = row[0].strip()
                    unit_num = row[1].strip()
                    mapping[sn] = unit_num
        print(f"[Info] Successfully loaded {len(mapping)} SN mappings from {map_file}")
    except Exception as e:
        print(f"[Warning] Failed to load mapping file {map_file}: {e}")
        
    return mapping

def filter_latest_test_results(input_file, output_file, unit_mapping,file_sort, has_header=True):
    latest_results = {}

    print(f"[Start] Reading file: {input_file}")
    print("Filesort:"+file_sort)
    try:
        with open(input_file, mode='r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            
            # If the CSV has a header, skip the first row automatically
            if has_header:
                next(reader, None)
                print("[Info] Automatically skipped the header row")
            
            for row in reader:
                # Safety net: skip empty rows or rows with insufficient columns
                if not row or len(row) < 6:
                    continue
                    
                serial_num = row[0].strip()       
                test_result = row[3].strip()      
                end_time_str = row[5].strip()     
                configs = row[22].strip() 
                
                try:
                    # Convert string to datetime object for comparison
                    # Note: Adjust format if your CSV uses '-' or includes seconds
                    current_test_time = datetime.strptime(end_time_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    continue
                
                vendor = VENDOR_MAP.get(configs, 'Unknown')
                
                # 💡 新增：拿著序號去查 Unit 字典！(找不到就顯示 N/A)
                unit_num = unit_mapping.get(serial_num, 'N/A')
                
                # 💡 新增：把 unit_num 放在資料清單的最前面
                clean_data = [unit_num, serial_num, test_result, configs, end_time_str, vendor]
                
                if serial_num not in latest_results:
                    latest_results[serial_num] = {'time': current_test_time, 'data': clean_data}
                else:
                    existing_time = latest_results[serial_num]['time']
                    if current_test_time > existing_time:
                        latest_results[serial_num] = {'time': current_test_time, 'data': clean_data}

        # Write the filtered results to a new CSV file
        with open(output_file, mode='w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            # 💡 新增：輸出檔案的標題列最前面加上 'Unit#'
            writer.writerow(['Unit#', 'Serial_Number', 'Test_Result', 'Configs', 'End_Time', 'Vendor'])
            
            for serial_num, info in latest_results.items():
                writer.writerow(info['data'])

        print(f"[Success] Processing complete! Kept {len(latest_results)} latest test records, saved to {output_file}")
        
    except FileNotFoundError:
        print(f"[Error] File not found: {input_file}. Please check the file name or path.")
    except Exception as e:
        print(f"[Error] An unknown error occurred: {e}")
    
    try:
        # ... (讀取與寫入檔案的邏輯) ...

        print(f"[Success] Processing complete! Kept {len(latest_results)} latest test records, saved to {output_file}")
        
        # ==========================================
        # 💡 新增：檢查並列出 MAP FILE 中未被使用的序號
        # ==========================================
        if unit_mapping: # 確保使用者有輸入 MAP FILE 才進行檢查
            # 1. 取得 MAP FILE 中所有的序號 (變成一個集合)
            map_sns = set(unit_mapping.keys())
            
            # 2. 取得實際測試紀錄中抓到的所有序號 (變成一個集合)
            tested_sns = set(latest_results.keys())
            
            # 3. 集合相減：在 MAP 中但不在測試紀錄中
            unused_sns = map_sns - tested_sns
            
            if unused_sns:
                print(f"\n[Info] 發現 {len(unused_sns)} 筆 MAP FILE 序號未被使用，已將清單存入 unmatched_sn.txt")
                
                # 💡 加上了引號的正確檔名！
                with open('unmatched_sn.txt', mode='w', encoding='utf-8') as log_file:
                    for sn in unused_sns:
                        unit_num = unit_mapping[sn]
                        log_file.write(f"序號 (SN): {sn}  =>  機台 (Unit#): {unit_num}\n")
       
    except FileNotFoundError:
        print(f"[Error] 找不到檔案：{input_file}")
    



if __name__ == "__main__":
    # Ensure Windows terminal outputs UTF-8 correctly
    sys.stdout.reconfigure(encoding='utf-8')
    
    parser = argparse.ArgumentParser(description="Tool to filter CSV test records and keep only the latest results")
    parser.add_argument('-i', metavar="INPUT_FILE", required=True, help="Specify the original CSV file to read")
    parser.add_argument('-o', metavar="OUTPUT_FILE", help="Specify the output CSV file name")
    
    parser.add_argument('-m', metavar="MAP_FILE", help="Specify the SN to Unit# mapping CSV file")
    parser.add_argument('--no-header', action='store_true', help="Disable skipping the first row")
    parser.add_argument('--sort', metavar="FILE_SORT", default="SOC_station", help="Specify the file sort (default: SOC_station)")
    args = parser.parse_args()
    
    if args.o:
        output_name = args.o
    else:
        input_path = Path(args.i)
        name_without_extension = input_path.stem
        extension = input_path.suffix
        output_name = name_without_extension + "_converted" + extension

    has_header_flag = not args.no_header

   
    unit_mapping_dict = load_unit_mapping(args.m)
    
    filter_latest_test_results(args.i, output_name, unit_mapping_dict,args.sort, has_header_flag)