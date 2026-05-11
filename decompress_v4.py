import os
import zipfile
import tarfile
import subprocess
import shutil
import argparse
import csv
from pathlib import Path
from datetime import date

# ==========================================
# 🛠️ Your custom automation toolkit (Robot section)
# ==========================================

def create_old(file_path, folder_path):
    """Move the processed archive to the parent directory under old/YYYY-MM-DD for archiving"""
    today_str = str(date.today())
    archive_dir = folder_path.parent / "old" / today_str
    archive_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(file_path, archive_dir)
    print(f"📁 Archived original file to {archive_dir.resolve()}\n")

def create_folder_if_not_exists(folder_path, folder_name):
    """Prepare the destination folder for extraction (create if it doesn't exist)"""
    extract_dir = folder_path / folder_name
    extract_dir.mkdir(parents=True, exist_ok=True)
    return extract_dir

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

# ==========================================

def extract_universal_mac(target_folder, output_folder,unit_map):
    """
    Automatically determine format, extract, filter Mac hidden files, and archive upon success.
    """
    folder_path = Path(target_folder)
    output_path = Path(output_folder)
    
    print(f"📂 Source directory: {folder_path.resolve()}")
    print(f"🎯 Output destination: {output_path.resolve()}\n" + "-"*40)
    
    for file_path in folder_path.iterdir():
        # Ignore directories and hidden files
        if not file_path.is_file() or file_path.name.startswith('.'):
            continue
            
        # Convert to lowercase for easier format checking
        file_name = file_path.name.lower()
        
        original_name = file_path.name        
        base_name = original_name.split('.')[0]         
        parts = base_name.split('_')   
        sn = parts[0]         
        # 4. 去字典查機台號碼 (找不到就顯示 Unknown)
        unit_num = unit_map.get(sn, 'Unknown')        
        # 5. 終極組合：產出 "#40_ABC" 這種格式！
        custom_folder_name = f"#{unit_num}_{sn}"
        
        # 轉小寫，只是為了方便下面判斷副檔名
        file_name_lower = original_name.lower()


        # --- Case 1: Handle .tar.gz or .tgz ---
        if file_name.endswith('.tar.gz') or file_name.endswith('.tgz'):
            folder_name = file_path.name[:-7] if file_name.endswith('.tar.gz') else file_path.name[:-4]
            # 💡 Call the robot to create the folder and get the path
            extract_dir = create_folder_if_not_exists(output_path,custom_folder_name)
            
            print(f"📦 Extracting Tarball: {file_path.name} -> {custom_folder_name}")
            try:
                with tarfile.open(file_path, 'r:gz') as tar_ref:
                    clean_members = [m for m in tar_ref.getmembers() if not m.name.startswith('__MACOSX') and not m.name.endswith('.DS_Store') and not '/._' in m.name]
                    tar_ref.extractall(extract_dir, members=clean_members)
                print(f"✅ Extraction complete! (Saved in {extract_dir.name}/)")
                
                create_old(file_path, folder_path)
                
            except tarfile.ReadError:
                print(f"❌ Failed to extract. The file might be corrupted.\n")

        # --- Case 2: Handle standard .zip ---
        elif file_name.endswith('.zip'):
            # 💡 Call the robot to create the folder and get the path
            extract_dir = create_folder_if_not_exists(output_path, custom_folder_name)
            
            print(f"📦 Extracting ZIP: {file_path.name} -> {custom_folder_name}")
            try:
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    clean_members = [m for m in zip_ref.namelist() if not m.startswith('__MACOSX/') and not m.endswith('.DS_Store')]
                    zip_ref.extractall(extract_dir, members=clean_members)
                print(f"✅ Extraction complete! (Saved in {extract_dir.name}/)")
                
                create_old(file_path, folder_path)

            except zipfile.BadZipFile:
                print(f"   ⚠️ Python extraction failed, falling back to macOS ditto...")
                try:
                    cmd = ['ditto', '-x', '-k', str(file_path), str(extract_dir)]
                    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print(f"✅ Extraction complete! (Using ditto command)")
                    
                    create_old(file_path, folder_path)
                    
                except subprocess.CalledProcessError:
                    print(f"❌ System extraction also failed. The file might be corrupted.\n")

        # --- Case 3: Handle Apple-specific .aar ---
        elif file_name.endswith('.aar'):
            # 💡 Call the robot to create the folder and get the path
            extract_dir = create_folder_if_not_exists(output_path, custom_folder_name)
            print(f"📦 Extracting Apple Archive: {file_path.name} -> {custom_folder_name}")
            try:
                cmd = ['aa', 'extract', '-i', str(file_path), '-d', str(extract_dir)]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"✅ Extraction complete!")
                
                create_old(file_path, folder_path)
                
            except subprocess.CalledProcessError:
                print(f"❌ Failed to extract. Unknown format or file corrupted.\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tool for automatically extracting and archiving files")
    parser.add_argument('-i', metavar="PATH", help="Specify the source directory path (optional)")
    parser.add_argument('-d', metavar="PATH", help="Specify the output directory path (optional)")
    parser.add_argument('-m', metavar="MAP_FILE", help="Specify the SN to Unit# mapping CSV file")

    args = parser.parse_args()
    
    if args.i:
        TARGET_DIR = args.i
    else:
        TARGET_DIR = Path(__file__).resolve().parent
    
    if args.d:
        OUTPUT_DIR = args.d
    else:
        OUTPUT_DIR = Path(__file__).resolve().parent    

    if args.m:
        unit_mapping_dict = load_unit_mapping(args.m)
    else:
        default_map_file = Path(__file__).resolve().parent / "unit_num_table.csv"
        unit_mapping_dict = load_unit_mapping(default_map_file)
       #default is "unit_num_table.csv" in the same folder  
    extract_universal_mac(TARGET_DIR, OUTPUT_DIR,unit_mapping_dict)