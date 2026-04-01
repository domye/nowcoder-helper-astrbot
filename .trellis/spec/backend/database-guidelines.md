# Data Storage Guidelines

> How to store and manage data in AstrBot plugins.

---

## Overview

AstrBot plugins typically **do not use traditional databases**. Instead, data persistence is achieved through:

1. **Configuration files** - User-configurable settings
2. **Plugin data directory** - Persistent data storage
3. **Cache** - Temporary data in memory

**Key Principle**: Use AstrBot's provided storage mechanisms, not custom database solutions.

---

## Data Storage Locations

### 1. Plugin Configuration

**Path**: `data/config/<plugin_name>_config.json`

**Purpose**: User-customizable settings defined in `_conf_schema.json`

**Access**:
```python
def __init__(self, context: Context, config: AstrBotConfig):
    super().__init__(context)
    self.config = config  # AstrBotConfig instance

    # Read config
    token = config.get("api_token")

    # Modify and save
    config["new_setting"] = "value"
    config.save_config()  # Persist to disk
```

### 2. Plugin Data Directory

**Path**: `data/plugin_data/<plugin_name>/`

**Purpose**: Store plugin-specific data files (cache, logs, user data, etc.)

**Access**:
```python
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

# Get plugin data directory
data_dir = get_astrbot_data_path() / "plugin_data" / self.name

# Create directory if needed
data_dir.mkdir(parents=True, exist_ok=True)

# Store data
data_file = data_dir / "cache.json"
await self.save_json(data_file, cache_data)

# Load data
cache_data = await self.load_json(data_file)
```

---

## File-Based Data Storage

### JSON Storage Pattern

```python
import json
import aiofiles
from pathlib import Path

class DataStorage:
    def __init__(self, plugin_name: str):
        self.data_dir = get_astrbot_data_path() / "plugin_data" / plugin_name
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def save_json(self, filename: str, data: dict):
        '''Save data to JSON file'''
        filepath = self.data_dir / filename
        async with aiofiles.open(filepath, 'w') as f:
            await f.write(json.dumps(data, indent=2))

    async def load_json(self, filename: str) -> dict:
        '''Load data from JSON file'''
        filepath = self.data_dir / filename
        if not filepath.exists():
            return {}

        async with aiofiles.open(filepath, 'r') as f:
            content = await f.read()
            return json.loads(content)

    async def delete_file(self, filename: str):
        '''Delete data file'''
        filepath = self.data_dir / filename
        if filepath.exists():
            filepath.unlink()
```

### Usage in Plugin

```python
@register("my_plugin", "author", "desc", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.storage = DataStorage("my_plugin")

    async def initialize(self):
        '''Load cached data'''
        self.cache = await self.storage.load_json("cache.json")

    @filter.command("save_data")
    async def save_data(self, event: AstrMessageEvent, key: str, value: str):
        '''Save data to cache'''
        self.cache[key] = value
        await self.storage.save_json("cache.json", self.cache)
        yield event.plain_result(f"Saved: {key}={value}")

    async def terminate(self):
        '''Save cache before exit'''
        await self.storage.save_json("cache.json", self.cache)
```

---

## Configuration Schema (_conf_schema.json)

### Defining User-Configurable Settings

```json
{
  "api_token": {
    "description": "API Token",
    "type": "string",
    "hint": "Enter your API token"
  },
  "cache_enabled": {
    "description": "Enable caching",
    "type": "bool",
    "default": true
  },
  "max_items": {
    "description": "Maximum items to store",
    "type": "int",
    "default": 100
  },
  "advanced": {
    "description": "Advanced settings",
    "type": "object",
    "items": {
      "timeout": {
        "description": "Timeout (seconds)",
        "type": "int",
        "default": 30
      },
      "retry_count": {
        "description": "Retry attempts",
        "type": "int",
        "default": 3
      }
    }
  }
}
```

### Accessing Configuration

```python
def __init__(self, context: Context, config: AstrBotConfig):
    super().__init__(context)
    self.config = config

    # Simple values
    token = config.get("api_token")
    cache_enabled = config.get("cache_enabled", True)
    max_items = config.get("max_items", 100)

    # Nested values
    timeout = config.get("advanced", {}).get("timeout", 30)
    retries = config.get("advanced", {}).get("retry_count", 3)
```

---

## In-Memory Cache Pattern

### Simple Cache

```python
@register("cached_plugin", "author", "desc", "1.0.0")
class CachedPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.cache = {}  # In-memory cache
        self.cache_timestamp = {}

    async def get_cached_data(self, key: str, ttl: int = 300):
        '''Get data from cache or fetch fresh'''
        # Check cache
        if key in self.cache:
            timestamp = self.cache_timestamp.get(key, 0)
            if time.time() - timestamp < ttl:
                return self.cache[key]

        # Fetch fresh data
        data = await self.fetch_data(key)

        # Update cache
        self.cache[key] = data
        self.cache_timestamp[key] = time.time()

        return data

    @filter.command("query")
    async def query(self, event: AstrMessageEvent, keyword: str):
        '''Query with cache'''
        data = await self.get_cached_data(keyword, ttl=300)
        yield event.plain_result(data)
```

### Persistent Cache

```python
class PersistentCache:
    def __init__(self, plugin_name: str, filename: str = "cache.json"):
        self.storage = DataStorage(plugin_name)
        self.filename = filename
        self.cache = {}
        self.timestamp = {}

    async def load(self):
        '''Load cache from disk'''
        data = await self.storage.load_json(self.filename)
        self.cache = data.get("cache", {})
        self.timestamp = data.get("timestamp", {})

    async def save(self):
        '''Save cache to disk'''
        data = {
            "cache": self.cache,
            "timestamp": self.timestamp
        }
        await self.storage.save_json(self.filename, data)

    async def get(self, key: str, ttl: int = 300):
        '''Get cached item'''
        if key in self.cache:
            ts = self.timestamp.get(key, 0)
            if time.time() - ts < ttl:
                return self.cache[key]
        return None

    async def set(self, key: str, value: any):
        '''Set cached item'''
        self.cache[key] = value
        self.timestamp[key] = time.time()
        await self.save()

# Usage in plugin
def __init__(self, context: Context):
    super().__init__(context)
    self.cache = PersistentCache("my_plugin")

async def initialize(self):
    await self.cache.load()

async def terminate(self):
    await self.cache.save()
```

---

## Data Migration Pattern

### Version-Based Migration

```python
class DataMigration:
    def __init__(self, storage: DataStorage):
        self.storage = storage

    async def get_version(self) -> int:
        '''Get current data version'''
        meta = await self.storage.load_json("meta.json")
        return meta.get("version", 0)

    async def set_version(self, version: int):
        '''Set data version'''
        meta = await self.storage.load_json("meta.json")
        meta["version"] = version
        await self.storage.save_json("meta.json", meta)

    async def migrate(self):
        '''Run migrations'''
        version = await self.get_version()

        if version < 1:
            await self.migrate_v1()
            await self.set_version(1)

        if version < 2:
            await self.migrate_v2()
            await self.set_version(2)

    async def migrate_v1(self):
        '''Migration to version 1'''
        logger.info("Migrating to v1...")
        # Migration logic

    async def migrate_v2(self):
        '''Migration to version 2'''
        logger.info("Migrating to v2...")
        # Migration logic

# Usage in plugin
async def initialize(self):
    migration = DataMigration(self.storage)
    await migration.migrate()
```

---

## Anti-Patterns

### ❌ Wrong: Custom Database

```python
# WRONG: Using SQLite or other database
import sqlite3

conn = sqlite3.connect("my_database.db")  # Wrong!
```

**Why**: AstrBot provides standardized storage paths. Use them for consistency.

### ❌ Wrong: Hardcoded Paths

```python
# WRONG: Hardcoded file path
filepath = "/tmp/my_data.json"  # Wrong!

# CORRECT: Use AstrBot's data path
filepath = get_astrbot_data_path() / "plugin_data" / self.name / "data.json"
```

### ❌ Wrong: Blocking File I/O

```python
# WRONG: Blocking file operations
with open("data.json") as f:
    data = json.load(f)  # Blocking!

# CORRECT: Async file operations
import aiofiles

async with aiofiles.open("data.json") as f:
    content = await f.read()
    data = json.loads(content)
```

### ❌ Wrong: Storing in Plugin Directory

```python
# WRONG: Storing data in plugin source directory
filepath = Path(__file__).parent / "data.json"  # Wrong!

# CORRECT: Store in AstrBot data directory
filepath = get_astrbot_data_path() / "plugin_data" / self.name / "data.json"
```

---

## Best Practices

### 1. Use AstrBot's Storage Paths

```python
# Always use get_astrbot_data_path()
data_dir = get_astrbot_data_path() / "plugin_data" / self.name
```

### 2. Async File Operations

```python
# Use aiofiles for async file I/O
import aiofiles

async with aiofiles.open(filepath, 'w') as f:
    await f.write(json.dumps(data))
```

### 3. Create Directories Before Use

```python
data_dir = get_astrbot_data_path() / "plugin_data" / self.name
data_dir.mkdir(parents=True, exist_ok=True)
```

### 4. Save on Terminate

```python
async def terminate(self):
    '''Always save data before exit'''
    await self.storage.save_json("cache.json", self.cache)
    logger.info("Data saved")
```

### 5. Handle Missing Files Gracefully

```python
async def load_data(self) -> dict:
    filepath = self.data_dir / "data.json"

    if not filepath.exists():
        logger.warning("No data file found, using defaults")
        return {}

    try:
        async with aiofiles.open(filepath) as f:
            return json.loads(await f.read())
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        return {}
```

---

## Complete Example

```python
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import AstrBotConfig, logger
from astrbot.core.utils.astrbot_path import get_astrbot_data_path
import aiofiles
import json
from pathlib import Path

class DataManager:
    '''Manages plugin data storage'''

    def __init__(self, plugin_name: str):
        self.data_dir = get_astrbot_data_path() / "plugin_data" / plugin_name
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, filename: str, data: dict):
        filepath = self.data_dir / filename
        async with aiofiles.open(filepath, 'w') as f:
            await f.write(json.dumps(data, indent=2))
        logger.debug(f"Saved {filename}")

    async def load(self, filename: str) -> dict:
        filepath = self.data_dir / filename
        if not filepath.exists():
            return {}

        async with aiofiles.open(filepath, 'r') as f:
            return json.loads(await f.read())

@register("data_plugin", "author", "Data storage example", "1.0.0")
class DataPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.data_manager = DataManager("data_plugin")
        self.user_data = {}

    async def initialize(self):
        '''Load saved data'''
        self.user_data = await self.data_manager.load("users.json")
        logger.info(f"Loaded {len(self.user_data)} user records")

    @filter.command("save_user")
    async def save_user(self, event: AstrMessageEvent, name: str, value: str):
        '''Save user data. Usage: /save_user <name> <value>'''

        user_id = event.get_sender_id()
        self.user_data[user_id] = {
            "name": name,
            "value": value,
            "timestamp": time.time()
        }

        await self.data_manager.save("users.json", self.user_data)
        yield event.plain_result(f"Saved data for {name}")

    @filter.command("get_user")
    async def get_user(self, event: AstrMessageEvent):
        '''Get user data'''

        user_id = event.get_sender_id()
        data = self.user_data.get(user_id)

        if data:
            yield event.plain_result(f"Name: {data['name']}, Value: {data['value']}")
        else:
            yield event.plain_result("No data found")

    async def terminate(self):
        '''Save before exit'''
        await self.data_manager.save("users.json", self.user_data)
        logger.info("User data saved")
```

---

## Checklist

- [ ] Use `get_astrbot_data_path()` for data storage
- [ ] Store data in `data/plugin_data/<plugin_name>/`
- [ ] Use async file operations (aiofiles)
- [ ] Create directories with `mkdir(parents=True, exist_ok=True)`
- [ ] Handle missing files gracefully
- [ ] Save data in `terminate()` method
- [ ] Use `_conf_schema.json` for user settings
- [ ] No custom database solutions
- [ ] No hardcoded file paths