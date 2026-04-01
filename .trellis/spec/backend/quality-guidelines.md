# Quality Guidelines

> Code quality standards for AstrBot plugin development.

---

## Overview

AstrBot plugins should follow Python best practices with emphasis on:
- Async/await patterns
- Clean code structure
- Type safety
- Error handling
- Maintainability

---

## Python Standards

### Code Style

Follow **PEP 8** with these AstrBot-specific conventions:

```python
# Good: Clear naming, async pattern
@filter.command("query_problem")
async def query_problem(self, event: AstrMessageEvent, problem_id: str):
    '''Query a problem by ID. Usage: /query_problem <id>'''
    result = await self.problem_service.query(problem_id)
    yield event.plain_result(result)

# Bad: Sync, unclear naming
@filter.command("query")
def q(self, e, id):  # Sync, short names, no docstring
    return e.plain_result(self.query(id))
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Plugin class | PascalCase | `NowcoderHelperPlugin` |
| Handlers | snake_case | `query_problem`, `fetch_data` |
| Services | PascalCase | `APIClient`, `ProblemService` |
| Variables | snake_case | `problem_id`, `user_name` |
| Constants | UPPER_SNAKE_CASE | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |

---

## Async Best Practices

### 1. Use async/await Consistently

```python
# Good: Async throughout
async def fetch_data(self, url: str) -> str:
    response = await self.http_client.get(url)
    return response.text

async def process(self, data: str) -> dict:
    parsed = self.parse(data)
    return await self.save(parsed)

@filter.command("fetch")
async def fetch(self, event: AstrMessageEvent):
    data = await self.fetch_data("https://api.example.com")
    result = await self.process(data)
    yield event.plain_result(result)
```

### 2. Avoid Blocking Operations

```python
# Bad: Blocking I/O
async def handler(self, event: AstrMessageEvent):
    with open("file.txt") as f:  # Blocking!
        data = f.read()
    yield event.plain_result(data)

# Good: Use aiofiles or asyncio
import aiofiles

async def handler(self, event: AstrMessageEvent):
    async with aiofiles.open("file.txt") as f:
        data = await f.read()
    yield event.plain_result(data)
```

### 3. Use asyncio.create_task for Background Work

```python
def __init__(self, context: Context):
    super().__init__(context)
    # Start background task
    asyncio.create_task(self.poll_service())

async def poll_service(self):
    '''Background polling'''
    while True:
        await asyncio.sleep(60)
        await self.refresh_data()
```

### 4. Handle Task Cancellation

```python
async def background_task(self):
    '''Task that handles cancellation'''
    while True:
        try:
            await asyncio.sleep(60)
            await self.work()
        except asyncio.CancelledError:
            logger.info("Task cancelled")
            break  # Exit cleanly

async def terminate(self):
    '''Cancel tasks on shutdown'''
    self.background_task.cancel()
```

### 5. Use aiohttp for HTTP Requests

**CRITICAL**: Never use `requests` in async code. Use `aiohttp` or `httpx`.

```python
# ❌ WRONG: requests is blocking
import requests

async def fetch_data(self, url: str):
    response = requests.get(url)  # Blocks the event loop!
    return response.json()

# ✅ CORRECT: aiohttp is async
import aiohttp

async def fetch_data(self, url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()

# ✅ CORRECT: Reuse session for multiple requests
async def fetch_multiple(self, urls: list) -> list:
    results = []
    async with aiohttp.ClientSession() as session:
        for url in urls:
            async with session.get(url) as resp:
                results.append(await resp.json())
    return results
```

### 6. Use Dataclasses for Data Models

```python
from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class Article:
    """文章数据模型"""
    id: str
    title: str
    author: str
    content: str
    url: str
    post_time: Optional[str] = None
    view_count: int = 0
    like_count: int = 0
    feed_images: List[str] = field(default_factory=list)

# Usage
article = Article(
    id="123",
    title="Title",
    author="Author",
    content="Content",
    url="https://..."
)
print(article.title)  # Direct attribute access
```

---

## Function Size Limits

### Handler Functions

**Maximum**: 50 lines of logic

```python
# Good: Delegated to service
@filter.command("complex_query")
async def complex_query(self, event: AstrMessageEvent, query: str):
    '''Complex query operation'''
    result = await self.query_service.process_complex(query)
    yield event.plain_result(result)

# In services/query_service.py (separate file)
class QueryService:
    async def process_complex(self, query: str):
        # Complex logic here (can be longer)
        step1 = await self.step1(query)
        step2 = await self.step2(step1)
        return self.format(step2)
```

### Service Functions

**Maximum**: 100 lines (complex business logic)

**Rule**: If function > 100 lines, split into sub-functions.

---

## File Size Limits

| File Type | Maximum Lines | Action if Exceeded |
|-----------|---------------|-------------------|
| `main.py` | 200 | Extract to services/ |
| Service files | 300 | Split into multiple services |
| Utility files | 150 | Keep minimal |

### When to Split main.py

```python
# main.py becoming too large (>200 lines)
@register("plugin", "author", "desc", "1.0.0")
class Plugin(Star):
    # 50 lines of handlers...

    # 150 lines of business logic...
    async def fetch_api(self):
        # ...
    async def process_data(self):
        # ...
    async def format_output(self):
        # ...
```

**Solution**:
```
plugin/
├── main.py               # Handlers only (50 lines)
└── services/
    ├── api_client.py     # fetch_api moved here
    ├── processor.py      # process_data moved here
    └── formatter.py      # format_output moved here
```

---

## Type Safety

### Use Type Hints

```python
# Good: Full type hints
from typing import Optional, Dict, List

async def fetch_problem(self, problem_id: str) -> Optional[Dict]:
    response = await self.api.get(f"/problems/{problem_id}")
    return response.json()

async def get_user_problems(self, user_id: int) -> List[Dict]:
    return await self.api.get(f"/users/{user_id}/problems")

@filter.command("query")
async def query(self, event: AstrMessageEvent, problem_id: str):
    '''Query problem'''
    problem: Optional[Dict] = await self.fetch_problem(problem_id)
    if problem:
        yield event.plain_result(str(problem))
```

### Handler Type Hints

```python
# Parameters auto-parsed based on type hints
@filter.command("set_limit")
async def set_limit(self, event: AstrMessageEvent, limit: int):
    '''Set limit (parsed as int)'''
    # AstrBot parses limit as integer automatically
    self.limit = limit
    yield event.plain_result(f"Limit: {limit}")

@filter.command("search")
async def search(self, event: AstrMessageEvent, keyword: str):
    '''Search (parsed as str)'''
    # AstrBot parses keyword as string
    yield event.plain_result(await self.search(keyword))
```

---

## Code Organization

### Single Responsibility Principle

```python
# Good: One responsibility per class
class APIClient:
    '''Handles API communication only'''
    async def get(self, endpoint: str) -> dict:
        # ...

class DataProcessor:
    '''Processes data only'''
    def parse(self, raw: str) -> dict:
        # ...

class Formatter:
    '''Formats output only'''
    def format(self, data: dict) -> str:
        # ...

# In main.py - orchestrates services
@register("plugin", "author", "desc", "1.0.0")
class Plugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.api = APIClient()
        self.processor = DataProcessor()
        self.formatter = Formatter()
```

### Dependency Injection Pattern

```python
# Services initialized with dependencies
class ProblemService:
    def __init__(self, api_client: APIClient, cache: CacheManager):
        self.api = api_client
        self.cache = cache

# In main.py
def __init__(self, context: Context, config: AstrBotConfig):
    super().__init__(context)
    api_client = APIClient(config.get("api_token"))
    cache = CacheManager()
    self.problem_service = ProblemService(api_client, cache)
```

---

## Error Handling Standards

### Required: Try/Except in All Handlers

```python
@filter.command("operation")
async def operation(self, event: AstrMessageEvent):
    '''Perform operation'''
    try:
        result = await self.do_operation()
        yield event.plain_result(result)
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        yield event.plain_result("Operation failed")
```

### Specific Exception Types

```python
try:
    result = await operation()
except ConnectionError as e:
    logger.error(f"Connection: {e}")
    yield event.plain_result("Network error")
except TimeoutError as e:
    logger.error(f"Timeout: {e}")
    yield event.plain_result("Timeout")
except ValueError as e:
    logger.error(f"Invalid: {e}")
    yield event.plain_result("Invalid input")
except Exception as e:
    logger.error(f"Unexpected: {e}", exc_info=True)
    yield event.plain_result("Unexpected error")
```

---

## Testing Requirements

### Minimum Coverage

- **Handlers**: 100% (must test all handlers)
- **Services**: 80% minimum
- **Utilities**: 90% minimum

### Test File Organization

```
plugin/
├── main.py
├── services/
│   └── api_client.py
└── tests/
    ├── test_handlers.py      # Handler tests
    ├── test_api_client.py    # Service tests
    └── test_utils.py         # Utility tests
```

### Example Test

```python
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
async def test_query_handler():
    # Setup
    context = Mock()
    event = Mock(spec=AstrMessageEvent)
    event.message_str = "/query test"
    event.get_sender_name.return_value = "user"

    plugin = MyPlugin(context)

    # Execute
    result = await plugin.query(event, "test")

    # Assert
    assert result is not None
```

---

## Forbidden Patterns

### ❌ Global State

```python
# WRONG: Global variables
cache = {}  # Global!

@register("plugin", "author", "desc", "1.0.0")
class Plugin(Star):
    async def handler(self, event):
        cache[event.get_sender_id()] = event.message_str
```

**Why**: Multiple plugin instances, race conditions.

**Correct**:
```python
class Plugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.cache = {}  # Instance variable
```

### ❌ Blocking Sleep

```python
# WRONG: Blocking sleep
import time

async def handler(self, event):
    time.sleep(5)  # Blocks all async operations!
```

**Correct**:
```python
async def handler(self, event):
    await asyncio.sleep(5)  # Async sleep
```

### ❌ Return Instead of Yield

```python
# WRONG: Using return
async def handler(self, event):
    return event.plain_result("text")
```

**Correct**:
```python
async def handler(self, event):
    yield event.plain_result("text")
```

### ❌ Sync in Async Context

```python
# WRONG: Sync operation in async
async def handler(self, event):
    data = requests.get(url)  # Sync HTTP!
```

**Correct**:
```python
async def handler(self, event):
    data = await self.http_client.get(url)  # Async HTTP
```

### ❌ Missing Docstrings

```python
# WRONG: No documentation
@filter.command("cmd")
async def cmd(self, event):
    yield event.plain_result("text")
```

**Correct**:
```python
@filter.command("cmd")
async def cmd(self, event):
    '''Command description. Usage: /cmd <param>'''
    yield event.plain_result("text")
```

### ❌ Deep Nesting

```python
# WRONG: >4 levels of nesting
async def handler(self, event):
    if condition1:
        if condition2:
            if condition3:
                if condition4:
                    if condition5:
                        yield event.plain_result("...")
```

**Correct**: Extract logic, use early returns.

---

## Linting Standards

### Use Ruff or Flake8

```bash
# Install
pip install ruff

# Run
ruff check .
ruff format .
```

### Recommended Rules

- `E` - PEP 8 errors
- `F` - Pyflakes
- `I` - Isort
- `W` - PEP 8 warnings
- `C90` - McCabe complexity (max 10)
- `UP` - Pyupgrade

### Configuration (ruff.toml)

```toml
line-length = 100
select = ["E", "F", "I", "W", "C90", "UP"]

[per-file-ignores]
"tests/*" = ["F401"]  # Unused imports in tests
```

---

## Code Review Checklist

Before committing, verify:

- [ ] All handlers have docstrings
- [ ] All handlers use async/await
- [ ] All handlers use yield (not return)
- [ ] Type hints on all functions
- [ ] Error handling in all handlers
- [ ] No global variables
- [ ] No blocking operations in async
- [ ] Files under size limits
- [ ] Functions under complexity limit
- [ ] Linting passes (ruff/flake8)
- [ ] Tests pass
- [ ] Background tasks handle cancellation

---

## Best Practices Summary

### 1. Keep main.py Minimal

```python
# main.py - handlers only
@register("plugin", "author", "desc", "1.0.0")
class Plugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.service = PluginService(config)

    @filter.command("cmd")
    async def cmd(self, event: AstrMessageEvent):
        '''Handler delegating to service'''
        result = await self.service.handle(event)
        yield event.plain_result(result)
```

### 2. Use Services for Logic

```python
# services/plugin_service.py
class PluginService:
    async def handle(self, event: AstrMessageEvent) -> str:
        # Business logic here
        data = await self.fetch()
        processed = self.process(data)
        return self.format(processed)
```

### 3. Test Everything

```python
# tests/test_service.py
@pytest.mark.asyncio
async def test_service_handle():
    service = PluginService(config)
    result = await service.handle(mock_event)
    assert result is not None
```

---

## Quality Checklist

### Code Structure
- [ ] Files under size limits (main.py < 200 lines)
- [ ] Functions under complexity limit (McCabe < 10)
- [ ] Services extracted for logic > 50 lines
- [ ] Single responsibility per class/function

### Async Patterns
- [ ] All handlers are async
- [ ] All I/O is async (no blocking)
- [ ] Background tasks use asyncio.create_task
- [ ] Background tasks handle CancelledError

### Error Handling
- [ ] Try/except in all handlers
- [ ] User feedback on all errors
- [ ] Logged errors with context
- [ ] Graceful degradation where appropriate

### Documentation
- [ ] All handlers have docstrings
- [ ] Type hints on all functions
- [ ] README if complex plugin

### Testing
- [ ] Handlers tested (100%)
- [ ] Services tested (80%+)
- [ ] Edge cases covered

### Linting
- [ ] Ruff/flake8 passes
- [ ] No PEP 8 violations
- [ ] Imports organized