# Module Naming Conflict Fix

## Problem

The project had a folder named `queue/` which conflicted with Python's built-in `queue` module. This caused a circular import error:

```
ImportError: cannot import name 'Empty' from partially initialized module 'queue'
(most likely due to a circular import) (/workspaces/teraboxmainbot/queue/__init__.py)
```

## Solution

Renamed the folder from `queue/` to `redis_queue/` to avoid the conflict.

## Changes Made

### 1. Renamed Folder
```bash
queue/ → redis_queue/
```

### 2. Updated Imports

**main_bot.py:**
```python
# Before
from queue import init_redis, close_redis, job_queue

# After
from redis_queue import init_redis, close_redis, job_queue
```

**worker.py:**
```python
# Before
from queue import init_redis, close_redis, job_queue

# After
from redis_queue import init_redis, close_redis, job_queue
```

## Why This Happened

When Python encounters `import queue`, it first looks in the current project directory. Since we had a `queue/` folder, Python tried to import from there instead of the standard library's `queue` module. This caused pymongo (which needs the real `queue` module) to fail.

## Lesson Learned

**Never name your project folders/modules the same as Python built-in modules:**
- ❌ `queue`, `json`, `os`, `sys`, `time`, `datetime`, `random`, `string`, etc.
- ✅ `redis_queue`, `custom_json`, `app_os`, etc.

## Verification

After the fix, the bot should start without import errors:
```bash
python main_bot.py
```
