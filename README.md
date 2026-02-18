# 实时技术新闻聚合器

一个基于 Python FastAPI 的实时技术新闻聚合器项目，模拟新闻流并提供 Web 界面展示。

## 项目结构

```
wsproject1/
├── mock_stream.py      # 模拟新闻流生成器
├── main.py            # FastAPI 主应用
├── requirements.txt   # 项目依赖
└── README.md         # 项目说明
```

## 功能特性

- 🚀 **实时新闻流**: 每 3 秒生成一条模拟技术新闻
- 📡 **WebSocket 支持**: 实时推送新闻到 Web 客户端
- 🌐 **Web 界面**: 美观的实时新闻展示界面
- 📊 **统计信息**: 新闻处理统计和分类分布
- 🔌 **RESTful API**: 提供 JSON API 接口

## 快速开始

### 1. 安装依赖

```bash
python3 -m pip install -r requirements.txt
```

### 2. 启动应用

```bash
python3 main.py
```

### 3. 访问界面

- **Web 界面**: http://localhost:8000
- **新闻 API**: http://localhost:8000/api/news
- **统计 API**: http://localhost:8000/api/stats
- **WebSocket**: ws://localhost:8000/ws

## 使用说明

### 运行模拟新闻流

如果只想运行新闻流生成器：

```bash
python3 mock_stream.py
```

这将每 3 秒输出一条 JSON 格式的模拟新闻。

### 启动完整应用

运行 `main.py` 将启动：
1. 新闻流读取器（后台进程）
2. FastAPI Web 服务器
3. WebSocket 实时推送服务

### 新闻数据格式

每条新闻包含以下字段：

```json
{
  "id": "news_1234567890",
  "timestamp": "2024-01-01T12:00:00",
  "source": "TechCrunch",
  "title": "OpenAI Announces Revolutionary AI Breakthrough",
  "summary": "Latest developments in AI...",
  "category": "Artificial Intelligence",
  "company": "OpenAI",
  "impact_score": 8.5,
  "url": "https://example.com/news/1234567890",
  "processed_at": "2024-01-01T12:00:01",
  "processing_id": 1
}
```

## 技术栈

- **FastAPI**: 现代、快速的 Web 框架
- **Uvicorn**: ASGI 服务器
- **WebSocket**: 实时通信
- **Python 3.9+**: 编程语言

## 项目特点

1. **模块化设计**: 清晰的代码结构，易于扩展
2. **实时处理**: 异步处理新闻流
3. **多客户端支持**: WebSocket 支持多个并发连接
4. **统计功能**: 实时统计新闻处理情况
5. **响应式界面**: 现代化的 Web 界面设计

## 扩展建议

- 添加真实新闻源 API 集成
- 实现新闻过滤和搜索功能
- 添加用户订阅和通知功能
- 集成数据库存储历史新闻
- 添加新闻情感分析

## 故障排除

如果遇到端口占用问题，可以修改 `main.py` 中的端口号：

```python
config = uvicorn.Config(app, host="0.0.0.0", port=8001, log_level="info")
```

## 许可证

MIT License
