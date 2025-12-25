"""
Cleanup orphaned download files.
Run this script to remove old temporary files that weren't deleted properly.
"""
import asyncio
from pathlib import Path
from utils.file_manager import file_manager
from utils.logger import log, setup_logger


async def cleanup_orphaned_files():
    """Clean up all orphaned files in the downloads directory."""
    try:
        setup_logger("cleanup")
        
        print("=" * 60)
        print("Orphaned Files Cleanup")
        print("=" * 60)
        
        download_dir = Path(file_manager.download_dir)
        
        if not download_dir.exists():
            print(f"❌ Download directory not found: {download_dir}")
            return
        
        # Get all files in download directory
        all_files = list(download_dir.glob("*.mp4"))
        
        if not all_files:
            print("✅ No files found in download directory - already clean!")
            return
        
        print(f"\n📁 Found {len(all_files)} file(s) in download directory")
        print(f"📂 Directory: {download_dir}\n")
        
        # Calculate total size
        total_size = sum(f.stat().st_size for f in all_files if f.exists())
        total_size_mb = total_size / (1024 * 1024)
        
        print(f"💾 Total size: {total_size_mb:.2f} MB\n")
        
        # List files
        print("Files to be deleted:")
        print("-" * 60)
        for f in all_files:
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"  • {f.name} ({size_mb:.2f} MB)")
        print("-" * 60)
        
        # Confirm deletion
        print(f"\n⚠️  WARNING: About to delete {len(all_files)} file(s) ({total_size_mb:.2f} MB)")
        response = input("Are you sure you want to continue? (yes/no): ")
        
        if response.lower() != 'yes':
            print("❌ Cancelled - no files were deleted")
            return
        
        # Delete files
        deleted_count = 0
        freed_space = 0
        
        for file_path in all_files:
            try:
                size = file_path.stat().st_size
                file_path.unlink()
                deleted_count += 1
                freed_space += size
                log.info(f"Deleted: {file_path.name}")
            except Exception as e:
                log.error(f"Failed to delete {file_path.name}: {e}")
                print(f"❌ Failed to delete: {file_path.name}")
        
        freed_space_mb = freed_space / (1024 * 1024)
        
        print(f"\n✅ Cleanup complete!")
        print(f"📊 Deleted: {deleted_count}/{len(all_files)} files")
        print(f"💾 Freed space: {freed_space_mb:.2f} MB")
        
    except Exception as e:
        log.error(f"Error during cleanup: {e}")
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(cleanup_orphaned_files())
