# 实时技术新闻聚合器

一个基于 Python FastAPI 的实时技术新闻聚合器项目，专注于系统保护和内存管理机制。

## 项目结构

```
wsproject1/
├── main.py                          # 主应用入口
├── src/                             # 源代码目录
│   ├── __init__.py
│   ├── core/                         # 核心功能模块
│   │   ├── __init__.py
│   │   ├── backpressure_controller.py  # 系统控制器
│   │   ├── protected_news_processor.py # 新闻处理器和流读取器
│   │   ├── websocket_manager.py       # WebSocket连接管理器
│   │   └── news_stream_generator.py  # 新闻流生成器
│   ├── api/                          # API路由模块
│   │   ├── __init__.py
│   │   └── routes.py                 # API路由定义
│   ├── generators/                   # 新闻生成器
│   │   ├── __init__.py
│   │   ├── mock_news_stream.py       # 模拟新闻流生成器
│   │   └── high_frequency_news.py   # 高频新闻生成器
│   └── utils/                        # 工具模块
│       ├── __init__.py
│       └── config.py                 # 配置管理
├── tests/                            # 测试目录
│   ├── __init__.py
│   ├── test_protection.py            # 系统保护测试
│   ├── test_websocket.py             # WebSocket测试
│   └── main_original.py              # 原始版本（备份）
├── docs/                             # 文档目录
│   ├── guide.md                      # 系统保护实现指南
│   └── explanation.md                # 修复说明
├── requirements.txt                  # 项目依赖
└── README.md                         # 项目说明
```

## 功能特性

- 🚀 **实时新闻流**: 每 3 秒生成一条模拟技术新闻
- 📡 **WebSocket 支持**: 实时推送新闻到 Web 客户端
- 🌐 **Web 界面**: 美观的实时新闻展示界面
- 📊 **统计信息**: 新闻处理统计和分类分布
- 🔌 **RESTful API**: 提供 JSON API 接口
- 🛡️ **背压保护**: 防止内存溢出和系统过载
- 🔍 **内存监控**: 实时监控内存使用情况
- ⚡ **性能优化**: 高效的异步处理机制

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

### 运行系统保护测试

```bash
python3 tests/test_protection.py
```

### 运行 WebSocket 测试

```bash
python3 tests/test_websocket.py
```

### 启动完整应用

运行 `main.py` 将启动：
1. 带系统保护的新闻流读取器
2. FastAPI Web 服务器
3. WebSocket 实时推送服务
4. 内存监控和系统控制

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
- **asyncio**: 异步编程支持
- **psutil**: 系统资源监控
- **Python 3.9+**: 编程语言

## 系统保护特性

1. **内存监控**: 实时监控进程内存使用情况
2. **队列限制**: 防止消息队列无限增长
3. **处理延迟控制**: 监控和限制处理延迟
4. **优雅降级**: 系统过载时自动暂停处理
5. **自动恢复**: 系统资源充足时自动恢复处理

## 项目特点

1. **标准Python项目结构**: 遵循Python项目最佳实践
2. **模块化架构**: 清晰的代码结构，易于维护和扩展
3. **系统保护**: 完整的系统保护和内存管理机制
4. **实时处理**: 异步处理新闻流
5. **多客户端支持**: WebSocket 支持多个并发连接
6. **统计功能**: 实时统计新闻处理情况
7. **响应式界面**: 现代化的 Web 界面设计
8. **测试覆盖**: 完整的系统保护测试套件
9. **配置管理**: 集中化的配置管理

## 扩展建议

- 添加真实新闻源 API 集成
- 实现新闻过滤和搜索功能
- 添加用户订阅和通知功能
- 集成数据库存储历史新闻
- 添加新闻情感分析
- 优化系统控制算法
- 添加分布式系统控制

## 故障排除

如果遇到端口占用问题，可以修改 `src/utils/config.py` 中的端口号：

```python
APP_CONFIG = {
    'port': 8001,  # 修改为其他端口
    # ...
}
```

## 系统保护配置

系统保护配置位于 `src/utils/config.py` 中的 `BACKPRESSURE_CONFIG`：

```python
BACKPRESSURE_CONFIG = {
    'max_line_size': 1 * 1024 * 1024,  # 1MB 最大行大小
    'max_memory_usage': 200 * 1024 * 1024,  # 200MB 最大内存使用
    'max_queue_size': 10000,  # 最大队列大小
    'processing_delay_threshold': 0.1,  # 处理延迟阈值(秒)
    'memory_check_interval': 5,  # 内存检查间隔(秒)
    'graceful_shutdown_timeout': 10  # 优雅关闭超时(秒)
}
```

## 许可证

MIT License
