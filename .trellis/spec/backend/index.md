# AstrBot Plugin Development Guidelines

> Best practices for developing AstrBot plugins in Python.

---

## Overview

This project is an **AstrBot Plugin**. All backend code follows AstrBot's plugin architecture and conventions.

**Key Technologies**:
- Python 3.8+
- AstrBot Plugin Framework (Star class)
- Async/await patterns
- AstrBot API (event, message_components, logger)

---

## Pre-Development Checklist

Before writing any plugin code, read these documents:

1. **[Directory Structure](./directory-structure.md)** - Plugin file organization
2. **[Plugin Architecture](./plugin-architecture.md)** - Star class, lifecycle, registration
3. **[Event Handling](./event-handling.md)** - Filters, commands, message events
4. **[Error Handling](./error-handling.md)** - Exception patterns, graceful failures
5. **[Quality Guidelines](./quality-guidelines.md)** - Code standards, async best practices
6. **[Logging Guidelines](./logging-guidelines.md)** - Using AstrBot's logger

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Plugin file layout and organization | ✅ Complete |
| [Plugin Architecture](./plugin-architecture.md) | Star class, metadata, lifecycle | ✅ Complete |
| [Event Handling](./event-handling.md) | Filters, commands, message processing | ✅ Complete |
| [Error Handling](./error-handling.md) | Exception handling in async handlers | ✅ Complete |
| [Quality Guidelines](./quality-guidelines.md) | Code standards, async patterns | ✅ Complete |
| [Logging Guidelines](./logging-guidelines.md) | AstrBot logger usage | ✅ Complete |

---

## Official Documentation

- [AstrBot Plugin Dev Guide (EN)](https://docs.astrbot.app/en/dev/star/plugin-new.html)
- [AstrBot Plugin Dev Guide (CN)](https://docs.astrbot.app/dev/star/plugin-new.html)
- [Minimal Example](https://docs.astrbot.app/en/dev/star/guides/simple.html)
- [Message Events](https://docs.astrbot.app/en/dev/star/guides/listen-message-event.html)
- [Plugin Config](https://docs.astrbot.app/en/dev/star/guides/plugin-config.html)

---

**Language**: All documentation is written in **English** with code examples from AstrBot docs.