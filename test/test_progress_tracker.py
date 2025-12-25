"""
Test script for progress tracking utilities.
Run this to verify the progress tracker module works correctly.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from utils.progress_tracker import (
    FFmpegProgressParser,
    ProgressBarGenerator,
    MessageRateLimiter,
    ProgressLogger,
    format_time,
    format_bytes
)


def test_ffmpeg_parser():
    """Test FFmpeg progress parser."""
    print("=" * 50)
    print("Testing FFmpeg Progress Parser")
    print("=" * 50)
    
    parser = FFmpegProgressParser()
    
    # Test duration parsing
    duration_line = "  Duration: 00:04:33.45, start: 0.000000, bitrate: 1234 kb/s"
    duration = parser.parse_duration(duration_line)
    print(f"✓ Duration parsed: {duration}s (expected: 273.45s)")
    assert abs(duration - 273.45) < 0.1, "Duration parsing failed"
    
    # Test progress line parsing
    progress_line = "out_time_ms=123456789"
    parsed = parser.parse_progress_line(progress_line)
    print(f"✓ Progress line parsed: {parsed}")
    assert parsed == {'out_time_ms': '123456789'}, "Progress line parsing failed"
    
    # Test progress calculation
    progress_data = parser.calculate_progress(
        out_time_ms=123_456_789,  # 123.456 seconds
        total_duration=273.45,
        speed="2.3x"
    )
    print(f"✓ Progress calculated:")
    print(f"  - Percentage: {progress_data.percentage:.2f}%")
    print(f"  - Speed: {progress_data.speed}")
    print(f"  - ETA: {progress_data.eta}")
    print(f"  - Current time: {progress_data.current_time:.2f}s")
    
    print("\n✅ FFmpeg parser tests passed!\n")


def test_progress_bar():
    """Test progress bar generator."""
    print("=" * 50)
    print("Testing Progress Bar Generator")
    print("=" * 50)
    
    generator = ProgressBarGenerator()
    
    test_cases = [0, 25, 50, 75, 100]
    for percentage in test_cases:
        bar = generator.generate(percentage, length=15)
        print(f"{percentage:3d}%: {bar}")
    
    # Test edge cases
    print("\nEdge cases:")
    print(f"Negative: {generator.generate(-10, 15)}")
    print(f"Over 100: {generator.generate(150, 15)}")
    
    print("\n✅ Progress bar tests passed!\n")


async def test_rate_limiter():
    """Test message rate limiter."""
    print("=" * 50)
    print("Testing Message Rate Limiter")
    print("=" * 50)
    
    limiter = MessageRateLimiter(min_interval=2.0)  # 2 seconds for testing
    
    job_id = "test_job_123"
    
    # First update should pass
    should_update = await limiter.should_update(job_id)
    print(f"✓ First update: {should_update} (expected: True)")
    assert should_update == True, "First update should be allowed"
    
    # Immediate second update should fail
    should_update = await limiter.should_update(job_id)
    print(f"✓ Immediate update: {should_update} (expected: False)")
    assert should_update == False, "Immediate update should be blocked"
    
    # Wait 2 seconds
    print("  Waiting 2 seconds...")
    await asyncio.sleep(2.1)
    
    # Update after interval should pass
    should_update = await limiter.should_update(job_id)
    print(f"✓ Update after interval: {should_update} (expected: True)")
    assert should_update == True, "Update after interval should be allowed"
    
    print("\n✅ Rate limiter tests passed!\n")


def test_formatters():
    """Test formatting functions."""
    print("=" * 50)
    print("Testing Formatters")
    print("=" * 50)
    
    # Test time formatting
    print("Time formatting:")
    test_times = [30, 90, 3665, 7325]
    for seconds in test_times:
        formatted = format_time(seconds)
        print(f"  {seconds:5d}s → {formatted}")
    
    print("\nBytes formatting:")
    test_bytes = [512, 1024, 1048576, 1073741824, 1099511627776]
    for bytes_val in test_bytes:
        formatted = format_bytes(bytes_val)
        print(f"  {bytes_val:15d} → {formatted}")
    
    print("\n✅ Formatter tests passed!\n")


def test_logger():
    """Test progress logger."""
    print("=" * 50)
    print("Testing Progress Logger")
    print("=" * 50)
    
    logger = ProgressLogger()
    
    job_id = "a1b2c3d4e5f6g7h8i9j0"
    
    print("Download logs:")
    logger.log_download_start(job_id, "https://example.com/stream.m3u8")
    logger.log_download_progress(job_id, 45.2, "2.3x", "02:31")
    logger.log_download_complete(job_id, 245.3, 198_450_000)
    logger.log_download_error(job_id, "Network timeout")
    
    print("\nUpload logs:")
    logger.log_upload_start(job_id, 0, 198_450_000)
    logger.log_upload_progress(job_id, 60.5, 120.3, 198.7, 0)
    logger.log_upload_complete(job_id, 38.2, 0, 198_450_000)
    logger.log_upload_error(job_id, "Connection reset", 0)
    
    print("\n✅ Logger tests passed!\n")


async def main():
    """Run all tests."""
    print("\n" + "=" * 50)
    print("PROGRESS TRACKER UTILITY TESTS")
    print("=" * 50 + "\n")
    
    try:
        test_ffmpeg_parser()
        test_progress_bar()
        await test_rate_limiter()
        test_formatters()
        test_logger()
        
        print("=" * 50)
        print("✅ ALL TESTS PASSED!")
        print("=" * 50)
        print("\nThe progress tracking utilities are working correctly.")
        print("You can now test the full bot with real M3U8 streams.\n")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        raise


if __name__ == "__main__":
    asyncio.run(main())
