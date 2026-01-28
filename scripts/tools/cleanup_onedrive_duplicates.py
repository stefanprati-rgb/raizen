import os
import hashlib
import argparse
from pathlib import Path
from tqdm import tqdm

def get_file_hash(filepath):
    """Calculates MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None

def build_file_index(directory):
    """Builds a dictionary of {filename: filepath} for a given directory."""
    print(f"Indexing files in {directory}...")
    file_index = {}
    count = 0
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.pdf'):
                # Key is filename, Value is full path
                # Note: If multiple files have same name in processed, we keep the last one found.
                # This is acceptable for existence check.
                file_index[file] = os.path.join(root, file)
                count += 1
    print(f"Indexed {count} files in {directory}.")
    return file_index

def cleanup_duplicates(source_dir, target_dir, dry_run=True):
    """
    Removes files from target_dir if they exist in source_dir with same content.
    
    Args:
        source_dir: Directory containing files to KEEP (Reference).
        target_dir: Directory containing files to CLEANUP.
        dry_run: If True, only simulate deletion.
    """
    
    reference_files = build_file_index(source_dir)
    
    print(f"\nScanning {target_dir} for duplicates...")
    
    duplicates_found = 0
    space_saved = 0
    files_checked = 0
    errors = 0
    
    # Walk target directory
    files_to_check = []
    for root, _, files in os.walk(target_dir):
        for file in files:
            if file.lower().endswith('.pdf'):
                files_to_check.append(os.path.join(root, file))
    
    print(f"Found {len(files_to_check)} files to check in OneDrive folder.")
    
    for target_path in tqdm(files_to_check, desc="Checking files"):
        files_checked += 1
        filename = os.path.basename(target_path)
        
        # Check if filename exists in reference index
        if filename in reference_files:
            reference_path = reference_files[filename]
            
            # Calculate hashes
            target_hash = get_file_hash(target_path)
            reference_hash = get_file_hash(reference_path)
            
            if target_hash and reference_hash:
                if target_hash == reference_hash:
                    duplicates_found += 1
                    file_size = os.path.getsize(target_path)
                    space_saved += file_size
                    
                    if dry_run:
                        # concise log for dry run
                        # print(f"[DRY RUN] Would delete: {target_path} (Match: {reference_path})")
                        pass
                    else:
                        try:
                            os.remove(target_path)
                            print(f"[DELETED] {target_path}")
                        except Exception as e:
                            print(f"Failed to delete {target_path}: {e}")
                            errors += 1
                else:
                    # Same name, different content - WARN
                    print(f"\n[WARNING] Name match but HASH MISMATCH: {filename}")
                    print(f"  Target: {target_path}")
                    print(f"  Ref:    {reference_path}")
            else:
                errors += 1
    
    # Check for empty directories in target (optional cleanup)
    if not dry_run:
        print("\nCleaning up empty directories...")
        for root, dirs, files in os.walk(target_dir, topdown=False):
            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except OSError:
                    pass # Directory not empty

    print("\n" + "="*40)
    print("CLEANUP SUMMARY " + ("(DRY RUN)" if dry_run else "(LIVE)"))
    print("="*40)
    print(f"Files Checked:    {files_checked}")
    print(f"Duplicates Found: {duplicates_found}")
    print(f"Space Reclaimable: {space_saved / (1024*1024):.2f} MB")
    print(f"Errors:           {errors}")
    print("="*40)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cleanup duplicate PDFs from OneDrive folder.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate deletion without removing files")
    parser.add_argument("--force", action="store_true", help="Actually delete files (disable dry-run)")
    
    args = parser.parse_args()
    
    # Default to dry-run unless --force is specified
    is_dry_run = not args.force
    if args.dry_run:
        is_dry_run = True
        
    source_directory = r"c:\Projetos\Raizen\data\processed"
    target_directory = r"c:\Projetos\Raizen\data\raw\OneDrive_2026-01-06"
    
    if not os.path.exists(source_directory):
        print(f"Error: Source directory not found: {source_directory}")
        exit(1)
        
    if not os.path.exists(target_directory):
        print(f"Error: Target directory not found: {target_directory}")
        exit(1)

    cleanup_duplicates(source_directory, target_directory, dry_run=is_dry_run)
