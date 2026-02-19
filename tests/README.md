# 压力测试文档

## 概述

本项目包含完整的压力测试套件，用于测试实时技术新闻聚合器的性能和稳定性。

## 测试组件

### 1. 核心框架

- **`stress_test_framework.py`**: 核心测试框架，提供基础功能和指标收集
- **`stress_test_config.py`**: 测试配置文件，定义测试参数和场景

### 2. 专项测试

- **`test_stress_websocket.py`**: WebSocket连接压力测试
- **`test_stress_api.py`**: API端点压力测试  
- **`test_stress_memory.py`**: 内存和系统资源压力测试

### 3. 测试运行器

- **`run_stress_tests.py`**: 主测试运行器，支持多种测试模式

## 使用方法

### 前提条件

1. 确保目标应用正在运行：
```bash
python main.py
```

2. 安装测试依赖：
```bash
pip install -r requirements.txt
```

### 运行测试

#### 快速测试（推荐首次使用）
```bash
cd tests
python run_stress_tests.py --type quick
```

#### 完整测试套件
```bash
cd tests
python run_stress_tests.py --type full
```

#### 单独运行特定测试

```bash
# 只运行WebSocket测试
python run_stress_tests.py --type websocket

# 只运行API测试
python run_stress_tests.py --type api

# 只运行内存测试
python run_stress_tests.py --type memory
```

#### 指定测试场景
```bash
python run_stress_tests.py --type websocket --scenarios light_load medium_load
```

#### 详细输出
```bash
python run_stress_tests.py --type quick --verbose
```

## 测试场景

### 负载级别

- **light_load**: 轻负载测试
  - WebSocket: 10个客户端
  - API: 5个并发请求
  - 持续时间: 30秒

- **medium_load**: 中等负载测试
  - WebSocket: 50个客户端
  - API: 20个并发请求
  - 持续时间: 60秒

- **heavy_load**: 重负载测试
  - WebSocket: 100个客户端
  - API: 50个并发请求
  - 持续时间: 120秒

- **extreme_load**: 极限负载测试
  - WebSocket: 200个客户端
  - API: 100个并发请求
  - 持续时间: 180秒

## 测试报告

### 报告位置

所有测试报告保存在 `test_reports/` 目录中：
- 单个测试报告: `test_reports/{test_name}_{timestamp}.json`
- 综合报告: `test_reports/stress_test_summary_{timestamp}.json`
- 日志文件: `test_reports/stress_test_{timestamp}.log`

### 报告内容

每个测试报告包含：
- 测试基本信息（名称、时长、请求数等）
- 响应时间统计（平均值、最小值、最大值、P95、P99）
- 系统资源使用情况（CPU、内存峰值和平均值）
- 错误信息和统计

### 关键指标

- **成功率**: 成功请求 / 总请求数
- **RPS**: 每秒请求数
- **响应时间**: 平均、P95、P99响应时间
- **资源使用**: CPU和内存使用率峰值
- **错误率**: 失败请求的比例和类型

## 配置说明

### 修改测试参数

编辑 `stress_test_config.py` 文件：

```python
# WebSocket测试配置
websocket_clients: int = 100
websocket_duration: int = 60
websocket_message_interval: float = 0.1

# API测试配置
api_concurrent_requests: int = 50
api_duration: int = 60
api_request_interval: float = 0.05

# 系统资源阈值
cpu_threshold: float = 80.0  # CPU使用率阈值(%)
memory_threshold: float = 85.0  # 内存使用率阈值(%)
```

### 添加自定义场景

在 `test_scenarios` 中添加新场景：

```python
"custom_load": {
    "websocket_clients": 75,
    "api_concurrent_requests": 30,
    "duration": 90
}
```

## 故障排除

### 常见问题

1. **连接被拒绝**
   - 确保目标应用正在运行
   - 检查端口配置（默认8000）

2. **内存不足**
   - 减少并发数量
   - 缩短测试持续时间
   - 增加系统恢复时间

3. **测试超时**
   - 增加timeout配置
   - 检查网络连接
   - 减少负载

### 性能调优建议

1. **系统准备**
   - 关闭不必要的应用程序
   - 确保有足够的可用内存
   - 监控系统温度

2. **测试策略**
   - 从轻负载开始逐步增加
   - 在测试之间留出恢复时间
   - 监控系统资源使用情况

3. **结果分析**
   - 关注P95/P99响应时间而非平均值
   - 监控错误率趋势
   - 对比不同负载级别的性能表现

## 扩展开发

### 添加新的测试类型

1. 继承 `StressTestFramework` 类
2. 实现测试逻辑
3. 在 `run_stress_tests.py` 中集成

### 自定义指标收集

重写 `collect_system_metrics()` 方法添加自定义指标。

### 集成外部监控

可以集成Prometheus、Grafana等监控工具进行更详细的性能分析。

## 最佳实践

1. **测试环境**: 使用与生产环境相似的配置
2. **测试频率**: 定期运行压力测试，特别是在代码变更后
3. **结果对比**: 保存历史测试结果进行趋势分析
4. **自动化**: 将压力测试集成到CI/CD流程中
5. **监控**: 在测试过程中实时监控系统状态

## 许可证

本压力测试套件遵循项目的MIT许可证。
