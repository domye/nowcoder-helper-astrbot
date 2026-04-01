# Logging Guidelines

> How to use AstrBot's logger in plugins.

---

## Overview

AstrBot provides a built-in logger that plugins **must** use. Do not use Python's standard `logging` module.

**Key Benefits**:
- Unified logging format
- Integrated with AstrBot's log management
- Proper output routing (file, console, dashboard)
- Consistent log levels

---

## Importing the Logger

### Correct Import

```python
from astrbot import logger
```

### Wrong Import

```python
# ❌ WRONG: Don't use Python's logging module
import logging
logger = logging.getLogger(__name__)

# ❌ WRONG: Don't use print statements
print("Debug message")
```

---

## Log Levels

### Available Levels

| Level | Method | When to Use |
|-------|--------|-------------|
| DEBUG | `logger.debug()` | Detailed debugging info |
| INFO | `logger.info()` | General operational messages |
| WARNING | `logger.warning()` | Something unexpected, but not error |
| ERROR | `logger.error()` | Errors that don't crash plugin |
| CRITICAL | `logger.critical()` | Serious errors requiring attention |

### Usage Examples

```python
# DEBUG: Detailed info for troubleshooting
logger.debug(f"Processing message: {event.message_str}")

# INFO: Normal operations
logger.info("Plugin initialized successfully")

# WARNING: Recoverable issues
logger.warning("API token not configured, using defaults")

# ERROR: Operation failures
logger.error(f"API request failed: {e}")

# CRITICAL: Serious issues
logger.critical("Database connection lost, plugin disabled")
```

---

## Logging Patterns

### Pattern 1: Handler Logging

```python
@filter.command("query")
async def query(self, event: AstrMessageEvent, keyword: str):
    '''Query data'''
    sender = event.get_sender_name()

    logger.info(f"{sender} executing query: {keyword}")

    try:
        result = await self.api.query(keyword)
        logger.debug(f"Query result: {result}")
        yield event.plain_result(result)
    except Exception as e:
        logger.error(f"Query failed for {sender}: {e}")
        yield event.plain_result("Query failed")
```

### Pattern 2: Service Logging

```python
class APIClient:
    async def request(self, endpoint: str):
        logger.debug(f"Requesting: {endpoint}")

        try:
            response = await self.http.get(endpoint)
            logger.debug(f"Response status: {response.status}")
            return response.json()
        except ConnectionError as e:
            logger.error(f"Connection failed: {e}")
            raise
        except TimeoutError as e:
            logger.warning(f"Timeout on {endpoint}")
            raise
```

### Pattern 3: Lifecycle Logging

```python
@register("my_plugin", "author", "desc", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        logger.info("MyPlugin instance created")

    async def initialize(self):
        '''Initialize plugin'''
        logger.info("Initializing MyPlugin...")

        try:
            await self.setup_api()
            logger.info("API client ready")
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return

        logger.info("MyPlugin initialized successfully")

    async def terminate(self):
        '''Cleanup'''
        logger.info("MyPlugin terminating...")

        await self.cleanup()
        logger.info("MyPlugin terminated")
```

### Pattern 4: Background Task Logging

```python
async def background_worker(self):
    '''Background polling'''
    logger.info("Background worker started")

    while True:
        try:
            await asyncio.sleep(60)
            data = await self.poll_api()
            logger.debug(f"Poll result: {len(data)} items")

        except asyncio.CancelledError:
            logger.info("Background worker cancelled")
            break

        except Exception as e:
            logger.error(f"Background worker error: {e}")
            await asyncio.sleep(120)  # Wait longer

    logger.info("Background worker stopped")
```

---

## Logging Best Practices

### 1. Include Context

```python
# Bad: No context
logger.error("Failed")

# Good: With context
logger.error(f"API request failed for user {user_id}: {e}")

# Better: Full context
sender = event.get_sender_name()
logger.error(f"Query failed for {sender} (keyword={keyword}): {e}")
```

### 2. Use Appropriate Level

```python
# DEBUG: Internal details
logger.debug(f"Raw response: {response.text}")

# INFO: Normal operations
logger.info("User logged in")

# WARNING: Recoverable issues
logger.warning("Cache expired, fetching fresh data")

# ERROR: Operation failures
logger.error(f"Failed to save data: {e}")

# CRITICAL: System issues
logger.critical("Plugin cannot function without API token")
```

### 3. Log Exceptions with Traceback

```python
try:
    await operation()
except Exception as e:
    # Good: Includes traceback
    logger.error(f"Operation failed: {e}", exc_info=True)

    # Also good: Simple error log
    logger.error(f"Operation failed: {e}")
```

### 4. Log Important Events

```python
# Log when plugin starts
logger.info(f"{self.name} plugin loaded")

# Log when user triggers command
logger.info(f"Command {command_name} triggered by {sender}")

# Log when operation completes
logger.info(f"Processed {count} items in {duration}s")

# Log when plugin stops
logger.info(f"{self.name} plugin terminated")
```

### 5. Don't Over-log

```python
# Bad: Too verbose
logger.debug("Step 1")
logger.debug("Step 2")
logger.debug("Step 3")
logger.debug("Step 4")
logger.debug("Step 5")

# Good: Summary only
logger.debug(f"Completed 5 steps in {time}s")
```

---

## Common Logging Scenarios

### API Operations

```python
class APIClient:
    async def get(self, endpoint: str):
        logger.debug(f"GET {endpoint}")

        try:
            response = await self.request(endpoint)
            logger.debug(f"Got {len(response)} bytes")
            return response
        except ConnectionError:
            logger.error(f"Connection failed: {endpoint}")
            raise
```

### User Actions

```python
@filter.command("search")
async def search(self, event: AstrMessageEvent, query: str):
    '''Search'''
    sender = event.get_sender_name()

    logger.info(f"{sender} searches: {query}")

    results = await self.search_service.query(query)
    logger.info(f"{sender} got {len(results)} results")

    yield event.plain_result(results)
```

### Configuration Issues

```python
def __init__(self, context: Context, config: AstrBotConfig):
    super().__init__(context)

    self.token = config.get("api_token")
    if not self.token:
        logger.warning("api_token not set - plugin will have limited functionality")
```

### Error Recovery

```python
async def fetch_with_retry(self, url: str, max_retries: int = 3):
    '''Fetch with retry'''
    for attempt in range(max_retries):
        try:
            return await self.fetch(url)
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Attempt {attempt+1} failed, retrying: {e}")
                await asyncio.sleep(2 ** attempt)
            else:
                logger.error(f"All {max_retries} attempts failed: {e}")
                raise
```

### Background Tasks

```python
async def poll_service(self):
    '''Background polling'''
    logger.info("Started polling service")

    while True:
        try:
            await asyncio.sleep(300)
            data = await self.fetch_data()
            logger.info(f"Polled {len(data)} items")
        except asyncio.CancelledError:
            logger.info("Polling stopped")
            break
        except Exception as e:
            logger.error(f"Polling error: {e}")
```

---

## Anti-Patterns

### ❌ Wrong: Using print()

```python
# WRONG: Use logger, not print
async def handler(self, event):
    print(f"Received: {event.message_str}")  # Wrong!
    yield event.plain_result("Response")
```

**Why**: `print()` bypasses AstrBot's logging system, won't appear in dashboard.

### ❌ Wrong: Using logging module

```python
# WRONG: Don't use Python's logging
import logging

logger = logging.getLogger(__name__)  # Wrong!

async def handler(self, event):
    logger.info("Message")
```

**Why**: AstrBot's logger integrates with dashboard and log management.

### ❌ Wrong: No context in logs

```python
# WRONG: Insufficient context
logger.error("Failed")
logger.error("Error occurred")
```

**Correct**:
```python
logger.error(f"Query failed for {user}: {e}")
logger.error(f"API error code {code}: {message}")
```

### ❌ Wrong: Wrong log level

```python
# WRONG: Using ERROR for normal events
logger.error("User logged in")  # Should be INFO

# WRONG: Using INFO for errors
logger.info(f"Operation failed: {e}")  # Should be ERROR
```

### ❌ Wrong: Too verbose in production

```python
# WRONG: Too much DEBUG in handler
async def handler(self, event):
    logger.debug("Step 1")
    logger.debug("Step 2")
    logger.debug("Step 3")
    logger.debug("Checking condition")
    logger.debug("Processing data")
    # ...
```

**Correct**: Use INFO for high-level, DEBUG for troubleshooting only.

---

## Structured Logging

### Include Key Information

```python
@filter.command("query")
async def query(self, event: AstrMessageEvent, problem_id: str):
    '''Query problem'''
    # Key info: who, what, when
    sender = event.get_sender_name()
    sender_id = event.get_sender_id()

    logger.info(f"[{sender}] query problem: {problem_id}")

    try:
        result = await self.problem_service.query(problem_id)

        logger.info(
            f"[{sender}] query success - "
            f"problem_id={problem_id}, "
            f"result_size={len(result)}"
        )

        yield event.plain_result(result)
    except Exception as e:
        logger.error(
            f"[{sender}] query failed - "
            f"problem_id={problem_id}, "
            f"error={e}"
        )
        yield event.plain_result("Query failed")
```

### Log Format Convention

```python
# Pattern: [User] action - details
logger.info(f"[{sender}] executes command: {command}")
logger.error(f"[{sender}] operation failed: {e}")

# Pattern: Component: message
logger.info(f"API Client: Connected to {endpoint}")
logger.error(f"Cache: Failed to save {key}")
```

---

## Complete Example

```python
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import AstrBotConfig, logger
import asyncio

@register("logged_plugin", "author", "Logging example", "1.0.0")
class LoggedPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)

        logger.info("LoggedPlugin instance created")

        self.config = config
        self.token = config.get("api_token")

        if not self.token:
            logger.warning("api_token not configured")

        logger.debug(f"Config keys: {list(config.keys())}")

    async def initialize(self):
        '''Initialize'''
        logger.info("Initializing LoggedPlugin...")

        try:
            # Validate API
            valid = await self.validate_token()
            if not valid:
                logger.error("API token validation failed")
                return

            logger.info("API token valid")

            # Start background task
            asyncio.create_task(self.background_poll())
            logger.info("Background polling started")

        except Exception as e:
            logger.error(f"Initialization failed: {e}", exc_info=True)

        logger.info("LoggedPlugin initialized")

    @filter.command("query")
    async def query(self, event: AstrMessageEvent, keyword: str):
        '''Query data. Usage: /query <keyword>'''

        sender = event.get_sender_name()
        logger.info(f"[{sender}] query: {keyword}")

        # Validate
        if not self.token:
            logger.warning(f"[{sender}] query without token configured")
            yield event.plain_result("Plugin not configured")
            event.stop_event()
            return

        # Execute
        try:
            logger.debug(f"Fetching data for: {keyword}")
            result = await self.fetch_data(keyword)

            logger.info(f"[{sender}] query success - {len(result)} items")
            yield event.plain_result(result)

        except ConnectionError as e:
            logger.error(f"[{sender}] connection failed: {e}")
            yield event.plain_result("Network error")

        except TimeoutError as e:
            logger.warning(f"[{sender}] query timeout: {e}")
            yield event.plain_result("Request timed out")

        except Exception as e:
            logger.error(f"[{sender}] query failed: {e}", exc_info=True)
            yield event.plain_result("Query failed")

    async def background_poll(self):
        '''Background polling'''
        logger.info("Background poll started")

        while True:
            try:
                await asyncio.sleep(300)

                logger.debug("Polling API...")
                data = await self.poll_api()

                logger.info(f"Poll success - {len(data)} items")

            except asyncio.CancelledError:
                logger.info("Background poll cancelled")
                break

            except Exception as e:
                logger.error(f"Background poll error: {e}")
                await asyncio.sleep(600)

        logger.info("Background poll stopped")

    async def terminate(self):
        '''Cleanup'''
        logger.info("LoggedPlugin terminating...")

        # Cleanup
        await self.cleanup()

        logger.info("LoggedPlugin terminated")
```

---

## Checklist

- [ ] Import logger from `astrbot` (not `logging` module)
- [ ] No `print()` statements
- [ ] Appropriate log levels used
- [ ] Context included in error logs
- [ ] Important events logged (init, terminate, commands)
- [ ] Background tasks logged
- [ ] Exceptions logged with `exc_info=True` when needed
- [ ] Not over-logging in production handlers
- [ ] Structured format for complex operations