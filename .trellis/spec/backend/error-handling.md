# Error Handling

> Exception handling patterns for AstrBot plugins.

---

## Overview

AstrBot plugins must handle errors gracefully to avoid:
- Bot crashes affecting all users
- Silent failures that confuse users
- Unresponsive handlers blocking message flow

**Key Principles**:
- Catch exceptions in handlers
- Provide user-friendly error messages
- Log detailed errors for debugging
- Never let handlers crash silently

---

## Async Exception Handling

### Basic Pattern

```python
@filter.command("query")
async def query(self, event: AstrMessageEvent, keyword: str):
    '''Query data by keyword'''
    try:
        result = await self.api_client.query(keyword)
        yield event.plain_result(result)
    except Exception as e:
        logger.error(f"Query failed: {e}")
        yield event.plain_result("Query failed. Please try again.")
```

### Specific Exception Types

```python
from astrbot.api import logger

@filter.command("fetch")
async def fetch(self, event: AstrMessageEvent, url: str):
    '''Fetch data from URL'''
    try:
        data = await self.fetch_url(url)
        yield event.plain_result(data)
    except ConnectionError:
        logger.error(f"Connection failed: {url}")
        yield event.plain_result("Connection failed. Check network.")
    except TimeoutError:
        logger.error(f"Timeout: {url}")
        yield event.plain_result("Request timed out. Try again.")
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        yield event.plain_result("Invalid input provided.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        yield event.plain_result("An unexpected error occurred.")
```

---

## Error Response Patterns

### Pattern 1: User-Friendly Message + Log

```python
@filter.command("api_call")
async def api_call(self, event: AstrMessageEvent):
    '''Make API call'''
    try:
        response = await self.api.request()
        yield event.plain_result(f"Success: {response}")
    except APIError as e:
        # Log detailed error
        logger.error(f"API error {e.code}: {e.message}")

        # User-friendly message
        yield event.plain_result("Service temporarily unavailable.")
```

### Pattern 2: Graceful Degradation

```python
@filter.command("get_data")
async def get_data(self, event: AstrMessageEvent):
    '''Get data with fallback'''
    try:
        # Try primary source
        data = await self.fetch_from_api()
    except APIError:
        logger.warning("API unavailable, using cache")
        # Fallback to cache
        data = self.cache.get("last_data")

    if data:
        yield event.plain_result(data)
    else:
        yield event.plain_result("No data available.")
```

### Pattern 3: Retry with Backoff

```python
import asyncio

async def fetch_with_retry(self, url, max_retries=3):
    '''Fetch with exponential backoff'''
    for attempt in range(max_retries):
        try:
            return await self.fetch_url(url)
        except ConnectionError as e:
            if attempt == max_retries - 1:
                raise e
            wait_time = 2 ** attempt  # 1, 2, 4 seconds
            logger.warning(f"Retry {attempt+1} in {wait_time}s")
            await asyncio.sleep(wait_time)

@filter.command("retry_fetch")
async def retry_fetch(self, event: AstrMessageEvent):
    '''Fetch with retry'''
    try:
        data = await self.fetch_with_retry("https://api.example.com")
        yield event.plain_result(data)
    except Exception as e:
        logger.error(f"All retries failed: {e}")
        yield event.plain_result("Service unavailable after retries.")
```

---

## Validation Errors

### Input Validation Pattern

```python
@filter.command("set_limit")
async def set_limit(self, event: AstrMessageEvent, value: int):
    '''Set limit value'''
    # Validate input
    if value < 0:
        yield event.plain_result("Limit must be positive.")
        event.stop_event()
        return

    if value > 1000:
        yield event.plain_result("Limit too high (max 1000).")
        event.stop_event()
        return

    # Process valid input
    self.limit = value
    yield event.plain_result(f"Limit set to {value}")
```

### Permission Validation

```python
@filter.command("admin_cmd")
async def admin_cmd(self, event: AstrMessageEvent):
    '''Admin-only command'''
    sender_id = event.get_sender_id()

    # Check permission
    if sender_id not in self.config.get("admin_users", []):
        logger.warning(f"Unauthorized access by {sender_id}")
        yield event.plain_result("Permission denied.")
        event.stop_event()
        return

    # Process admin command
    result = await self.admin_operation()
    yield event.plain_result(result)
```

---

## Configuration Errors

### Missing Config Handling

```python
def __init__(self, context: Context, config: AstrBotConfig):
    super().__init__(context)

    # Check required config
    self.token = config.get("api_token")

    if not self.token:
        logger.error("api_token not configured")
        self.token = None

async def initialize(self):
    '''Validate configuration'''
    if not self.token:
        logger.warning("Plugin disabled: missing api_token")
        # Plugin will work but handlers should check
```

### Handler Config Check

```python
@filter.command("api_query")
async def api_query(self, event: AstrMessageEvent):
    '''Query API'''
    if not self.token:
        logger.error("No API token configured")
        yield event.plain_result("Plugin not configured. Contact admin.")
        event.stop_event()
        return

    # Proceed with query
    result = await self.query_api()
    yield event.plain_result(result)
```

---

## Background Task Errors

### Task Error Handling

```python
import asyncio

async def background_worker(self):
    '''Background task with error handling'''
    while True:
        try:
            await asyncio.sleep(60)
            data = await self.poll_api()
            self.update_cache(data)
        except asyncio.CancelledError:
            logger.info("Background task cancelled")
            break
        except Exception as e:
            logger.error(f"Background task error: {e}", exc_info=True)
            # Continue running despite error
            await asyncio.sleep(120)  # Wait longer before retry

def __init__(self, context: Context):
    super().__init__(context)
    self.task = asyncio.create_task(self.background_worker())

async def terminate(self):
    '''Cancel task gracefully'''
    self.task.cancel()
    try:
        await self.task
    except asyncio.CancelledError:
        logger.info("Task cancelled successfully")
```

---

## API Client Error Patterns

### Wrapped API Client

```python
class APIClient:
    async def request(self, endpoint):
        '''Request with error wrapping'''
        try:
            response = await self.http.get(endpoint)
            if response.status != 200:
                raise APIError(f"HTTP {response.status}")
            return response.json()
        except ConnectionError:
            raise APIError("Connection failed")
        except TimeoutError:
            raise APIError("Timeout")
        except JSONDecodeError:
            raise APIError("Invalid response format")

class APIError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)
```

### Usage in Handler

```python
@filter.command("fetch")
async def fetch(self, event: AstrMessageEvent):
    '''Fetch from API'''
    try:
        data = await self.api_client.request("/data")
        yield event.plain_result(data)
    except APIError as e:
        logger.error(f"API failed: {e.message}")
        yield event.plain_result(f"Error: {e.message}")
```

---

## Logging Errors

### Error Logging Patterns

```python
# Basic error log
logger.error(f"Operation failed: {e}")

# With exception traceback
logger.error(f"Unexpected error: {e}", exc_info=True)

# With context
logger.error(
    f"Query failed for user {event.get_sender_id()}: {e}",
    exc_info=True
)

# Warning for recoverable errors
logger.warning(f"Using fallback: {e}")
```

---

## Anti-Patterns

### ❌ Wrong: Silent Failure

```python
# WRONG: No error handling
@filter.command("cmd")
async def cmd(self, event: AstrMessageEvent):
    data = await self.fetch()  # Could crash
    yield event.plain_result(data)  # Never executed if fetch fails
```

### ❌ Wrong: No User Message

```python
# WRONG: User gets no feedback
@filter.command("cmd")
async def cmd(self, event: AstrMessageEvent):
    try:
        data = await self.fetch()
        yield event.plain_result(data)
    except Exception as e:
        logger.error(f"Error: {e}")
        # No yield - user gets nothing
```

### ❌ Wrong: Crashing Background Task

```python
# WRONG: Unhandled exception kills task
async def background_worker(self):
    while True:
        await asyncio.sleep(60)
        data = await self.poll_api()  # Could crash task
        self.process(data)
```

### ❌ Wrong: Broad Exception Without Log

```python
# WRONG: Silent catch
@filter.command("cmd")
async def cmd(self, event: AstrMessageEvent):
    try:
        # ...
    except:
        pass  # No logging, no response
```

---

## Best Practices

### 1. Always Provide User Feedback

```python
try:
    result = await operation()
    yield event.plain_result(result)
except Exception as e:
    logger.error(f"Error: {e}")
    yield event.plain_result("Operation failed.")  # ALWAYS respond
```

### 2. Log with Context

```python
sender = event.get_sender_name()
logger.error(f"Operation failed for {sender}: {e}", exc_info=True)
```

### 3. Use Specific Exception Types

```python
try:
    # ...
except ConnectionError:
    # Handle connection issues
except TimeoutError:
    # Handle timeouts
except ValueError:
    # Handle invalid input
except Exception as e:
    # Catch-all for unexpected errors
```

### 4. Handle Background Task Errors

```python
async def background_task(self):
    while True:
        try:
            # Task logic
        except asyncio.CancelledError:
            break  # Graceful shutdown
        except Exception as e:
            logger.error(f"Task error: {e}")
            await asyncio.sleep(60)  # Wait and retry
```

### 5. Validate Before Processing

```python
@filter.command("cmd")
async def cmd(self, event: AstrMessageEvent, param: str):
    # Validate first
    if not param:
        yield event.plain_result("Missing parameter")
        event.stop_event()
        return

    # Process
    try:
        result = await self.process(param)
        yield event.plain_result(result)
    except Exception as e:
        logger.error(f"Process failed: {e}")
        yield event.plain_result("Processing failed")
```

---

## Complete Example

```python
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import asyncio

class APIError(Exception):
    pass

@register("robust_plugin", "author", "Error handling example", "1.0.0")
class RobustPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.token = config.get("api_token")

        if not self.token:
            logger.warning("api_token not configured")

        self.task = asyncio.create_task(self.background_worker())

    async def fetch_with_retry(self, url, retries=3):
        '''Fetch with retry'''
        for i in range(retries):
            try:
                return await self.http_get(url)
            except Exception as e:
                if i == retries - 1:
                    raise APIError(f"All retries failed: {e}")
                wait = 2 ** i
                logger.warning(f"Retry {i+1} in {wait}s")
                await asyncio.sleep(wait)

    @filter.command("query")
    async def query(self, event: AstrMessageEvent, keyword: str):
        '''Query data. Usage: /query <keyword>'''

        # Check configuration
        if not self.token:
            yield event.plain_result("Plugin not configured.")
            event.stop_event()
            return

        # Validate input
        if len(keyword) > 50:
            yield event.plain_result("Keyword too long (max 50).")
            event.stop_event()
            return

        # Fetch with error handling
        try:
            data = await self.fetch_with_retry(f"https://api.example.com/search?q={keyword}")
            yield event.plain_result(f"Result: {data}")
        except APIError as e:
            logger.error(f"API error for {keyword}: {e}")
            yield event.plain_result("API unavailable. Try later.")
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            yield event.plain_result("An error occurred.")

    async def background_worker(self):
        '''Background task with error handling'''
        while True:
            try:
                await asyncio.sleep(300)
                await self.refresh_cache()
            except asyncio.CancelledError:
                logger.info("Background task cancelled")
                break
            except Exception as e:
                logger.error(f"Background error: {e}")
                await asyncio.sleep(600)  # Wait longer on error

    async def terminate(self):
        '''Cleanup'''
        self.task.cancel()
        try:
            await self.task
        except asyncio.CancelledError:
            pass
        logger.info("Plugin terminated")
```

---

## Checklist

- [ ] All handlers have try/except blocks
- [ ] Errors are logged with context
- [ ] User receives feedback on failure
- [ ] Specific exception types used when possible
- [ ] Background tasks handle asyncio.CancelledError
- [ ] Configuration errors checked in __init__ or initialize
- [ ] Validation before processing
- [ ] Graceful degradation where appropriate
- [ ] Retry logic for transient failures