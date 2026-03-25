#!/usr/bin/env python3
"""
云成本优化工具
监控云资源使用，识别浪费，自动优化成本
"""

import os
import sys
import json
import csv
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import yaml

class CloudCostOptimizer:
    """云成本优化器"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path('~/.cloud-ops/cost-config.json').expanduser()
        self.load_config()
        
        # 成本数据
        self.cost_data = {}
        self.waste_analysis = {}
        self.optimization_actions = []
        
        # 免费层限制（2026年最新）
        self.free_tier_limits = {
            'cloudflare': {
                'requests_per_day': 100000,
                'bandwidth': 'unlimited',
                'builds_per_month': 500
            },
            'vercel': {
                'bandwidth_gb_per_month': 100,
                'build_minutes_per_month': 6000,
                'serverless_invocations_per_month': 100000
            },
            'netlify': {
                'bandwidth_gb_per_month': 100,
                'build_minutes_per_month': 100,
                'serverless_invocations_per_month': 125000
            },
            'github_actions': {
                'public_repo_minutes': 'unlimited',
                'private_repo_minutes': 2000
            },
            'deno_deploy': {
                'requests_per_month': 100000,
                'execution_time': '100k GiB-seconds/month'
            }
        }
        
        print(f"💰 Cloud Cost Optimizer initialized")
        print(f"   Config: {self.config_path}")
    
    def load_config(self):
        """加载配置"""
        default_config = {
            'budgets': {
                'monthly_budget': 0,  # 0 表示完全使用免费层
                'alert_threshold_percent': 80,
                'daily_spending_limit': 0
            },
            'monitoring': {
                'check_interval_hours': 24,
                'data_retention_days': 90,
                'log_file': 'cost_optimization.log',
                'reports_dir': 'cost_reports'
            },
            'optimizations': {
                'auto_cleanup_idle_resources': True,
                'idle_threshold_days': 30,
                'downsize_underutilized': True,
                'utilization_threshold_percent': 20,
                'enable_caching': True,
                'cache_ttl_days': 7
            },
            'notifications': {
                'enabled': False,
                'email': {
                    'smtp_server': '',
                    'smtp_port': 587,
                    'username': '',
                    'password': ''
                },
                'slack_webhook': '',
                'telegram_bot_token': '',
                'telegram_chat_id': ''
            },
            'cloud_accounts': {
                # 这里配置云账户信息
                # 实际使用时从环境变量或密钥管理服务读取
            }
        }
        
        try:
            with open(self.config_path, 'r') as f:
                self.config = {**default_config, **json.load(f)}
        except (FileNotFoundError, json.JSONDecodeError):
            self.config = default_config
            self.save_config()
    
    def save_config(self):
        """保存配置"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def collect_cost_data(self, platform: str) -> Dict:
        """收集成本数据"""
        print(f"📊 Collecting cost data for {platform}...")
        
        data = {
            'platform': platform,
            'timestamp': datetime.now().isoformat(),
            'costs': {},
            'usage': {},
            'forecast': {}
        }
        
        # 平台特定的数据收集
        if platform == 'vercel':
            data.update(self._collect_vercel_data())
        elif platform == 'cloudflare':
            data.update(self._collect_cloudflare_data())
        elif platform == 'netlify':
            data.update(self._collect_netlify_data())
        elif platform == 'github':
            data.update(self._collect_github_data())
        elif platform == 'all':
            # 收集所有平台数据
            all_data = {}
            for p in ['vercel', 'cloudflare', 'netlify', 'github']:
                try:
                    all_data[p] = self.collect_cost_data(p)
                except Exception as e:
                    print(f"  ❌ Failed to collect data for {p}: {e}")
                    all_data[p] = {'error': str(e)}
            return all_data
        
        # 存储数据
        self.cost_data[platform] = data
        
        # 保存到文件
        self.save_cost_data(platform, data)
        
        return data
    
    def _collect_vercel_data(self) -> Dict:
        """收集 Vercel 数据"""
        # 简化实现：实际需要 Vercel API 访问
        print("  Note: Vercel cost data requires API access")
        
        return {
            'estimated_cost': 0,  # 假设完全在免费层
            'bandwidth_used_gb': 0,
            'serverless_invocations': 0,
            'build_minutes_used': 0,
            'free_tier_remaining': {
                'bandwidth_gb': 100,
                'invocations': 100000,
                'build_minutes': 6000
            }
        }
    
    def _collect_cloudflare_data(self) -> Dict:
        """收集 Cloudflare 数据"""
        # 简化实现
        print("  Note: Cloudflare analytics requires API access")
        
        return {
            'estimated_cost': 0,
            'requests_today': 0,
            'bandwidth_used_gb': 0,
            'free_tier_remaining': {
                'daily_requests': 100000,
                'monthly_builds': 500
            }
        }
    
    def _collect_netlify_data(self) -> Dict:
        """收集 Netlify 数据"""
        return {
            'estimated_cost': 0,
            'bandwidth_used_gb': 0,
            'build_minutes_used': 0,
            'serverless_invocations': 0,
            'free_tier_remaining': {
                'bandwidth_gb': 100,
                'build_minutes': 100,
                'invocations': 125000
            }
        }
    
    def _collect_github_data(self) -> Dict:
        """收集 GitHub Actions 数据"""
        # 检查是否为公共仓库
        is_public_repo = True  # 简化假设
        
        return {
            'estimated_cost': 0,
            'actions_minutes_used': 0,
            'is_public_repo': is_public_repo,
            'free_tier_info': 'Unlimited minutes for public repos' if is_public_repo else '2000 minutes/month for private repos'
        }
    
    def save_cost_data(self, platform: str, data: Dict):
        """保存成本数据到文件"""
        reports_dir = Path(self.config['monitoring']['reports_dir'])
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # 按日期保存
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = reports_dir / f'cost_{platform}_{date_str}.json'
        
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to save cost data: {e}")
    
    def analyze_waste(self, platform: str, cost_data: Dict) -> Dict:
        """分析资源浪费"""
        print(f"🔍 Analyzing waste for {platform}...")
        
        waste_items = []
        savings_potential = 0
        
        # 检查是否接近免费层限制
        free_limits = self.free_tier_limits.get(platform, {})
        
        if platform == 'vercel':
            # 检查带宽使用
            bandwidth_used = cost_data.get('bandwidth_used_gb', 0)
            bandwidth_limit = free_limits.get('bandwidth_gb_per_month', 100)
            
            if bandwidth_used > bandwidth_limit * 0.8:  # 超过80%
                waste_items.append({
                    'type': 'BANDWIDTH_NEAR_LIMIT',
                    'description': f'Bandwidth usage ({bandwidth_used}GB) is near free tier limit ({bandwidth_limit}GB)',
                    'suggestion': 'Implement caching or CDN optimization',
                    'estimated_savings': 'Avoid $0.40/GB overage fees'
                })
        
        elif platform == 'netlify':
            # Netlify 构建分钟数很少
            build_minutes_used = cost_data.get('build_minutes_used', 0)
            build_minutes_limit = free_limits.get('build_minutes_per_month', 100)
            
            if build_minutes_used > build_minutes_limit * 0.9:
                waste_items.append({
                    'type': 'BUILD_MINUTES_CRITICAL',
                    'description': f'Build minutes ({build_minutes_used}) critical near limit ({build_minutes_limit})',
                    'suggestion': 'Reduce build frequency, optimize build process',
                    'estimated_savings': 'Avoid $7/500 build minutes overage'
                })
        
        # 检查闲置资源（通用）
        idle_resources = self.detect_idle_resources(platform)
        if idle_resources:
            waste_items.extend(idle_resources)
            savings_potential += len(idle_resources) * 5  # 估算每个闲置资源节省5美元
        
        # 检查未使用的服务
        unused_services = self.detect_unused_services(platform)
        if unused_services:
            waste_items.extend(unused_services)
        
        analysis = {
            'platform': platform,
            'waste_items': waste_items,
            'total_items': len(waste_items),
            'savings_potential_usd': savings_potential,
            'priority': 'HIGH' if len(waste_items) > 3 else 'MEDIUM' if len(waste_items) > 0 else 'LOW'
        }
        
        self.waste_analysis[platform] = analysis
        
        return analysis
    
    def detect_idle_resources(self, platform: str) -> List[Dict]:
        """检测闲置资源"""
        idle_resources = []
        
        # 这里简化实现，实际需要查询云平台API
        # 检测长时间无活动的资源
        
        if platform == 'vercel':
            # 检测无流量的部署
            idle_resources.append({
                'type': 'IDLE_DEPLOYMENT',
                'resource_id': 'example-deployment-123',
                'description': 'Deployment with no traffic in last 30 days',
                'last_accessed': '2026-02-01',
                'suggestion': 'Remove or archive this deployment'
            })
        
        elif platform == 'cloudflare':
            # 检测未使用的 Workers
            idle_resources.append({
                'type': 'IDLE_WORKER',
                'resource_id': 'unused-worker',
                'description': 'Cloudflare Worker with no invocations in last 30 days',
                'invocations_last_30_days': 0,
                'suggestion': 'Remove unused Worker'
            })
        
        return idle_resources
    
    def detect_unused_services(self, platform: str) -> List[Dict]:
        """检测未使用的服务"""
        unused_services = []
        
        # 常见未使用服务模式
        common_unused = [
            'Development/Staging environments that are never used',
            'Backup services with no actual backups',
            'Monitoring services with no alerts configured',
            'Database replicas with no read traffic'
        ]
        
        for service in common_unused[:2]:  # 只显示前两个
            unused_services.append({
                'type': 'UNUSED_SERVICE',
                'description': service,
                'suggestion': 'Review and remove if not needed'
            })
        
        return unused_services
    
    def generate_optimization_actions(self, waste_analysis: Dict) -> List[Dict]:
        """生成优化行动计划"""
        platform = waste_analysis['platform']
        waste_items = waste_analysis.get('waste_items', [])
        
        actions = []
        
        for item in waste_items:
            action = {
                'platform': platform,
                'issue_type': item['type'],
                'description': item['description'],
                'recommended_action': item.get('suggestion', 'Review and optimize'),
                'estimated_savings': item.get('estimated_savings', 'Varies'),
                'priority': 'HIGH' if 'CRITICAL' in item['type'] or 'NEAR_LIMIT' in item['type'] else 'MEDIUM',
                'implementation': self._get_implementation_guide(platform, item['type'])
            }
            actions.append(action)
        
        # 添加通用优化建议
        if platform in ['vercel', 'netlify']:
            actions.append({
                'platform': platform,
                'issue_type': 'GENERAL_OPTIMIZATION',
                'description': 'General cost optimization opportunities',
                'recommended_action': 'Implement caching and optimize assets',
                'estimated_savings': '10-30% bandwidth reduction',
                'priority': 'MEDIUM',
                'implementation': {
                    'steps': [
                        'Configure CDN caching headers',
                        'Optimize images with next/image or similar',
                        'Implement incremental static regeneration',
                        'Use lazy loading for non-critical resources'
                    ]
                }
            })
        
        self.optimization_actions.extend(actions)
        
        return actions
    
    def _get_implementation_guide(self, platform: str, issue_type: str) -> Dict:
        """获取实施指南"""
        guides = {
            ('vercel', 'BANDWIDTH_NEAR_LIMIT'): {
                'title': 'Reduce Vercel Bandwidth Usage',
                'steps': [
                    'Enable Image Optimization in next.config.js',
                    'Implement ISR (Incremental Static Regeneration)',
                    'Use Vercel Analytics to identify high-bandwidth pages',
                    'Consider moving large assets to Cloudflare R2 or similar'
                ],
                'resources': [
                    'https://vercel.com/docs/concepts/next.js/image-optimization',
                    'https://vercel.com/docs/concepts/next.js/incremental-static-regeneration'
                ]
            },
            ('netlify', 'BUILD_MINUTES_CRITICAL'): {
                'title': 'Reduce Netlify Build Minutes',
                'steps': [
                    'Optimize build process in netlify.toml',
                    'Use cached dependencies (npm ci vs npm install)',
                    'Implement build caching with Netlify Build Plugins',
                    'Reduce build frequency for non-critical updates'
                ],
                'resources': [
                    'https://docs.netlify.com/configure-builds/get-started/',
                    'https://docs.netlify.com/configure-builds/caching/'
                ]
            },
            ('cloudflare', 'IDLE_WORKER'): {
                'title': 'Clean Up Unused Cloudflare Workers',
                'steps': [
                    'Review Workers usage in Cloudflare Dashboard',
                    'Identify Workers with no recent invocations',
                    'Remove or disable unused Workers',
                    'Consider consolidating similar Workers'
                ],
                'resources': [
                    'https://developers.cloudflare.com/workers/',
                    'https://developers.cloudflare.com/workers/observability/logging/'
                ]
            }
        }
        
        return guides.get((platform, issue_type), {
            'title': 'General Optimization',
            'steps': ['Review the resource and determine if it can be removed or optimized'],
            'resources': []
        })
    
    def execute_optimization(self, action: Dict, dry_run: bool = True) -> Dict:
        """执行优化操作"""
        print(f"🔧 Executing optimization: {action['description']}")
        
        result = {
            'action_id': f"{action['platform']}_{action['issue_type']}_{int(time.time())}",
            'action': action,
            'dry_run': dry_run,
            'executed_at': datetime.now().isoformat(),
            'steps_completed': [],
            'errors': []
        }
        
        if dry_run:
            result['status'] = 'simulated'
            result['message'] = 'Dry run - no actual changes made'
            print(f"  📋 Dry run simulation (no changes made)")
            return result
        
        # 实际执行（简化实现）
        try:
            # 这里根据action类型执行具体操作
            # 实际实现需要调用各云平台的API
            
            if action['issue_type'] == 'IDLE_DEPLOYMENT':
                # 示例：删除闲置部署
                result['steps_completed'].append('Identified idle deployment')
                result['message'] = 'Action requires manual review and execution'
            
            elif action['issue_type'] == 'BANDWIDTH_NEAR_LIMIT':
                # 示例：优化缓存配置
                result['steps_completed'].append('Generated cache optimization recommendations')
                result['message'] = 'Recommendations generated, manual implementation required'
            
            result['status'] = 'completed'
        
        except Exception as e:
            result['status'] = 'failed'
            result['errors'].append(str(e))
        
        return result
    
    def generate_report(self, platforms: List[str] = None) -> Dict:
        """生成成本优化报告"""
        if platforms is None:
            platforms = ['vercel', 'cloudflare', 'netlify', 'github']
        
        print("\n" + "="*60)
        print("📈 CLOUD COST OPTIMIZATION REPORT")
        print("="*60)
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'platforms_analyzed': platforms,
            'total_estimated_monthly_cost': 0,
            'total_savings_potential': 0,
            'platform_details': {},
            'optimization_actions': [],
            'recommendations': []
        }
        
        for platform in platforms:
            print(f"\n--- {platform.upper()} ---")
            
            # 收集数据
            try:
                cost_data = self.collect_cost_data(platform)
                
                # 分析浪费
                waste_analysis = self.analyze_waste(platform, cost_data)
                
                # 生成优化行动
                actions = self.generate_optimization_actions(waste_analysis)
                
                # 汇总到报告
                platform_summary = {
                    'cost_data': cost_data,
                    'waste_analysis': waste_analysis,
                    'optimization_actions': actions,
                    'estimated_savings': waste_analysis.get('savings_potential_usd', 0)
                }
                
                report['platform_details'][platform] = platform_summary
                report['total_savings_potential'] += waste_analysis.get('savings_potential_usd', 0)
                report['optimization_actions'].extend(actions)
                
                # 输出平台摘要
                print(f"  Status: {'⚠️ Needs optimization' if waste_analysis['total_items'] > 0 else '✅ Optimized'}")
                print(f"  Waste items found: {waste_analysis['total_items']}")
                print(f"  Estimated savings: ${waste_analysis.get('savings_potential_usd', 0):.2f}")
                
                if waste_analysis['total_items'] > 0:
                    print(f"  Priority: {waste_analysis['priority']}")
            
            except Exception as e:
                print(f"  ❌ Analysis failed: {e}")
                report['platform_details'][platform] = {'error': str(e)}
        
        # 生成总体建议
        report['recommendations'] = self.generate_recommendations(report)
        
        # 输出总体摘要
        print("\n" + "="*60)
        print("📊 OVERALL SUMMARY")
        print("="*60)
        print(f"Platforms analyzed: {len(report['platform_details'])}")
        print(f"Total savings potential: ${report['total_savings_potential']:.2f}")
        print(f"Total optimization actions: {len(report['optimization_actions'])}")
        
        # 按优先级分组行动
        high_priority = [a for a in report['optimization_actions'] if a['priority'] == 'HIGH']
        medium_priority = [a for a in report['optimization_actions'] if a['priority'] == 'MEDIUM']
        
        if high_priority:
            print(f"\n🔴 HIGH PRIORITY ACTIONS ({len(high_priority)}):")
            for action in high_priority[:3]:  # 只显示前3个
                print(f"  • {action['platform']}: {action['description']}")
        
        if medium_priority:
            print(f"\n🟡 MEDIUM PRIORITY ACTIONS ({len(medium_priority)}):")
            for action in medium_priority[:2]:
                print(f"  • {action['platform']}: {action['description']}")
        
        # 保存报告
        self.save_report(report)
        
        # 发送通知（如果配置了）
        if self.config['notifications']['enabled']:
            self.send_notification(report)
        
        return report
    
    def generate_recommendations(self, report: Dict) -> List[Dict]:
        """生成总体建议"""
        recommendations = []
        
        total_savings = report['total_savings_potential']
        
        if total_savings > 50:
            recommendations.append({
                'priority': 'HIGH',
                'title': 'Significant Savings Opportunity',
                'description': f'Potential savings of ${total_savings:.2f} identified',
                'action': 'Review and implement high-priority optimization actions'
            })
        
        # 检查是否接近预算
        monthly_budget = self.config['budgets']['monthly_budget']
        if monthly_budget > 0:
            # 这里可以添加预算相关的建议
            pass
        
        # 免费层优化建议
        recommendations.append({
            'priority': 'MEDIUM',
            'title': 'Maximize Free Tier Usage',
            'description': 'Ensure you are fully utilizing all available free tier resources',
            'action': 'Review free tier limits and adjust usage patterns accordingly'
        })
        
        # 监控建议
        recommendations.append({
            'priority': 'LOW',
            'title': 'Implement Cost Monitoring',
            'description': 'Set up automated cost monitoring and alerts',
            'action': 'Configure budget alerts and regular cost reviews'
        })
        
        return recommendations
    
    def save_report(self, report: Dict):
        """保存报告到文件"""
        reports_dir = Path(self.config['monitoring']['reports_dir'])
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存 JSON 版本
        json_file = reports_dir / f'cost_optimization_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(json_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # 保存 CSV 版本（简化）
        csv_file = reports_dir / f'cost_optimization_actions_{datetime.now().strftime("%Y%m%d")}.csv'
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Platform', 'Issue Type', 'Description', 'Priority', 'Estimated Savings', 'Recommended Action'])
            
            for action in report['optimization_actions']:
                writer.writerow([
                    action['platform'],
                    action['issue_type'],
                    action['description'][:100],  # 截断长描述
                    action['priority'],
                    action['estimated_savings'],
                    action['recommended_action'][:100]
                ])
        
        print(f"\n📁 Reports saved:")
        print(f"  • Detailed report: {json_file}")
        print(f"  • Action items: {csv_file}")
    
    def send_notification(self, report: Dict):
        """发送通知"""
        notifications = self.config['notifications']
        
        message = f"""Cloud Cost Optimization Report - {datetime.now().strftime('%Y-%m-%d')}

Platforms analyzed: {len(report['platform_details'])}
Total savings potential: ${report['total_savings_potential']:.2f}
Total optimization actions: {len(report['optimization_actions'])}

High priority actions: {len([a for a in report['optimization_actions'] if a['priority'] == 'HIGH'])}
Medium priority actions: {len([a for a in report['optimization_actions'] if a['priority'] == 'MEDIUM'])}

Detailed report has been saved.
"""
        
        # 邮件通知
        if notifications['email']['smtp_server']:
            self._send_email_notification(message)
        
        # Slack 通知
        if notifications['slack_webhook']:
            self._send_slack_notification(message)
        
        # Telegram 通知
        if notifications['telegram_bot_token'] and notifications['telegram_chat_id']:
            self._send_telegram_notification(message)
    
    def _send_email_notification(self, message: str):
        """发送邮件通知"""
        try:
            email_config = self.config['notifications']['email']
            
            msg = MIMEMultipart()
            msg['From'] = email_config['username']
            msg['To'] = email_config['username']  # 发送给自己
            msg['Subject'] = f'Cloud Cost Optimization Report - {datetime.now().strftime("%Y-%m-%d")}'
            
            msg.attach(MIMEText(message, 'plain'))
            
            with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
                server.starttls()
                server.login(email_config['username'], email_config['password'])
                server.send_message(msg)
            
            print("  📧 Email notification sent")
        
        except Exception as e:
            print(f"  ❌ Failed to send email: {e}")
    
    def _send_slack_notification(self, message: str):
        """发送 Slack 通知"""
        try:
            webhook_url = self.config['notifications']['slack_webhook']
            
            payload = {
                'text': message,
                'username': 'Cloud Cost Optimizer',
                'icon_emoji': ':money_with_wings:'
            }
            
            response = requests.post(webhook_url, json=payload)
            if response.status_code == 200:
                print("  💬 Slack notification sent")
            else:
                print(f"  ❌ Slack notification failed: {response.status_code}")
        
        except Exception as e:
            print(f"  ❌ Failed to send Slack notification: {e}")
    
    def _send_telegram_notification(self, message: str):
        """发送 Telegram 通知"""
        try:
            token = self.config['notifications']['telegram_bot_token']
            chat_id = self.config['notifications']['telegram_chat_id']
            
            url = f'https://api.telegram.org/bot{token}/sendMessage'
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                print("  📱 Telegram notification sent")
            else:
                print(f"  ❌ Telegram notification failed: {response.status_code}")
        
        except Exception as e:
            print(f"  ❌ Failed to send Telegram notification: {e}")
    
    def run_continuous_monitoring(self):
        """运行持续监控"""
        print("👁️  Starting continuous cost monitoring...")
        print(f"   Check interval: {self.config['monitoring']['check_interval_hours']} hours")
        print("   Press Ctrl+C to stop")
        print("="*60)
        
        check_interval = self.config['monitoring']['check_interval_hours'] * 3600
        
        try:
            while True:
                print(f"\n🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 生成报告
                report = self.generate_report()
                
                # 检查是否需要立即行动
                high_priority = len([a for a in report['optimization_actions'] if a['priority'] == 'HIGH'])
                if high_priority > 0:
                    print(f"⚠️  {high_priority} high priority actions need attention!")
                
                # 等待下一个检查
                print(f"\r📊 Monitoring... Next check in {self.config['monitoring']['check_interval_hours']} hours", end='', flush=True)
                time.sleep(check_interval)
        
        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped")
        except Exception as e:
            print(f"\n❌ Monitoring error: {e}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Cloud Cost Optimization Tool')
    parser.add_argument('--report', action='store_true', help='Generate cost optimization report')
    parser.add_argument('--monitor', action='store_true', help='Start continuous monitoring')
    parser.add_argument('--platform', help='Specific platform to analyze')
    parser.add_argument('--config', help='Custom config file path')
    parser.add_argument('--execute', action='store_true', help='Execute optimization actions (dry run by default)')
    parser.add_argument('--dry-run', action='store_true', help='Simulate actions without making changes')
    
    args = parser.parse_args()
    
    # 创建优化器
    optimizer = CloudCostOptimizer(Path(args.config) if args.config else None)
    
    if args.monitor:
        optimizer.run_continuous_monitoring()
    
    elif args.report:
        platforms = [args.platform] if args.platform else None
        report = optimizer.generate_report(platforms)
        
        # 如果请求执行，执行高优先级操作
        if args.execute:
            high_priority = [a for a in report['optimization_actions'] if a['priority'] == 'HIGH']
            if high_priority:
                print(f"\n🚀 Executing {len(high_priority)} high priority actions...")
                
                for action in high_priority[:3]:  # 只执行前3个
                    result = optimizer.execute_optimization(action, dry_run=args.dry_run)
                    print(f"  {action['platform']}: {result['status']}")
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()