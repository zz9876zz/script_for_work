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
            next(reader, None) # Skip the header row
            
            for row in reader:
                if len(row) >= 2:
                    sn = row[0].strip()
                    unit_num = row[1].strip()
                    mapping[sn] = unit_num
        print(f"[Info] Successfully loaded {len(mapping)} SN mappings from {map_file}")
    except Exception as e:
        print(f"[Warning] Failed to load mapping file {map_file}: {e}")
        
    return mapping

def filter_latest_test_results(input_file, output_file, unit_mapping, file_sort, has_header=True):
    latest_results = {}

    print(f"[Start] Reading file: {input_file}")
    print(f"[Info] Filesort: {file_sort}")
    
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
                    current_test_time = datetime.strptime(end_time_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    continue
                
                vendor = VENDOR_MAP.get(configs, 'Unknown')
                
                # 💡 Look up Unit# using SN (default to 'N/A' if not found)
                unit_num = unit_mapping.get(serial_num, 'N/A')
                
                # 💡 Place unit_num at the beginning of the clean_data list
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
            # 💡 Add 'Unit#' to the first column of the header row
            writer.writerow(['Unit#', 'Serial_Number', 'Test_Result', 'Configs', 'End_Time', 'Vendor'])
            
            for serial_num, info in latest_results.items():
                writer.writerow(info['data'])

        print(f"[Success] Processing complete! Kept {len(latest_results)} latest test records, saved to {output_file}")
        
        # ==========================================
        # 💡 Check and list unused SNs from the MAP FILE
        # ==========================================
        # Ensure the user has provided a MAP FILE before checking
        if unit_mapping: 
            # 1. Get all SNs from the MAP FILE (as a set)
            map_sns = set(unit_mapping.keys())
            
            # 2. Get all tested SNs (as a set)
            tested_sns = set(latest_results.items()) 
            tested_sns = set(latest_results.keys())
            
            # 3. Set subtraction: Find SNs in MAP but not in test records
            unused_sns = map_sns - tested_sns
            
            if unused_sns:
                print(f"\n[Info] Found {len(unused_sns)} unused SNs from MAP FILE, saved the list to unmatched_sn.txt")
                
                # Save the unused SNs to a text file
                with open('unmatched_sn.txt', mode='w', encoding='utf-8') as log_file:
                    for sn in unused_sns:
                        unit_num = unit_mapping[sn]
                        log_file.write(f"SN: {sn}  =>  Unit#: {unit_num}\n")
            else:
                print("\n[Info] Great! All SNs in the MAP FILE match the test records.")
                
    except FileNotFoundError:
        print(f"[Error] File not found: {input_file}. Please check the file name or path.")
    except Exception as e:
        print(f"[Error] An unknown error occurred: {e}")

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
    
    filter_latest_test_results(args.i, output_name, unit_mapping_dict, args.sort, has_header_flag)