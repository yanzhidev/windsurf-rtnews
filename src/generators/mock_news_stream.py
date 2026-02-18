"""
模拟新闻流生成器
"""
import json
import time
import random
from datetime import datetime


class MockStreamGenerator:
    """模拟流生成器"""
    
    def __init__(self):
        self.news_sources = [
            "TechCrunch", "Wired", "Ars Technica", "The Verge", 
            "Engadget", "ZDNet", "CNET", "VentureBeat"
        ]
        
        self.tech_companies = [
            "OpenAI", "Google", "Microsoft", "Apple", "Meta", 
            "Tesla", "Amazon", "NVIDIA", "AMD", "Intel"
        ]
        
        self.news_categories = [
            "Artificial Intelligence", "Cloud Computing", "Cybersecurity",
            "Mobile Technology", "Blockchain", "IoT", "5G", "Quantum Computing"
        ]
        
        self.counter = 0
    
    def generate_news_item(self):
        """生成新闻项"""
        self.counter += 1
        
        news_item = {
            "id": f"news_{int(time.time() * 1000)}_{self.counter}",
            "timestamp": datetime.now().isoformat(),
            "source": random.choice(self.news_sources),
            "title": f"Breaking: {random.choice(self.tech_companies)} Announces Revolutionary {random.choice(['AI Model', 'Cloud Service', 'Security Feature', 'Device'])}",
            "summary": f"Latest developments in technology sector with focus on innovation and digital transformation. Story #{self.counter}",
            "category": random.choice(self.news_categories),
            "company": random.choice(self.tech_companies),
            "impact_score": round(random.uniform(1.0, 10.0), 2),
            "url": f"https://example.com/news/{self.counter}"
        }
        
        return news_item


def main():
    """主函数 - 生成模拟新闻流"""
    generator = MockStreamGenerator()
    
    print("📡 启动模拟新闻流生成器...")
    
    try:
        while True:
            news_item = generator.generate_news_item()
            
            # 输出JSON格式的新闻
            print(json.dumps(news_item, ensure_ascii=False))
            
            # 每3秒生成一条新闻
            time.sleep(3)
            
    except KeyboardInterrupt:
        print("\n📡 模拟新闻流生成器已停止")
    except Exception as e:
        print(f"❌ 生成器错误: {e}")


if __name__ == "__main__":
    main()
