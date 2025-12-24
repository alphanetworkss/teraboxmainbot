"""
Quick setup script to verify environment and create necessary directories.
Run this before starting the bot for the first time.
"""
import os
import sys
from pathlib import Path


def check_python_version():
    """Check Python version."""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print(f"❌ Python 3.11+ required, found {version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_ffmpeg():
    """Check if FFmpeg is installed."""
    print("\n🎬 Checking FFmpeg...")
    result = os.system("ffmpeg -version > nul 2>&1" if os.name == 'nt' else "ffmpeg -version > /dev/null 2>&1")
    if result != 0:
        print("❌ FFmpeg not found in PATH")
        print("   Install from: https://ffmpeg.org/download.html")
        return False
    print("✅ FFmpeg installed")
    return True


def check_env_file():
    """Check if .env file exists."""
    print("\n📝 Checking .env file...")
    if not Path('.env').exists():
        print("❌ .env file not found")
        print("   Copy .env.example to .env and configure it")
        return False
    print("✅ .env file exists")
    return True


def create_directories():
    """Create necessary directories."""
    print("\n📁 Creating directories...")
    
    directories = [
        'downloads',
        'logs',
        'sessions'
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created {directory}/")
    
    return True


def check_dependencies():
    """Check if Python dependencies are installed."""
    print("\n📦 Checking Python dependencies...")
    
    required = [
        'aiogram',
        'motor',
        'redis',
        'aiohttp',
        'pydantic',
        'pydantic_settings',
        'loguru',
        'pyrogram',
        'tgcrypto'
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing.append(package)
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("   Run: pip install -r requirements.txt")
        return False
    
    return True


def main():
    """Main setup function."""
    print("=" * 50)
    print("TeraBox Bot System - Setup Verification")
    print("=" * 50)
    
    checks = [
        check_python_version(),
        check_ffmpeg(),
        check_env_file(),
        create_directories(),
        check_dependencies()
    ]
    
    print("\n" + "=" * 50)
    if all(checks):
        print("✅ All checks passed! Ready to start the bot.")
        print("\nNext steps:")
        print("1. Configure .env file with your credentials")
        print("2. Start MongoDB and Redis servers")
        print("3. Run: python main_bot.py")
        print("4. Run: python worker.py (in separate terminal)")
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        sys.exit(1)
    print("=" * 50)


if __name__ == "__main__":
    main()
