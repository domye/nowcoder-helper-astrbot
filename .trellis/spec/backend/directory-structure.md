# Directory Structure

> How AstrBot plugin files are organized.

---

## Overview

AstrBot plugins follow a standardized directory structure. The main entry point must be `main.py`.

---

## Standard Plugin Layout

```
your_plugin/
├── main.py                   # Required: Plugin entry point (Star class)
├── metadata.yaml             # Required: Plugin metadata
├── _conf_schema.json         # Optional: Configuration schema
├── logo.png                  # Optional: Plugin logo
├── services/                 # Optional: Business logic modules
│   ├── __init__.py
│   ├── api_client.py
│   └── data_processor.py
├── utils/                    # Optional: Helper functions
│   ├── __init__.py
│   └── helpers.py
└── README.md                 # Optional: Documentation
```

---

## Critical Files

### 1. `main.py` (Required)

**Must contain**:
- Star class inheriting from `Star`
- `@register` decorator for plugin registration
- Handler functions with `@filter` decorators

**Naming**: MUST be exactly `main.py` - AstrBot looks for this filename.

**Example**:
```python
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot import logger

@register("my_plugin", "YourName", "Plugin description", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("mycommand")
    async def mycommand(self, event: AstrMessageEvent):
        '''Handler description'''
        yield event.plain_result("Response")
```

### 2. `metadata.yaml` (Required)

Plugin metadata for marketplace and management.

```yaml
name: "my_plugin"
version: "1.0.0"
author: "Your Name"
description: "Brief plugin description"
display_name: "My Plugin"
logo: "logo.png"
```

### 3. `_conf_schema.json` (Optional)

Configuration schema for user-customizable settings.

```json
{
  "token": {
    "description": "API Token",
    "type": "string"
  },
  "retry_count": {
    "description": "Retry attempts",
    "type": "int",
    "default": 3
  }
}
```

---

## Data Storage Paths

AstrBot provides standardized paths for plugin data:

### Plugin Configuration
- **Path**: `data/config/<plugin_name>_config.json`
- **Access**: Via `AstrBotConfig` in `__init__`

### Plugin Data Files
- **Path**: `data/plugin_data/<plugin_name>/`
- **Access**: Use `get_astrbot_data_path()` utility

```python
from pathlib import Path
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

# Get plugin data directory
# Note: get_astrbot_data_path() returns string, wrap with Path
plugin_data_path = Path(get_astrbot_data_path()) / "plugin_data" / self.name
sessions_file = plugin_data_path / "sessions.json"

# Ensure directory exists
plugin_data_path.mkdir(parents=True, exist_ok=True)
```

---

## Module Organization Patterns

### Pattern 1: Simple Plugin (Single File)

For plugins with minimal logic:

```python
# main.py - Everything in one file (<100 lines)
@register("simple_plugin", "Author", "Description", "1.0.0")
class SimplePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("cmd")
    async def cmd_handler(self, event: AstrMessageEvent):
        # Logic here
        yield event.plain_result("Result")
```

### Pattern 2: Moderate Plugin (Services Module)

For plugins with external APIs or complex logic:

```
my_plugin/
├── main.py
├── metadata.yaml
├── _conf_schema.json
└── services/
    ├── __init__.py
    ├── api_client.py      # External API calls (sync)
    ├── api_client_async.py # External API calls (async, recommended)
    ├── parser.py          # Data parsing
    └── models.py          # Data models (dataclass)
```

**main.py imports**:
```python
from .services.api_client_async import fetch_article, fetch_search_results
from .services.models import Article, SearchResult

@register("moderate_plugin", "Author", "Description", "1.0.0")
class ModeratePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.api_client = APIClient(config.get("token"))
```

**services/models.py** (Data Models):
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
```

**services/api_client_async.py** (Async API Client):
```python
import aiohttp
from .models import Article

async def fetch_article(url: str) -> Article:
    """异步获取文章"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return Article(**parse_data(data))
```

### Pattern 3: Complex Plugin (Full Structure)

For plugins with multiple features:

```
complex_plugin/
├── main.py                  # Entry + command routing
├── metadata.yaml
├── _conf_schema.json
├── handlers/                # Event handlers
│   ├── __init__.py
│   ├── commands.py          # Command handlers
│   └── listeners.py         # Event listeners
├── services/                # Business logic
│   ├── __init__.py
│   ├── auth.py
│   └── data.py
├── models/                  # Data models
│   ├── __init__.py
│   └── entities.py
└── utils/                   # Helpers
    ├── __init__.py
    └── helpers.py
```

---

## Naming Conventions

### Files
- **Snake case**: `api_client.py`, `data_processor.py`
- **Modules**: Use `__init__.py` for package imports
- **Handler files**: `handlers/commands.py`, `handlers/listeners.py`

### Classes
- **Plugin class**: Descriptive name (e.g., `NowcoderHelperPlugin`)
- **Services**: Functional name (e.g., `APIClient`, `DataProcessor`)
- **Models**: Entity name (e.g., `User`, `Problem`)

### Functions
- **Handlers**: Match command/event name (e.g., `helloworld` for `/helloworld`)
- **Async functions**: Prefix with action (e.g., `fetch_data`, `process_message`)
- **Private helpers**: Prefix with `_` (e.g., `_validate_input`)

---

## Import Conventions

### Standard AstrBot Imports
```python
# Core imports (always needed)
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot import logger

# Message components (when sending rich messages)
import astrbot.api.message_components as Comp

# Configuration (when using plugin config)
from astrbot.api import AstrBotConfig

# Platform adapters (when accessing platform APIs)
from astrbot.api.platform import AiocqhttpAdapter
```

### Local Imports
```python
# Services
from .services.api_client import APIClient

# Utils
from .utils.helpers import format_response

# Models
from .models.entities import Problem
```

---

## Anti-Patterns

### ❌ Wrong: Multiple Entry Points
```
plugin/
├── main.py
├── main_v2.py      # WRONG: Only main.py is recognized
└── handler.py      # WRONG: Can't have Star class here
```

### ❌ Wrong: Logic in main.py (Long Files)
```python
# main.py with 500+ lines of business logic
# WRONG: Extract to services/ module
```

### ❌ Wrong: Direct Platform Access
```python
# WRONG: Don't bypass AstrBot's abstraction
import requests  # Use AstrBot's platform adapters instead
```

---

## Examples from AstrBot

### Reference: AstrBot Plugin Template
- Repository: [astrbot-plugin-helloworld](https://github.com/AstrBotDevs/astrbot-plugin-helloworld)
- Structure: Minimal single-file plugin
- Use as: Starting template for new plugins

---

## Checklist for New Plugins

- [ ] `main.py` exists with Star class
- [ ] `metadata.yaml` has required fields
- [ ] `_conf_schema.json` if plugin needs configuration
- [ ] Services extracted if logic > 50 lines
- [ ] Data stored in `data/plugin_data/<plugin_name>/`
- [ ] All imports use AstrBot's API (not stdlib alternatives)