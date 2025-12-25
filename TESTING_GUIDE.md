# Testing Guide for Real-Time Progress Tracking

## Quick Start

### 1. Test Progress Utilities

Run the unit tests to verify all utilities work correctly:

```bash
cd "e:\Terabox dowanloader\terabox_bot_system"
python test\test_progress_tracker.py
```

**Expected output:**
- ✅ FFmpeg parser tests passed
- ✅ Progress bar tests passed
- ✅ Rate limiter tests passed
- ✅ Formatter tests passed
- ✅ Logger tests passed

---

## Manual Testing with Real Bot

### 2. Start the Worker

```bash
python worker.py
```

**Watch for logs:**
```
[DOWNLOAD] START | job_id=... | url=...
[FFMPEG] Detected duration: 273.45s
[DOWNLOAD] 25.0% | speed=2.1x | eta=03:12 | job_id=...
```

### 3. Send a TeraBox Link

Send any TeraBox link to your bot and observe:

**Download Progress Message:**
```
📥 Downloading (Stream → MP4)

╭━━━━❰Progress❱━━━━➣
┣⪼ ███████░░░░░░░░ 45.2%
┣⪼ ⚡ Speed: 2.3x
┣⪼ ⏱️ ETA: 02:31
╰━━━━━━━━━━━━━━━➣
```

**Upload Progress Message:**
```
📤 Uploading to Channel

╭━━━━❰Progress❱━━━━➣
┣⪼ █████████░░░░░░ 60.5%
┣⪼ 📦 Uploaded: 120.3MB / 198.7MB
┣⪼ 🚀 Speed: 5.1 MB/s
┣⪼ ⏱️ ETA: 01:15
╰━━━━━━━━━━━━━━━➣
```

---

## Verification Checklist

### Download Progress
- [ ] Progress starts at 0% and increases to 100%
- [ ] Progress bar fills from left to right (█ characters)
- [ ] Speed shows real ffmpeg speed (e.g., "2.3x", not "1.0x")
- [ ] ETA decreases as download progresses
- [ ] Message updates every 3-5 seconds (not faster)
- [ ] No "stuck at 0%" issue

### Upload Progress
- [ ] Progress starts at 0% and increases to 100%
- [ ] Uploaded MB increases (e.g., "50MB / 200MB")
- [ ] Speed shows MB/s (e.g., "5.1 MB/s")
- [ ] ETA is reasonable and decreases
- [ ] Message updates every 3-5 seconds

### Logging
- [ ] Logs show `[DOWNLOAD] START` with job_id
- [ ] Logs show `[FFMPEG] Detected duration: X.XXs`
- [ ] Logs show progress at 25%, 50%, 75%
- [ ] Logs show `[DOWNLOAD] COMPLETE` with duration and file size
- [ ] Logs show `[UPLOAD] START` with bot index
- [ ] Logs show `[UPLOAD] COMPLETE` with speed

### Error Handling
- [ ] Invalid M3U8 URL → shows error message
- [ ] Network interruption → logs error, doesn't crash
- [ ] No Telegram flood errors in logs

---

## Common Issues & Solutions

### Issue: Progress stuck at 0%

**Cause:** FFmpeg not outputting duration or progress data

**Solution:**
1. Check logs for `[FFMPEG] Detected duration: X.XXs`
2. If missing, verify ffmpeg command includes `-loglevel info`
3. Check stderr parsing is working

### Issue: Telegram flood errors

**Cause:** Messages updating too frequently

**Solution:**
1. Verify rate limiter is working: `await rate_limiter.should_update(job_id)`
2. Check minimum interval is 3 seconds
3. Look for multiple concurrent progress callbacks

### Issue: Speed always shows "1.0x"

**Cause:** FFmpeg not outputting speed data

**Solution:**
1. Verify `-progress pipe:1` is in ffmpeg command
2. Check stdout parsing is reading speed field
3. Verify progress data includes 'speed' key

### Issue: ETA shows "Calculating..." forever

**Cause:** Duration not detected or speed is 0

**Solution:**
1. Check duration extraction from stderr
2. Verify speed is being parsed correctly
3. Check calculation: `remaining_time / speed_multiplier`

---

## Performance Monitoring

### Check Log File

```bash
tail -f logs/worker.log
```

**Look for:**
- Regular progress updates (every 3-5 seconds)
- No error messages
- Completion logs with reasonable durations
- Upload speeds matching your network capacity

### Monitor Telegram API

**Watch for:**
- No "Too Many Requests" errors
- Message edits spacing (3+ seconds apart)
- Smooth progress updates without gaps

---

## Advanced Testing

### Test with Different Video Lengths

1. **Short video (< 1 min):** Verify 100% completion
2. **Medium video (5-10 min):** Check ETA accuracy
3. **Long video (> 30 min):** Verify no timeout issues

### Test with Different Network Speeds

1. **Fast connection:** Speed should be > 1.0x
2. **Slow connection:** Speed might be < 1.0x
3. **Unstable connection:** Verify graceful error handling

### Test Concurrent Downloads

1. Send multiple links simultaneously
2. Verify each has independent progress tracking
3. Check rate limiter works per job
4. Verify no cross-contamination of progress data

---

## Success Metrics

✅ **Download progress accuracy:** Within 5% of actual progress  
✅ **ETA accuracy:** Within 20% of actual remaining time  
✅ **Upload speed accuracy:** Matches network speed  
✅ **Message update frequency:** 3-5 seconds consistently  
✅ **No errors:** Zero flood errors, zero crashes  
✅ **Log completeness:** All milestones logged  

---

## Troubleshooting Commands

### Check FFmpeg Output Manually

```bash
ffmpeg -i "https://example.com/stream.m3u8" -c copy -progress pipe:1 -nostats -loglevel info output.mp4
```

Watch for:
- `Duration: HH:MM:SS.ms` in initial output
- `out_time_ms=...` in progress output
- `speed=X.Xx` in progress output

### Test Progress Parser

```python
from utils.progress_tracker import ffmpeg_parser

# Test duration parsing
line = "  Duration: 00:04:33.45, start: 0.000000"
duration = ffmpeg_parser.parse_duration(line)
print(f"Duration: {duration}s")

# Test progress calculation
progress = ffmpeg_parser.calculate_progress(
    out_time_ms=123_456_789,
    total_duration=273.45,
    speed="2.3x"
)
print(f"Progress: {progress.percentage}%")
print(f"ETA: {progress.eta}")
```

---

## Next Steps After Testing

1. ✅ Verify all tests pass
2. ✅ Monitor production logs for 24 hours
3. ✅ Collect user feedback on progress accuracy
4. ✅ Optimize rate limiting if needed
5. ✅ Consider adding progress persistence for resume capability

---

## Support

If you encounter issues:

1. Check logs in `logs/worker.log`
2. Run unit tests: `python test\test_progress_tracker.py`
3. Verify ffmpeg is installed and accessible
4. Check Telegram bot token and permissions
5. Review implementation in `walkthrough.md`
