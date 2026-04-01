# Event Handling

> How to handle messages and events in AstrBot plugins.

---

## Overview

AstrBot provides a flexible event handling system through **filter decorators**. Handlers can:
- Respond to commands (e.g., `/help`)
- Listen to message events (all, private, group)
- Filter by message type or content
- Control event propagation

---

## Importing Event Components

**Critical**: Import `filter` from `astrbot.api.event` to avoid conflicts with Python's built-in `filter`.

```python
from astrbot.api.event import filter, AstrMessageEvent
```

---

## Handler Signature

All handlers **must** follow this pattern:

```python
@filter.<decorator_type>(<params>)
async def handler_name(self, event: AstrMessageEvent):
    '''Handler description (required docstring)'''
    # Handler logic
    yield event.plain_result("Response")  # MUST use yield
```

**Requirements**:
- ✅ Async function (`async def`)
- ✅ Parameters: `self`, `event: AstrMessageEvent`
- ✅ Docstring for description (shown in help)
- ✅ Yield result (generator pattern)

---

## Command Handlers

### Basic Command

```python
@filter.command("helloworld")
async def helloworld(self, event: AstrMessageEvent):
    '''Say hello to the user'''
    user_name = event.get_sender_name()
    yield event.plain_result(f"Hello, {user_name}!")
```

**Usage**: User sends `/helloworld`

### Command with Parameters

```python
@filter.command("search")
async def search(self, event: AstrMessageEvent, keyword: str):
    '''Search by keyword. Usage: /search <keyword>'''
    result = await self.search_api(keyword)
    yield event.plain_result(result)
```

**Usage**: User sends `/search problem_name`

**Type hints**: AstrBot auto-parses parameters based on type hints:
- `str` - String parameter
- `int` - Integer parameter
- `float` - Float parameter

### Command Group (Subcommands)

Organize related commands under a group:

```python
@filter.command_group("math")
def math(self):
    '''Math operations group'''
    pass

@math.command("add")
async def add(self, event: AstrMessageEvent, a: int, b: int):
    '''Add two numbers. Usage: /math add <a> <b>'''
    yield event.plain_result(f"Result: {a + b}")

@math.command("sub")
async def sub(self, event: AstrMessageEvent, a: int, b: int):
    '''Subtract two numbers. Usage: /math sub <a> <b>'''
    yield event.plain_result(f"Result: {a - b}")
```

**Usage**:
- `/math add 1 2` → "Result: 3"
- `/math sub 5 3` → "Result: 2"

---

## Event Type Handlers

### Filter by Message Type

```python
# Listen to ALL messages
@filter.event_message_type(filter.EventMessageType.ALL)
async def on_all_message(self, event: AstrMessageEvent):
    '''Process every message'''
    logger.info(f"Received: {event.message_str}")
    yield event.plain_result("Message received")

# Listen to PRIVATE messages only
@filter.event_message_type(filter.EventMessageType.PRIVATE_MESSAGE)
async def on_private_message(self, event: AstrMessageEvent):
    '''Process private messages'''
    yield event.plain_result("Private message received")

# Listen to GROUP messages only
@filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
async def on_group_message(self, event: AstrMessageEvent):
    '''Process group messages'''
    yield event.plain_result("Group message received")
```

### Event Types Available

| Type | Constant | Description |
|------|----------|-------------|
| All Messages | `filter.EventMessageType.ALL` | All incoming messages |
| Private | `filter.EventMessageType.PRIVATE_MESSAGE` | Direct messages to bot |
| Group | `filter.EventMessageType.GROUP_MESSAGE` | Messages in group chats |

---

## Regex Filters

### Match by Pattern

```python
@filter.regex(r"^问题\s+(.+)$")
async def handle_problem_query(self, event: AstrMessageEvent):
    '''Query problem by pattern'''
    match = event.message_str.match(r"^问题\s+(.+)$")
    if match:
        keyword = match.group(1)
        result = await self.query_problem(keyword)
        yield event.plain_result(result)
```

---

## Message Components

### Accessing Message Data

```python
@filter.command("info")
async def info(self, event: AstrMessageEvent):
    '''Show message information'''
    # Pure text content
    message_str = event.message_str

    # Sender info
    sender_name = event.get_sender_name()
    sender_id = event.get_sender_id()

    # Full message chain (components)
    message_chain = event.get_messages()

    # Original message object
    message_obj = event.message_obj

    yield event.plain_result(f"From: {sender_name} ({sender_id})")
```

### Sending Plain Text

```python
yield event.plain_result("Simple text response")
```

### Sending Rich Messages (MessageChain)

```python
import astrbot.api.message_components as Comp

@filter.command("rich")
async def rich_message(self, event: AstrMessageEvent):
    '''Send rich message with components'''
    chain = [
        Comp.At(qq=event.get_sender_id()),  # Mention sender
        Comp.Plain("Look at this image:"),
        Comp.Image.fromURL("https://example.com/image.jpg"),
        Comp.Image.fromFileSystem("data/plugin_data/my_plugin/image.png"),
        Comp.Plain("End of message.")
    ]
    yield event.chain_result(chain)
```

### Available Components

| Component | Usage | Description |
|-----------|-------|-------------|
| `Plain` | `Comp.Plain("text")` | Plain text |
| `At` | `Comp.At(qq=12345)` | Mention user (QQ) |
| `Image` | `Comp.Image.fromURL(url)` | Image from URL |
| `Image` | `Comp.Image.fromFileSystem(path)` | Image from file |
| `Record` | `Comp.Record(file=path)` | Voice/audio |

---

## Event Propagation Control

### Stop Event Propagation

Prevent subsequent handlers from executing:

```python
@filter.command("check")
async def check(self, event: AstrMessageEvent):
    '''Check condition and stop if failed'''
    valid = self.validate_input(event.message_str)

    if not valid:
        yield event.plain_result("Validation failed")
        event.stop_event()  # Stop propagation
        return

    # Continue processing
    result = await self.process(event.message_str)
    yield event.plain_result(result)
```

**Use cases**:
- Permission checks
- Input validation
- Rate limiting
- Command blocking

---

## Platform-Specific Access

### Get Platform Adapter (Advanced)

Access native platform APIs (requires AstrBot v3.4.34+):

```python
from astrbot.api.platform import AiocqhttpAdapter

@filter.command("platform_test")
async def platform_test(self, event: AstrMessageEvent):
    '''Test platform API access'''
    platform = self.context.get_platform(filter.PlatformAdapterType.AIOCQHTTP)

    if isinstance(platform, AiocqhttpAdapter):
        client = platform.get_client()
        # Call native QQ API
        await client.api.call_action("get_group_member_list", group_id=12345)

    yield event.plain_result("Platform API called")
```

---

## Complete Handler Examples

### Example 1: Simple Command with Validation

```python
@register("simple_cmd", "author", "Simple command example", "1.0.0")
class SimpleCmdPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("echo")
    async def echo(self, event: AstrMessageEvent, text: str):
        '''Echo back the text. Usage: /echo <text>'''
        if len(text) > 100:
            yield event.plain_result("Text too long (max 100 chars)")
            event.stop_event()
            return

        yield event.plain_result(f"Echo: {text}")
```

### Example 2: Event Listener with Logging

```python
@register("message_logger", "author", "Log all messages", "1.0.0")
class MessageLoggerPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def log_all(self, event: AstrMessageEvent):
        '''Log all incoming messages'''
        sender = event.get_sender_name()
        content = event.message_str
        logger.info(f"[{sender}] {content}")

        # Don't respond - just log
        # Use yield event.plain_result() if you want to respond
```

### Example 3: Group Command with Rich Response

```python
import astrbot.api.message_components as Comp

@register("group_helper", "author", "Group chat helper", "1.0.0")
class GroupHelperPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("stats")
    async def stats(self, event: AstrMessageEvent):
        '''Show group statistics'''
        # Build rich message
        chain = [
            Comp.Plain("📊 Group Statistics:\n"),
            Comp.Plain(f"Messages: {self.get_message_count()}\n"),
            Comp.Plain(f"Members: {self.get_member_count()}")
        ]

        yield event.chain_result(chain)
```

---

## Anti-Patterns

### ❌ Wrong: Sync Handler

```python
# WRONG: Handler must be async
@filter.command("cmd")
def cmd_handler(self, event: AstrMessageEvent):
    yield event.plain_result("Text")
```

### ❌ Wrong: Using return

```python
# WRONG: Must use yield, not return
@filter.command("cmd")
async def cmd_handler(self, event: AstrMessageEvent):
    return event.plain_result("Text")
```

### ❌ Wrong: Missing Docstring

```python
# WRONG: No docstring = no help text
@filter.command("cmd")
async def cmd_handler(self, event: AstrMessageEvent):
    yield event.plain_result("Text")
```

### ❌ Wrong: Wrong Import

```python
# WRONG: Conflicts with Python's built-in filter
from astrbot.api import filter  # Wrong location

# CORRECT
from astrbot.api.event import filter  # Correct location
```

### ❌ Wrong: Wrong Parameters

```python
# WRONG: Missing self or event
@filter.command("cmd")
async def cmd_handler(event: AstrMessageEvent):
    yield event.plain_result("Text")

# CORRECT
@filter.command("cmd")
async def cmd_handler(self, event: AstrMessageEvent):
    yield event.plain_result("Text")
```

---

## Best Practices

### 1. Always Add Docstrings

```python
@filter.command("search")
async def search(self, event: AstrMessageEvent, keyword: str):
    '''Search problems by keyword. Usage: /search <keyword>'''
    # Implementation
```

### 2. Use Type Hints for Parameters

```python
# Good: AstrBot auto-parses based on type hints
@filter.command("set_limit")
async def set_limit(self, event: AstrMessageEvent, limit: int):
    '''Set limit. Usage: /set_limit <number>'''
    yield event.plain_result(f"Limit set to {limit}")
```

### 3. Validate Before Processing

```python
@filter.command("query")
async def query(self, event: AstrMessageEvent, keyword: str):
    '''Query data'''
    if not keyword:
        yield event.plain_result("Please provide a keyword")
        event.stop_event()
        return

    # Proceed with query
    result = await self.query_api(keyword)
    yield event.plain_result(result)
```

### 4. Log Important Events

```python
@filter.command("important_cmd")
async def important_cmd(self, event: AstrMessageEvent):
    '''Important command with logging'''
    sender = event.get_sender_name()
    logger.info(f"{sender} executed important_cmd")

    # Process
    yield event.plain_result("Done")
```

---

## Event Object Properties

### AstrMessageEvent Properties

| Property | Type | Description |
|----------|------|-------------|
| `message_str` | `str` | Pure text content |
| `message_obj` | `AstrBotMessage` | Full message object |
| `session_id` | `str` | Session identifier |

### AstrMessageEvent Methods

| Method | Return | Description |
|--------|--------|-------------|
| `get_sender_name()` | `str` | Sender's display name |
| `get_sender_id()` | `str/int` | Sender's unique ID |
| `get_messages()` | `MessageChain` | Get message components |
| `plain_result(text)` | `MessageEventResult` | Create text response |
| `chain_result(chain)` | `MessageEventResult` | Create rich response |
| `stop_event()` | `None` | Stop propagation |

---

## Checklist

- [ ] Import `filter` from `astrbot.api.event`
- [ ] Handlers are async functions
- [ ] Handlers have `self` and `event: AstrMessageEvent` parameters
- [ ] Handlers use `yield` (not `return`)
- [ ] Handlers have descriptive docstrings
- [ ] Type hints used for command parameters
- [ ] Validation before processing
- [ ] Event propagation controlled with `stop_event()` when needed