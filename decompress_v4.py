import os
import zipfile
import tarfile
import subprocess
import shutil
import argparse
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

# ==========================================

def extract_universal_mac(target_folder, output_folder):
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
        
        # --- Case 1: Handle .tar.gz or .tgz ---
        if file_name.endswith('.tar.gz') or file_name.endswith('.tgz'):
            folder_name = file_path.name[:-7] if file_name.endswith('.tar.gz') else file_path.name[:-4]
            # 💡 Call the robot to create the folder and get the path
            extract_dir = create_folder_if_not_exists(output_path, folder_name)
            
            print(f"📦 Extracting Tarball: {file_path.name}")
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
            folder_name = file_path.stem 
            # 💡 Call the robot to create the folder and get the path
            extract_dir = create_folder_if_not_exists(output_path, folder_name)
            
            print(f"📦 Extracting ZIP: {file_path.name}")
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
            folder_name = file_path.stem 
            # 💡 Call the robot to create the folder and get the path
            extract_dir = create_folder_if_not_exists(output_path, folder_name)
            
            print(f"📦 Extracting Apple Archive: {file_path.name}")
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
    args = parser.parse_args()
    
    if args.i:
        TARGET_DIR = args.i
    else:
        TARGET_DIR = Path(__file__).resolve().parent
    
    if args.d:
        OUTPUT_DIR = args.d
    else:
        OUTPUT_DIR = Path(__file__).resolve().parent    
        
    extract_universal_mac(TARGET_DIR, OUTPUT_DIR)