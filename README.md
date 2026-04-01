# Nowcoder Helper - AstrBot Plugin

交互式获取牛客网文章的 AstrBot 插件，支持多步骤对话、搜索翻页、会话持久化。

## 功能特性

- **交互式多步骤对话**: 通过会话控制实现自然的交互流程
- **用户会话隔离**: 群聊中每个用户的会话独立，互不干扰
- **会话超时**: 1分钟无操作自动退出
- **会话持久化**: AstrBot 重启后恢复未完成的会话状态
- **搜索翻页**: 支持查看多页搜索结果
- **异步请求**: 使用 aiohttp 实现高效的网络请求

## 安装

将本插件目录放入 AstrBot 的 `addons/plugins/` 目录下即可。

## 使用方法

### 启动助手

```
/nowcoder
```

### 交互流程示例

```
用户: /nowcoder
Bot: 牛客文章助手已启动

     请选择功能:
     1. 解析文章 (发送链接)
     2. 搜索文章 (发送关键词)

     发送数字选择，或发送'退出'取消

用户: 2
Bot: 请输入搜索关键词

用户: 面经
Bot: 搜索结果: 面经
     第 1 页 / 共 3 页
     共 20 条结果

     ---
     1. 阿里巴巴Java开发岗位面经分享
     2. 腾讯校招面试经验总结
     3. 字节跳动后端开发面试题
     ...

     ---
     输入编号选择文章
     发送'下一页'查看更多
     发送'退出'取消

用户: 下一页
Bot: [显示第2页结果]

用户: 5
Bot: [返回文章 Markdown 内容]
```

### 支持的文章类型

| 类型 | URL 格式 |
|------|----------|
| Discuss | `https://www.nowcoder.com/discuss/{id}` |
| Feed | `https://www.nowcoder.com/feed/main/detail/{uuid}` |

### 命令说明

| 命令 | 说明 |
|------|------|
| `/nowcoder` | 启动交互会话 |
| `1` 或 `2` | 选择功能 |
| `下一页` / `上一页` | 翻页浏览搜索结果 |
| `退出` | 取消当前会话 |

### 会话特性

- **超时**: 1分钟无操作自动退出
- **隔离**: 群聊中每个用户会话独立
- **持久化**: 重启 AstrBot 后恢复会话状态

## 技术实现

```
nowcoder-helper-astrbot/
├── main.py                    # 插件入口 + 会话控制
├── metadata.yaml              # 插件元数据
├── services/
│   ├── __init__.py
│   ├── api_client_async.py    # 异步 API 请求 (aiohttp)
│   ├── parser.py              # HTML 解析
│   └── models.py              # 数据模型
└── README.md
```

核心技术:
- `session_waiter` - 多轮对话会话控制
- `SessionController` - 会话生命周期管理
- `aiohttp` - 异步 HTTP 请求
- `get_astrbot_data_path()` - 会话状态持久化

## 相关链接

- [AstrBot 官方文档](https://docs.astrbot.app/)
- [会话控制指南](https://docs.astrbot.app/dev/star/guides/session-control.html)

## License

MIT License