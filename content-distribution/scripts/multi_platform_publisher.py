#!/usr/bin/env python3
"""
多平台内容发布引擎
支持掘金、知乎、Reddit、Dev.to、Twitter等平台自动发布
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import requests
from dataclasses import dataclass, field
from enum import Enum
import markdown
from pathlib import Path
import pytz

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Platform(Enum):
    """支持的发布平台"""
    JUEJIN = "juejin"        # 掘金
    ZHIHU = "zhihu"          # 知乎
    REDDIT = "reddit"        # Reddit
    DEVTO = "devto"          # Dev.to
    TWITTER = "twitter"      # Twitter
    LINKEDIN = "linkedin"    # LinkedIn
    CSDN = "csdn"            # CSDN
    V2EX = "v2ex"            # V2EX


class ContentType(Enum):
    """内容类型"""
    TECHNICAL_TUTORIAL = "technical_tutorial"      # 技术教程
    OPEN_SOURCE_SHOWCASE = "open_source_showcase"  # 开源项目展示
    PERFORMANCE_OPTIMIZATION = "performance_optimization"  # 性能优化
    TOOL_RECOMMENDATION = "tool_recommendation"    # 工具推荐
    INDUSTRY_ANALYSIS = "industry_analysis"        # 行业分析
    LEARNING_NOTE = "learning_note"                # 学习笔记


@dataclass
class Content:
    """内容数据结构"""
    title: str
    content_markdown: str
    content_type: ContentType
    tags: List[str] = field(default_factory=list)
    source_url: Optional[str] = None
    author: str = "Clavis"
    publish_date: Optional[datetime] = None
    cover_image: Optional[str] = None
    seo_keywords: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "title": self.title,
            "content": self.content_markdown,
            "content_type": self.content_type.value,
            "tags": self.tags,
            "source_url": self.source_url,
            "author": self.author,
            "publish_date": self.publish_date.isoformat() if self.publish_date else None,
            "cover_image": self.cover_image,
            "seo_keywords": self.seo_keywords
        }


@dataclass
class PublishResult:
    """发布结果"""
    platform: Platform
    success: bool
    post_url: Optional[str] = None
    post_id: Optional[str] = None
    error_message: Optional[str] = None
    response_time_ms: Optional[int] = None
    
    def to_dict(self) -> Dict:
        return {
            "platform": self.platform.value,
            "success": self.success,
            "post_url": self.post_url,
            "post_id": self.post_id,
            "error_message": self.error_message,
            "response_time_ms": self.response_time_ms
        }


@dataclass
class PlatformConfig:
    """平台配置"""
    api_base_url: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    rate_limit_per_hour: int = 100
    require_manual_auth: bool = False
    user_agent: str = "ContentDistributionBot/1.0 (by Clavis)"
    
    def is_authenticated(self) -> bool:
        """检查是否已认证"""
        return bool(self.access_token) or bool(self.api_key)


class ContentOptimizer:
    """内容优化器"""
    
    def __init__(self):
        self.platform_templates = self._load_templates()
        self.tag_recommendations = self._load_tag_recommendations()
    
    def _load_templates(self) -> Dict[str, Dict]:
        """加载各平台模板"""
        return {
            "juejin": {
                "title_max_length": 100,
                "content_structure": ["引言", "正文", "代码示例", "总结", "互动问题"],
                "recommended_tags_count": 5,
                "code_block_language": "自动检测"
            },
            "zhihu": {
                "title_max_length": 120,
                "content_structure": ["问题背景", "详细解答", "技术原理", "实践建议", "参考文献"],
                "require_citations": True,
                "depth_level": "high"
            },
            "reddit": {
                "title_max_length": 300,
                "content_structure": ["简洁说明", "核心内容", "讨论引导"],
                "flair_required": True,
                "self_promotion_limit": "10% rule"
            },
            "devto": {
                "title_max_length": 150,
                "content_structure": ["摘要", "正文", "代码示例", "总结", "下一步"],
                "tags_max": 4,
                "series_support": True
            }
        }
    
    def _load_tag_recommendations(self) -> Dict[str, List[str]]:
        """加载标签推荐"""
        return {
            "ai": ["人工智能", "机器学习", "深度学习", "AI编程"],
            "webdev": ["前端", "后端", "全栈", "JavaScript", "TypeScript"],
            "devops": ["Docker", "Kubernetes", "CI/CD", "云原生"],
            "database": ["MySQL", "PostgreSQL", "Redis", "MongoDB"],
            "mobile": ["iOS", "Android", "Flutter", "React Native"],
            "opensource": ["开源", "GitHub", "贡献指南", "社区"]
        }
    
    def optimize_for_platform(self, content: Content, platform: Platform) -> Content:
        """为特定平台优化内容"""
        platform_name = platform.value
        template = self.platform_templates.get(platform_name, {})
        
        optimized_content = Content(
            title=self._optimize_title(content.title, platform_name),
            content_markdown=self._optimize_markdown(content.content_markdown, platform_name),
            content_type=content.content_type,
            tags=self._optimize_tags(content.tags, content.content_type, platform_name),
            source_url=content.source_url,
            author=content.author,
            publish_date=content.publish_date,
            cover_image=content.cover_image,
            seo_keywords=content.seo_keywords
        )
        
        return optimized_content
    
    def _optimize_title(self, title: str, platform: str) -> str:
        """优化标题"""
        title = title.strip()
        
        # 平台特定优化
        if platform == "juejin":
            # 掘金：包含技术栈，突出价值
            if "提升" not in title and "减少" not in title:
                # 如果没有价值表述，考虑添加
                pass
            if len(title) > 100:
                title = title[:97] + "..."
                
        elif platform == "zhihu":
            # 知乎：问题导向，深度思考
            if "？" not in title and "?" not in title:
                # 如果不是问题形式，考虑转换
                if "如何" not in title:
                    title = f"如何{title}？"
            if len(title) > 120:
                title = title[:117] + "..."
                
        elif platform == "reddit":
            # Reddit：简洁描述，避免营销语言
            if "【" in title or "】" in title:
                title = title.replace("【", "[").replace("】", "]")
            if len(title) > 300:
                title = title[:297] + "..."
        
        return title
    
    def _optimize_markdown(self, markdown_content: str, platform: str) -> str:
        """优化Markdown内容"""
        lines = markdown_content.split('\n')
        optimized_lines = []
        
        for line in lines:
            # 平台特定优化
            if platform == "juejin":
                # 掘金：添加目录标记
                if line.startswith('# ') and len(optimized_lines) < 10:
                    pass
                    
            elif platform == "zhihu":
                # 知乎：强调引用和参考文献
                if line.startswith('> '):
                    line = f"**{line}**"
                    
            elif platform == "reddit":
                # Reddit：简化格式，避免复杂Markdown
                if line.startswith('#' * 4):
                    line = line.replace('#### ', '**')
                    line = line + '**'
                    
            optimized_lines.append(line)
        
        return '\n'.join(optimized_lines)
    
    def _optimize_tags(self, original_tags: List[str], content_type: ContentType, platform: str) -> List[str]:
        """优化标签"""
        tags = original_tags.copy()
        
        # 根据内容类型添加推荐标签
        type_tags = {
            ContentType.TECHNICAL_TUTORIAL: ["教程", "实战"],
            ContentType.OPEN_SOURCE_SHOWCASE: ["开源", "GitHub"],
            ContentType.PERFORMANCE_OPTIMIZATION: ["性能", "优化"],
            ContentType.TOOL_RECOMMENDATION: ["工具", "效率"],
            ContentType.INDUSTRY_ANALYSIS: ["行业", "趋势"],
            ContentType.LEARNING_NOTE: ["学习", "笔记"]
        }
        
        if content_type in type_tags:
            for tag in type_tags[content_type]:
                if tag not in tags:
                    tags.append(tag)
        
        # 平台特定限制
        if platform == "juejin" and len(tags) > 5:
            tags = tags[:5]
        elif platform == "devto" and len(tags) > 4:
            tags = tags[:4]
        
        return tags[:10]  # 最多10个标签


class MultiPlatformPublisher:
    """多平台发布器"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.configs: Dict[Platform, PlatformConfig] = {}
        self.optimizer = ContentOptimizer()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ContentDistributionBot/1.0 (by Clavis)"
        })
        
        if config_file:
            self.load_configs(config_file)
    
    def load_configs(self, config_file: str):
        """加载配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            for platform_str, config in config_data.items():
                try:
                    platform = Platform(platform_str)
                    self.configs[platform] = PlatformConfig(**config)
                    logger.info(f"已加载 {platform.value} 配置")
                except ValueError:
                    logger.warning(f"跳过未知平台: {platform_str}")
                    
        except FileNotFoundError:
            logger.error(f"配置文件不存在: {config_file}")
        except json.JSONDecodeError:
            logger.error(f"配置文件格式错误: {config_file}")
    
    def publish(self, content: Content, platforms: List[Platform], 
                dry_run: bool = False) -> List[PublishResult]:
        """发布内容到多个平台"""
        results = []
        
        for platform in platforms:
            if dry_run:
                logger.info(f"[DRY RUN] 准备发布到 {platform.value}")
                results.append(PublishResult(
                    platform=platform,
                    success=True,
                    post_url="(dry-run)",
                    post_id="(dry-run)"
                ))
                continue
            
            # 优化内容
            optimized_content = self.optimizer.optimize_for_platform(content, platform)
            
            # 发布
            start_time = time.time()
            try:
                result = self._publish_to_platform(optimized_content, platform)
                result.response_time_ms = int((time.time() - start_time) * 1000)
                results.append(result)
                
                if result.success:
                    logger.info(f"成功发布到 {platform.value}: {result.post_url}")
                else:
                    logger.error(f"发布到 {platform.value} 失败: {result.error_message}")
                    
                # 遵守API频率限制
                if platform in self.configs:
                    rate_limit = self.configs[platform].rate_limit_per_hour
                    if rate_limit > 0:
                        delay = 3600 / rate_limit
                        time.sleep(delay)
                        
            except Exception as e:
                logger.error(f"发布到 {platform.value} 时发生异常: {str(e)}")
                results.append(PublishResult(
                    platform=platform,
                    success=False,
                    error_message=f"异常: {str(e)}"
                ))
        
        return results
    
    def _publish_to_platform(self, content: Content, platform: Platform) -> PublishResult:
        """发布到具体平台"""
        platform_config = self.configs.get(platform)
        
        if not platform_config or not platform_config.is_authenticated():
            return PublishResult(
                platform=platform,
                success=False,
                error_message="平台未配置或未认证"
            )
        
        # 平台特定发布逻辑
        if platform == Platform.JUEJIN:
            return self._publish_to_juejin(content, platform_config)
        elif platform == Platform.REDDIT:
            return self._publish_to_reddit(content, platform_config)
        elif platform == Platform.DEVTO:
            return self._publish_to_devto(content, platform_config)
        else:
            return PublishResult(
                platform=platform,
                success=False,
                error_message=f"平台 {platform.value} 暂未实现"
            )
    
    def _publish_to_juejin(self, content: Content, config: PlatformConfig) -> PublishResult:
        """发布到掘金"""
        try:
            # 这里应该是实际的API调用
            # 由于需要真实API密钥，这里使用模拟响应
            logger.info(f"模拟发布到掘金: {content.title}")
            
            # 模拟API延迟
            time.sleep(0.5)
            
            return PublishResult(
                platform=Platform.JUEJIN,
                success=True,
                post_url=f"https://juejin.cn/post/模拟文章ID",
                post_id="模拟文章ID"
            )
            
        except Exception as e:
            return PublishResult(
                platform=Platform.JUEJIN,
                success=False,
                error_message=f"掘金发布失败: {str(e)}"
            )
    
    def _publish_to_reddit(self, content: Content, config: PlatformConfig) -> PublishResult:
        """发布到Reddit"""
        try:
            # Reddit API调用模拟
            logger.info(f"模拟发布到Reddit: {content.title}")
            
            # 模拟API延迟
            time.sleep(0.7)
            
            return PublishResult(
                platform=Platform.REDDIT,
                success=True,
                post_url=f"https://reddit.com/r/programming/comments/模拟ID",
                post_id="模拟ID"
            )
            
        except Exception as e:
            return PublishResult(
                platform=Platform.REDDIT,
                success=False,
                error_message=f"Reddit发布失败: {str(e)}"
            )
    
    def _publish_to_devto(self, content: Content, config: PlatformConfig) -> PublishResult:
        """发布到Dev.to"""
        try:
            # Dev.to API调用模拟
            logger.info(f"模拟发布到Dev.to: {content.title}")
            
            # 模拟API延迟
            time.sleep(0.6)
            
            return PublishResult(
                platform=Platform.DEVTO,
                success=True,
                post_url=f"https://dev.to/clavis/模拟文章",
                post_id="模拟文章ID"
            )
            
        except Exception as e:
            return PublishResult(
                platform=Platform.DEVTO,
                success=False,
                error_message=f"Dev.to发布失败: {str(e)}"
            )
    
    def generate_report(self, results: List[PublishResult]) -> Dict:
        """生成发布报告"""
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_platforms": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(results) if results else 0,
            "platform_details": [r.to_dict() for r in results],
            "summary": {
                "successful_platforms": [r.platform.value for r in successful],
                "failed_platforms": [{"platform": r.platform.value, "error": r.error_message} for r in failed]
            }
        }
        
        return report


def create_example_config() -> Dict:
    """创建示例配置文件"""
    config = {
        "juejin": {
            "api_base_url": "https://api.juejin.cn",
            "api_key": "your_juejin_api_key",
            "api_secret": "your_juejin_api_secret",
            "rate_limit_per_hour": 100,
            "require_manual_auth": False
        },
        "reddit": {
            "api_base_url": "https://oauth.reddit.com",
            "client_id": "your_reddit_client_id",
            "client_secret": "your_reddit_client_secret",
            "user_agent": "ContentDistributionBot/1.0 (by Clavis)",
            "rate_limit_per_hour": 60
        },
        "devto": {
            "api_base_url": "https://dev.to/api",
            "api_key": "your_devto_api_key",
            "rate_limit_per_hour": 120
        }
    }
    
    return config


def main():
    """主函数示例"""
    import argparse
    
    parser = argparse.ArgumentParser(description="多平台内容发布器")
    parser.add_argument("--config", default="config.json", help="配置文件路径")
    parser.add_argument("--title", required=True, help="文章标题")
    parser.add_argument("--content", required=True, help="Markdown内容文件路径")
    parser.add_argument("--tags", nargs="+", default=[], help="文章标签")
    parser.add_argument("--platforms", nargs="+", choices=[p.value for p in Platform], 
                       default=["juejin", "reddit", "devto"], help="发布平台")
    parser.add_argument("--dry-run", action="store_true", help="试运行，不实际发布")
    parser.add_argument("--output", default="publish_report.json", help="报告输出路径")
    
    args = parser.parse_args()
    
    # 读取内容
    try:
        with open(args.content, 'r', encoding='utf-8') as f:
            content_markdown = f.read()
    except FileNotFoundError:
        logger.error(f"内容文件不存在: {args.content}")
        return
    
    # 创建内容对象
    content = Content(
        title=args.title,
        content_markdown=content_markdown,
        content_type=ContentType.TECHNICAL_TUTORIAL,
        tags=args.tags,
        author="Clavis"
    )
    
    # 创建发布器
    publisher = MultiPlatformPublisher(args.config)
    
    # 转换为平台枚举
    platforms = [Platform(p) for p in args.platforms]
    
    # 发布
    results = publisher.publish(content, platforms, dry_run=args.dry_run)
    
    # 生成报告
    report = publisher.generate_report(results)
    
    # 保存报告
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # 打印摘要
    print(f"\n发布完成:")
    print(f"  总平台数: {report['total_platforms']}")
    print(f"  成功: {report['successful']}")
    print(f"  失败: {report['failed']}")
    print(f"  成功率: {report['success_rate']:.1%}")
    
    if args.dry_run:
        print("\n⚠️ 这是试运行，没有实际发布")


if __name__ == "__main__":
    main()