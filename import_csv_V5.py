import csv
import argparse
from datetime import datetime
import sys
from pathlib import Path

# ==========================================
# Set your Config and Vendor mapping (Dictionary) here
# ==========================================
VENDOR_MAP = {
    'X3603-SOMB-P1BUMAIN_P1BU-B-Main2AU': 'SamsungBu',
    'X3603-SOMB-P1BUMAIN_P1BU-B-REL3aAU': 'SamsungBu',
    'X3603-SOMB-P1BUMAIN_P1BU-B-REL2AV': 'MicronBu',
    'X3603-SOMB-P1BUMAIN_P1BU-B-REL4aAV': 'MicronBu',

    'X3603-SOMB-P1MAIN_P1-B-Main4bAU':'Samsung',
    'X3603-SOMB-P1MAIN_P1-B-Main2AU': 'Samsung',
    'X3603-SOMB-P1MAIN_P1-B-REL1aAU': 'Samsung(using Micron)',
    'X3603-SOMB-P1MAIN_P1-B-REL3AU': 'Samsung',
    'X3603-SOMB-P1MAIN_P1-B-REL5AU': 'Samsung',
    'X3603-SOMB-P1MAIN_P1-B-REL6AV': 'Samsung',
    'X3603-SOMB-P1MAIN_P1-B-MainFSAV': 'Samsung',
    'X3603-SOMB-P1MAIN_P1-B-MainFFAV': 'Samsung',
    'X3603-SOMB-P1MAIN_P1-B-MainSSAU': 'Samsung',

    'X3603-SOMB-P1MAIN_P1-B-Main3AV_REL4a': 'Micron(count as samsung)',
    'X3603-SOMB-P1MAIN_P1-B-Main1AV': 'Micron',
    'X3603-SOMB-P1MAIN_P1-B-Main3AV': 'Micron',
    'X3603-SOMB-P1MAIN_P1-B-Main3bAU': 'Micron',
    'X3603-SOMB-P1MAIN_P1-B-Main3cAU': 'Micron',
    'X3603-SOMB-P1MAIN_P1-B-REL4aAV': 'Micron',  
    'X3603-SOMB-P1MAIN_P1-B-REL2AV': 'Micron',
    'X3603-SOMB-P1MAIN_P1-B-Main4AU': 'Micron',

    '': 'Micron',
    '': 'Micron',
}
# ==========================================
import csv
def get_sort_key(unit_str):
    if unit_str == 'N/A':
        return 999999
    else:
        return int(unit_str)
    
def load_compare_data(file_path):
    """Reads yesterday's CSV file for delta check (comparing old and new results)."""
    compare_results = {}
    if not file_path:
        return compare_results
        
    try:
        with open(file_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            next(reader, None) # Skip the header row
            
            for row in reader:
                if not row or len(row) < 6:
                    continue
                    
                unit_num = row[0].strip()   
                serial_num = row[1].strip()
                test_result = row[2].strip()
                end_time_str = row[4].strip()
                
                # Store data into the dictionary using SN as the key
                compare_results[serial_num] = {
                    'unit': unit_num,
                    'result': test_result,
                    'time': end_time_str
                }
    except Exception as e:
        print(f"[Warning] Cannot read compare file: {e}")
        
    return compare_results

def run_delta_check(latest_results, old_data):
    """Compares new and old data to find new units and units with changed results/times."""
    new_sn_list = []       # List for new units
    change_sn_list = []    # List for changed units
    
    for sn, info in latest_results.items():
        today_unit = info['data'][0]
        today_result = info['data'][2]
        today_time = info['data'][4]
        
        if sn in old_data:
            yesterday_result = old_data[sn]['result']
            yesterday_time = old_data[sn]['time']
            
            # Check if result or time has changed
            if yesterday_result != today_result or yesterday_time != today_time:
                change_sn_list.append(sn)
        else:
            # If SN is not in old_data, it's a newly tested unit
            new_sn_list.append(sn)
            
    return new_sn_list, change_sn_list

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

def filter_latest_test_results(input_file, output_file, unit_mapping, compare_file, file_sort, has_header=True):
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
            
        # ==========================================
        # Perform Delta Check (Compare old and new data)
        # ==========================================
        if compare_file:
            print(f"\n[Info] Starting comparison with yesterday's file: {compare_file}")
            
            # 1. Load yesterday's old data
            old_data = load_compare_data(compare_file)
            
            # 2. Run the comparison function and catch the two lists
            new_sn_list, change_sn_list = run_delta_check(latest_results, old_data)
            
            # 3. Print the professional comparison report
            print(f"[Info] Comparison complete! Found {len(new_sn_list)} new units and {len(change_sn_list)} units with changed status.")
            
            # 4. Print the detailed lists
           
            if new_sn_list:
                print("\n--- New Units List ---")
                sorted_new = sorted(new_sn_list, key=lambda sn: get_sort_key(latest_results[sn]['data'][0]))
                for sn in new_sn_list:
                    print(f"#{latest_results[sn]['data'][0]}_{sn}")
                    
            if change_sn_list:
                print("\n--- Changed Units List ---")
                sorted_new = sorted(change_sn_list, key=lambda sn: get_sort_key(latest_results[sn]['data'][0]))
                for sn in change_sn_list:
                    print(f"#{latest_results[sn]['data'][0]}_{sn}")       
                
                
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
    parser.add_argument('-c', metavar="COMPARE_FILE", help="Specify yesterday's CSV file to compare")
    parser.add_argument('--sort', metavar="FILE_SORT", default="SOC_station", help="Specify the file sort (default: SOC_station)")
    
    args = parser.parse_args()
    
    if args.o:
        output_name = args.o
    else:
        input_path = Path(args.i)
        name_without_extension = input_path.stem
        extension = input_path.suffix
        output_name = name_without_extension + "_converted" + extension

    if args.c:
        compare_file = args.c
    else:
        compare_file = None
       

    has_header_flag = not args.no_header

    if args.m:
        unit_mapping_dict = load_unit_mapping(args.m)
    else:
        default_map_file = Path(__file__).resolve().parent / "unit_num_table.csv"
        unit_mapping_dict = load_unit_mapping(default_map_file)
    
    filter_latest_test_results(args.i, output_name, unit_mapping_dict,compare_file ,args.sort, has_header_flag)