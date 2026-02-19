"""
压力测试配置文件
"""
import os
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class StressTestConfig:
    """压力测试配置"""
    
    # 基础配置
    base_url: str = "http://localhost:8000"
    ws_url: str = "ws://localhost:8000/ws"
    
    # WebSocket压力测试配置
    websocket_clients: int = 100
    websocket_duration: int = 60  # 秒
    websocket_message_interval: float = 0.1  # 秒
    
    # API压力测试配置
    api_concurrent_requests: int = 50
    api_duration: int = 60  # 秒
    api_request_interval: float = 0.05  # 秒
    
    # 内存压力测试配置
    memory_test_duration: int = 120  # 秒
    memory_check_interval: float = 1.0  # 秒
    
    # 系统资源监控配置
    cpu_threshold: float = 80.0  # CPU使用率阈值(%)
    memory_threshold: float = 85.0  # 内存使用率阈值(%)
    
    # 测试报告配置
    report_output_dir: str = "test_reports"
    enable_detailed_logging: bool = True
    
    # 测试场景配置
    test_scenarios: Dict[str, Dict] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.test_scenarios is None:
            self.test_scenarios = {
                "light_load": {
                    "websocket_clients": 10,
                    "api_concurrent_requests": 5,
                    "duration": 30
                },
                "medium_load": {
                    "websocket_clients": 50,
                    "api_concurrent_requests": 20,
                    "duration": 60
                },
                "heavy_load": {
                    "websocket_clients": 100,
                    "api_concurrent_requests": 50,
                    "duration": 120
                },
                "extreme_load": {
                    "websocket_clients": 200,
                    "api_concurrent_requests": 100,
                    "duration": 180
                }
            }
        
        # 确保报告目录存在
        os.makedirs(self.report_output_dir, exist_ok=True)


# 全局配置实例
STRESS_CONFIG = StressTestConfig()
