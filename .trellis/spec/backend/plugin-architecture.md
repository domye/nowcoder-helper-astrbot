# Plugin Architecture

> AstrBot plugin core concepts: Star class, registration, and lifecycle.

---

## Overview

AstrBot plugins are Python classes that inherit from the `Star` base class. The plugin system provides:
- **Registration**: Via `@register` decorator
- **Lifecycle**: `initialize` and `terminate` hooks
- **Context**: Access to AstrBot's core components
- **Configuration**: User-customizable settings

---

## The Star Base Class

### Basic Structure

```python
from astrbot.api.star import Context, Star, register
from astrbot.api.event import filter, AstrMessageEvent

@register("plugin_name", "author", "description", "version")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        '''Called after plugin instantiation'''
        # Setup code here

    @filter.command("mycommand")
    async def mycommand(self, event: AstrMessageEvent):
        '''Handler description'''
        yield event.plain_result("Response")

    async def terminate(self):
        '''Called when plugin is unloaded/disabled'''
        # Cleanup code here
```

---

## Plugin Registration

### The @register Decorator

**Required parameters**:
```python
@register(
    "plugin_name",    # Unique identifier (lowercase, no spaces)
    "author_name",    # Your name or organization
    "description",    # Brief description of functionality
    "1.0.0",          # Version (semver recommended)
    "repo_url"        # Optional: GitHub repository URL
)
```

**Example**:
```python
@register("nowcoder_helper", "domye", "Nowcoder problem helper for AstrBot", "1.0.0", "https://github.com/domye/nowcoder-helper-astrbot")
class NowcoderHelperPlugin(Star):
    # ...
```

### Metadata Priority

AstrBot uses two sources for plugin metadata:

1. **metadata.yaml** (Higher priority)
2. **@register decorator** (Lower priority)

**Recommendation**: Use `metadata.yaml` for comprehensive metadata, `@register` for minimal info.

---

## Plugin Lifecycle

### Lifecycle Flow

```
Plugin Load → __init__() → initialize() → [Active] → terminate() → Plugin Unload
```

### 1. __init__() - Constructor

**Purpose**: Initialize plugin instance, store context and config.

**Signature**:
```python
def __init__(self, context: Context, config: AstrBotConfig = None):
    super().__init__(context)
    self.config = config  # Store config if provided
```

**Parameters**:
- `context: Context` - **Required**: AstrBot's core interface
- `config: AstrBotConfig` - **Optional**: Plugin configuration (if `_conf_schema.json` exists)

**Common patterns**:
```python
def __init__(self, context: Context, config: AstrBotConfig):
    super().__init__(context)

    # Store config
    self.config = config

    # Initialize services
    self.api_client = APIClient(config.get("api_token"))

    # Setup internal state
    self.cache = {}

    # Register background tasks
    asyncio.create_task(self.background_worker())
```

### 2. initialize() - Setup Hook

**Purpose**: Async initialization after instantiation.

**When called**: Automatically after `__init__()` completes.

**Signature**:
```python
async def initialize(self):
    '''Optional: Async initialization'''
    # Async setup code
```

**Use cases**:
- Async API validation
- Database connection setup
- Background task initialization
- Loading cached data

**Example**:
```python
async def initialize(self):
    # Validate API connection
    valid = await self.api_client.validate_token()
    if not valid:
        logger.warning("API token invalid")

    # Load cached data
    self.cache = await self.load_cache()

    logger.info("Plugin initialized successfully")
```

### 3. terminate() - Cleanup Hook

**Purpose**: Cleanup when plugin is disabled or unloaded.

**When called**: When user disables plugin or AstrBot shuts down.

**Signature**:
```python
async def terminate(self):
    '''Optional: Cleanup before unload'''
    # Cleanup code
```

**Use cases**:
- Save state to disk
- Close connections
- Cancel background tasks
- Clear temporary files

**Example**:
```python
async def terminate(self):
    # Save cache
    await self.save_cache(self.cache)

    # Close API connection
    await self.api_client.close()

    # Cancel background tasks
    for task in self.background_tasks:
        task.cancel()

    logger.info("Plugin terminated cleanly")
```

---

## The Context Object

### What is Context?

`Context` provides access to AstrBot's core components and APIs.

### Available APIs

```python
# Get all loaded plugins
plugins = self.context.get_all_stars()

# Get platform adapter (e.g., QQ adapter)
platform = self.context.get_platform(filter.PlatformAdapterType.AIOCQHTTP)

# Access configuration manager
config_manager = self.context.config_manager
```

### Platform Adapter Access

**Example** (requires AstrBot v3.4.34+):
```python
from astrbot.api.platform import AiocqhttpAdapter

@filter.command("test")
async def test_platform(self, event: AstrMessageEvent):
    # Get QQ platform adapter
    platform = self.context.get_platform(filter.PlatformAdapterType.AIOCQHTTP)

    if isinstance(platform, AiocqhttpAdapter):
        # Access native platform API
        client = platform.get_client()
        await client.api.call_action("some_action", params={...})
```

---

## Configuration System

### Configuration Schema (_conf_schema.json)

Define user-configurable settings:

```json
{
  "api_token": {
    "description": "API Token for authentication",
    "type": "string",
    "hint": "Enter your API token from the provider"
  },
  "retry_count": {
    "description": "Number of retry attempts",
    "type": "int",
    "default": 3,
    "hint": "How many times to retry on failure"
  },
  "advanced_settings": {
    "description": "Advanced configuration",
    "type": "object",
    "items": {
      "timeout": {
        "description": "Request timeout (seconds)",
        "type": "int",
        "default": 30
      },
      "debug_mode": {
        "description": "Enable debug logging",
        "type": "bool",
        "default": false
      }
    }
  }
}
```

### Using Configuration in Plugin

```python
from astrbot.api import AstrBotConfig

@register("my_plugin", "author", "desc", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

        # Access config values
        token = config.get("api_token")
        retries = config.get("retry_count", 3)  # Default fallback
        timeout = config.get("advanced_settings", {}).get("timeout", 30)
```

### Saving Configuration

```python
# Modify and save config
self.config["api_token"] = "new_token"
self.config.save_config()  # Persist to disk
```

**Config file location**: `data/config/<plugin_name>_config.json`

---

## Background Tasks

### Registering Async Tasks

**Pattern**: Use `asyncio.create_task()` in `__init__()` or `initialize()`.

```python
import asyncio

@register("task_plugin", "author", "desc", "1.0.0")
class TaskPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.background_tasks = []

        # Register background task
        task = asyncio.create_task(self.poll_api())
        self.background_tasks.append(task)

    async def poll_api(self):
        '''Background polling task'''
        while True:
            await asyncio.sleep(60)  # Poll every minute
            data = await self.fetch_data()
            await self.process_data(data)

    async def terminate(self):
        '''Cancel background tasks'''
        for task in self.background_tasks:
            task.cancel()
```

---

## Handler Requirements

### Handler Signature

All handlers **must** follow this signature:

```python
async def handler_name(self, event: AstrMessageEvent):
    '''Handler description (docstring)'''
    # Handler logic
    yield event.plain_result("Response")
```

**Requirements**:
- First parameter: `self` (instance)
- Second parameter: `event: AstrMessageEvent`
- Must be `async` function
- Must `yield` result (generator pattern)
- Must have docstring for description

### Handler Return Values

**Use yield (generator pattern)**:
```python
# CORRECT: Using yield
async def handler(self, event: AstrMessageEvent):
    yield event.plain_result("Text")

# WRONG: Using return (will not work)
async def handler(self, event: AstrMessageEvent):
    return event.plain_result("Text")  # Does not send message
```

---

## Anti-Patterns

### ❌ Wrong: Missing super().__init__()

```python
# WRONG
class MyPlugin(Star):
    def __init__(self, context: Context):
        # Missing super().__init__(context)
        self.config = {}
```

### ❌ Wrong: Sync Handlers

```python
# WRONG: Handler must be async
@filter.command("cmd")
def cmd_handler(self, event: AstrMessageEvent):  # Not async!
    yield event.plain_result("Text")
```

### ❌ Wrong: Using return Instead of yield

```python
# WRONG: Must use yield
@filter.command("cmd")
async def cmd_handler(self, event: AstrMessageEvent):
    return event.plain_result("Text")  # Does not send
```

### ❌ Wrong: Missing Docstring

```python
# WRONG: No description for help text
@filter.command("cmd")
async def cmd_handler(self, event: AstrMessageEvent):
    # Missing docstring - users won't understand command
    yield event.plain_result("Text")
```

---

## Best Practices

### 1. Always Call super().__init__()

```python
def __init__(self, context: Context, config: AstrBotConfig = None):
    super().__init__(context)  # REQUIRED
```

### 2. Use Docstrings for Handlers

```python
@filter.command("search")
async def search(self, event: AstrMessageEvent):
    '''Search for problems by keyword. Usage: /search <keyword>'''
    yield event.plain_result("Results...")
```

### 3. Handle Config Gracefully

```python
def __init__(self, context: Context, config: AstrBotConfig):
    super().__init__(context)

    # Check if config exists
    if config:
        self.token = config.get("token")
    else:
        self.token = None
        logger.warning("No config provided")
```

### 4. Clean Up in terminate()

```python
async def terminate(self):
    # Save state
    # Close connections
    # Cancel tasks
    logger.info(f"{self.name} terminated")
```

---

## Complete Example

```python
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import AstrBotConfig, logger
import asyncio

@register("complete_example", "Author", "A complete plugin example", "1.0.0")
class CompleteExamplePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.api_client = None
        self.cache = {}
        self.tasks = []

    async def initialize(self):
        '''Initialize API client and cache'''
        token = self.config.get("api_token")
        self.api_client = APIClient(token)

        # Validate connection
        connected = await self.api_client.connect()
        if not connected:
            logger.error("Failed to connect to API")
            return

        # Start background task
        task = asyncio.create_task(self.refresh_cache())
        self.tasks.append(task)

        logger.info("Plugin initialized")

    @filter.command("query")
    async def query(self, event: AstrMessageEvent, keyword: str):
        '''Query data by keyword. Usage: /query <keyword>'''
        result = await self.api_client.query(keyword)
        yield event.plain_result(result)

    async def refresh_cache(self):
        '''Background task to refresh cache'''
        while True:
            await asyncio.sleep(300)  # Every 5 minutes
            self.cache = await self.api_client.fetch_all()

    async def terminate(self):
        '''Cleanup before unload'''
        # Save cache
        await self.save_cache()

        # Close API connection
        await self.api_client.close()

        # Cancel background tasks
        for task in self.tasks:
            task.cancel()

        logger.info("Plugin terminated")
```

---

## Checklist

- [ ] Star class inherits from `Star`
- [ ] `@register` decorator with all required params
- [ ] `super().__init__(context)` called in `__init__`
- [ ] Handlers are async and use yield
- [ ] Handlers have descriptive docstrings
- [ ] `terminate()` implemented for cleanup (if needed)
- [ ] Background tasks registered with `asyncio.create_task()`
- [ ] Background tasks cancelled in `terminate()`