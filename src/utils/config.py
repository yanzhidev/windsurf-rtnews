"""
背压保护系统配置
"""
import os

# 背压控制配置
BACKPRESSURE_CONFIG = {
    'max_line_size': 1 * 1024 * 1024,  # 1MB 最大行大小
    'max_memory_usage': 200 * 1024 * 1024,  # 200MB 最大内存使用
    'max_queue_size': 10000,  # 最大队列大小
    'processing_delay_threshold': 0.1,  # 处理延迟阈值(秒)
    'memory_check_interval': 5,  # 内存检查间隔(秒)
    'graceful_shutdown_timeout': 10  # 优雅关闭超时(秒)
}

# 应用配置
APP_CONFIG = {
    'title': "背压保护版 - 实时技术新闻聚合器",
    'version': "1.3.0",
    'host': "0.0.0.0",
    'port': 8000,
    'log_level': "info"
}

# 新闻流配置
NEWS_CONFIG = {
    'buffer_size': 1000,  # 新闻缓冲区大小
    'test_duration': 30,  # 测试持续时间(秒)
    'news_per_second': 1000,  # 每秒新闻数量
    'stats_broadcast_interval': 100,  # 每100条新闻广播统计
    'progress_report_interval': 1000,  # 每1000条新闻打印进度
}

# WebSocket配置
WS_CONFIG = {
    'max_news_display': 20,  # 网页最大显示新闻数量
    'stats_update_interval': 10,  # 统计更新间隔(秒)
}
