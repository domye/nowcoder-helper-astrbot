# Nowcoder Helper - AstrBot Plugin

获取牛客网文章并以 Markdown 格式返回的 AstrBot 插件。

> [!NOTE]
> 本插件用于 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 平台。
>
> [AstrBot](https://github.com/AstrBotDevs/AstrBot) 是一个支持多平台的智能对话机器人框架，支持 QQ、Telegram、飞书、钉钉、Slack、LINE、Discord、Matrix 等数十种主流即时通讯平台。

## 功能特性

- 获取牛客文章内容并以 Markdown 格式返回
- 支持两种文章类型：
  - Discuss 类型: `https://www.nowcoder.com/discuss/xxx`
  - Feed 类型: `https://www.nowcoder.com/feed/main/detail/xxx`
- 搜索牛客文章

## 安装

将本插件目录放入 AstrBot 的 `addons/plugins/` 目录下即可。

## 使用方法

### 获取文章

```
/nowcoder <文章URL>
```

示例：
```
/nowcoder https://www.nowcoder.com/discuss/123456789
```

返回格式：
```markdown
# 文章标题

**作者**: 作者名称
**身份**: 用户身份信息
**时间**: 发布时间
**链接**: https://www.nowcoder.com/discuss/xxx

**统计**: 浏览 1000 | 点赞 50 | 评论 20

---

文章正文内容...

---

**图片**:

![图片](图片链接)
```

### 搜索文章

```
/nowcoder_search <关键词>
```

示例：
```
/nowcoder_search 面经
```

返回搜索结果列表，包含文章标题、类型和链接。

## 支持的文章类型

| 类型 | URL 格式 | 说明 |
|------|----------|------|
| Discuss | `/discuss/{id}` | 讨论帖类型 |
| Feed | `/feed/main/detail/{uuid}` | 动态类型 |

## 技术实现

插件结构：
```
nowcoder-helper-astrbot/
├── main.py               # 插件入口
├── metadata.yaml         # 插件元数据
├── services/             # 业务逻辑
│   ├── __init__.py
│   ├── api_client.py     # API 请求
│   ├── parser.py         # HTML 解析
│   └── models.py         # 数据模型
└── README.md             # 文档
```

## 相关链接

- [AstrBot Repo](https://github.com/AstrBotDevs/AstrBot)
- [AstrBot Plugin Development Docs (Chinese)](https://docs.astrbot.app/dev/star/plugin-new.html)
- [AstrBot Plugin Development Docs (English)](https://docs.astrbot.app/en/dev/star/plugin-new.html)

## License

MIT License