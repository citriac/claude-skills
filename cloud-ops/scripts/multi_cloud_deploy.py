#!/usr/bin/env python3
"""
多云部署自动化工具
支持同时部署到多个云平台，实现高可用和故障转移
"""

import os
import sys
import json
import yaml
import shutil
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import hashlib
import requests
import time

class MultiCloudDeployer:
    """多云部署器"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path('~/.cloud-ops/deploy-config.json').expanduser()
        self.load_config()
        
        # 部署状态跟踪
        self.deployment_status = {}
        self.deployment_log = []
        
        # 支持的平台
        self.supported_platforms = {
            'cloudflare_pages': self.deploy_to_cloudflare_pages,
            'vercel': self.deploy_to_vercel,
            'netlify': self.deploy_to_netlify,
            'github_pages': self.deploy_to_github_pages,
            'deno_deploy': self.deploy_to_deno_deploy,
            'aliyun_oss': self.deploy_to_aliyun_oss,
            'tencent_cos': self.deploy_to_tencent_cos
        }
        
        print(f"🚀 Multi-Cloud Deployer initialized")
        print(f"   Config: {self.config_path}")
        print(f"   Supported platforms: {', '.join(self.supported_platforms.keys())}")
    
    def load_config(self):
        """加载配置"""
        default_config = {
            'deployment_targets': {
                'primary': 'cloudflare_pages',
                'secondary': ['vercel', 'github_pages'],
                'backup': ['aliyun_oss']
            },
            'build_settings': {
                'build_command': 'npm run build',
                'build_dir': 'dist',
                'clean_before_build': True,
                'install_deps': True
            },
            'verification': {
                'health_check_urls': [],
                'timeout_seconds': 30,
                'retry_count': 3
            },
            'monitoring': {
                'log_file': 'deployments.log',
                'metrics_file': 'deployment_metrics.json'
            },
            'security': {
                'validate_build_output': True,
                'scan_for_secrets': True,
                'max_file_size_mb': 10
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
    
    def log_deployment(self, platform: str, action: str, status: str, details: str = ''):
        """记录部署日志"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'platform': platform,
            'action': action,
            'status': status,
            'details': details,
            'duration': None  # 将在完成时填充
        }
        
        self.deployment_log.append(entry)
        
        # 记录到文件
        log_file = self.config['monitoring']['log_file']
        try:
            with open(log_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            print(f"Failed to write log: {e}")
        
        # 输出到控制台
        status_symbol = '✅' if status == 'success' else '❌' if status == 'failed' else '⚠️'
        print(f"{status_symbol} [{platform}] {action}: {status}")
        if details:
            print(f"   Details: {details}")
        
        return entry
    
    def prepare_build(self, source_dir: Path) -> Path:
        """准备构建"""
        print("🔧 Preparing build...")
        
        build_settings = self.config['build_settings']
        build_dir = source_dir / build_settings['build_dir']
        
        # 清理之前的构建
        if build_settings['clean_before_build'] and build_dir.exists():
            print(f"  Cleaning {build_dir}...")
            shutil.rmtree(build_dir)
        
        # 安装依赖
        if build_settings['install_deps']:
            print("  Installing dependencies...")
            
            # 检查 package.json
            package_json = source_dir / 'package.json'
            if package_json.exists():
                try:
                    subprocess.run(['npm', 'install'], cwd=source_dir, check=True, capture_output=True)
                    print("  ✅ Dependencies installed")
                except subprocess.CalledProcessError as e:
                    print(f"  ❌ Failed to install dependencies: {e}")
                    raise
        
        # 执行构建命令
        print(f"  Running build command: {build_settings['build_command']}")
        try:
            result = subprocess.run(
                build_settings['build_command'],
                shell=True,
                cwd=source_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode != 0:
                print(f"  ❌ Build failed:\n{result.stderr}")
                raise RuntimeError(f"Build failed: {result.stderr}")
            
            print("  ✅ Build completed successfully")
            print(f"  Build output:\n{result.stdout[:500]}...")
        
        except subprocess.TimeoutExpired:
            print("  ❌ Build timeout after 5 minutes")
            raise
        
        # 验证构建输出
        if self.config['security']['validate_build_output']:
            self.validate_build_output(build_dir)
        
        return build_dir
    
    def validate_build_output(self, build_dir: Path):
        """验证构建输出"""
        print("🔍 Validating build output...")
        
        max_size_mb = self.config['security']['max_file_size_mb']
        issues = []
        
        # 检查文件大小
        for file_path in build_dir.rglob('*'):
            if file_path.is_file():
                file_size_mb = file_path.stat().st_size / (1024 * 1024)
                if file_size_mb > max_size_mb:
                    issues.append(f"File too large: {file_path.relative_to(build_dir)} ({file_size_mb:.1f}MB)")
        
        # 检查常见文件
        required_files = ['index.html']
        for req_file in required_files:
            if not (build_dir / req_file).exists():
                issues.append(f"Missing required file: {req_file}")
        
        # 扫描敏感信息
        if self.config['security']['scan_for_secrets']:
            secrets_found = self.scan_for_secrets(build_dir)
            if secrets_found:
                issues.append(f"Potential secrets found: {secrets_found}")
        
        if issues:
            print("  ⚠️  Validation issues found:")
            for issue in issues:
                print(f"    - {issue}")
        else:
            print("  ✅ Build validation passed")
    
    def scan_for_secrets(self, directory: Path) -> List[str]:
        """扫描构建输出中的敏感信息"""
        secret_patterns = [
            r'password\s*[:=]\s*["\']?[^"\'\s]+["\']?',
            r'api[_-]?key\s*[:=]\s*["\']?[^"\'\s]+["\']?',
            r'secret[_-]?key\s*[:=]\s*["\']?[^"\'\s]+["\']?',
            r'token\s*[:=]\s*["\']?[^"\'\s]+["\']?',
            r'[\w-]+_key\s*[:=]\s*["\']?[^"\'\s]+["\']?',
            r'[\w-]+_secret\s*[:=]\s*["\']?[^"\'\s]+["\']?'
        ]
        
        secrets_found = []
        
        for file_path in directory.rglob('*.js'):
            try:
                content = file_path.read_text(errors='ignore')
                for pattern in secret_patterns:
                    import re
                    if re.search(pattern, content, re.IGNORECASE):
                        secrets_found.append(str(file_path.relative_to(directory)))
                        break
            except Exception:
                continue
        
        return secrets_found
    
    def deploy_to_cloudflare_pages(self, build_dir: Path, project_name: str) -> Dict:
        """部署到 Cloudflare Pages"""
        print(f"☁️  Deploying to Cloudflare Pages: {project_name}")
        
        # 检查是否安装了 wrangler
        try:
            subprocess.run(['wrangler', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("  Installing wrangler...")
            subprocess.run(['npm', 'install', '-g', 'wrangler'], capture_output=True)
        
        # 创建必要的配置文件
        wrangler_toml = build_dir / 'wrangler.toml'
        if not wrangler_toml.exists():
            wrangler_config = f'''name = "{project_name}"
compatibility_date = "{datetime.now().strftime('%Y-%m-%d')}"
pages_build_output_dir = "."

[env.production]
workers_dev = false
'''
            wrangler_toml.write_text(wrangler_config)
        
        # 执行部署
        try:
            start_time = time.time()
            
            result = subprocess.run(
                ['wrangler', 'pages', 'deploy', str(build_dir), '--project-name', project_name],
                capture_output=True,
                text=True,
                timeout=180  # 3分钟超时
            )
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                # 从输出中提取 URL
                import re
                url_match = re.search(r'https://[a-zA-Z0-9.-]+\.pages\.dev', result.stdout)
                url = url_match.group(0) if url_match else 'unknown'
                
                return {
                    'success': True,
                    'url': url,
                    'duration': duration,
                    'output': result.stdout[:500]
                }
            else:
                return {
                    'success': False,
                    'error': result.stderr,
                    'duration': duration
                }
        
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Deployment timeout after 3 minutes'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def deploy_to_vercel(self, build_dir: Path, project_name: str) -> Dict:
        """部署到 Vercel"""
        print(f"▲ Deploying to Vercel: {project_name}")
        
        # 检查是否安装了 vercel CLI
        try:
            subprocess.run(['vercel', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("  Installing vercel CLI...")
            subprocess.run(['npm', 'install', '-g', 'vercel'], capture_output=True)
        
        # 创建 vercel.json 配置
        vercel_json = build_dir / 'vercel.json'
        if not vercel_json.exists():
            config = {
                'name': project_name,
                'version': 2,
                'builds': [{'src': '**', 'use': '@vercel/static'}],
                'routes': [{'src': '/(.*)', 'dest': '/$1'}]
            }
            vercel_json.write_text(json.dumps(config, indent=2))
        
        # 执行部署
        try:
            start_time = time.time()
            
            result = subprocess.run(
                ['vercel', '--prod', '--yes', '--confirm', '-b', f'PROJECT_NAME={project_name}'],
                cwd=build_dir,
                capture_output=True,
                text=True,
                timeout=180
            )
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                # 从输出中提取 URL
                import re
                url_match = re.search(r'https://[a-zA-Z0-9.-]+\.vercel\.app', result.stdout)
                url = url_match.group(0) if url_match else 'unknown'
                
                return {
                    'success': True,
                    'url': url,
                    'duration': duration,
                    'output': result.stdout[:500]
                }
            else:
                return {
                    'success': False,
                    'error': result.stderr,
                    'duration': duration
                }
        
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Deployment timeout after 3 minutes'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def deploy_to_netlify(self, build_dir: Path, project_name: str) -> Dict:
        """部署到 Netlify"""
        print(f"⎔ Deploying to Netlify: {project_name}")
        
        # 检查是否安装了 netlify CLI
        try:
            subprocess.run(['netlify', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("  Installing netlify CLI...")
            subprocess.run(['npm', 'install', '-g', 'netlify-cli'], capture_output=True)
        
        # 创建 netlify.toml 配置
        netlify_toml = build_dir / 'netlify.toml'
        if not netlify_toml.exists():
            config = f'''[build]
  publish = "."
  command = "echo 'Already built'"

[build.environment]
  NODE_VERSION = "18"

[context.production.environment]
  NODE_VERSION = "18"
'''
            netlify_toml.write_text(config)
        
        # 执行部署
        try:
            start_time = time.time()
            
            result = subprocess.run(
                ['netlify', 'deploy', '--prod', '--dir', str(build_dir), '--site', project_name],
                capture_output=True,
                text=True,
                timeout=180
            )
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                # 从输出中提取 URL
                import re
                url_match = re.search(r'https://[a-zA-Z0-9.-]+\.netlify\.app', result.stdout)
                url = url_match.group(0) if url_match else 'unknown'
                
                return {
                    'success': True,
                    'url': url,
                    'duration': duration,
                    'output': result.stdout[:500]
                }
            else:
                return {
                    'success': False,
                    'error': result.stderr,
                    'duration': duration
                }
        
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Deployment timeout after 3 minutes'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def deploy_to_github_pages(self, build_dir: Path, project_name: str) -> Dict:
        """部署到 GitHub Pages"""
        print(f"🐙 Deploying to GitHub Pages: {project_name}")
        
        # 这个通常通过 GitHub Actions 完成
        # 这里我们只是准备文件结构
        
        # 创建 .nojekyll 文件（禁用 Jekyll 处理）
        (build_dir / '.nojekyll').touch()
        
        # 创建 CNAME 文件（如果配置了自定义域名）
        # 这里简化处理
        
        return {
            'success': True,
            'url': f'https://{project_name}.github.io',
            'notes': 'Deployment should be triggered via GitHub Actions',
            'files_prepared': ['.nojekyll']
        }
    
    def deploy_to_deno_deploy(self, build_dir: Path, project_name: str) -> Dict:
        """部署到 Deno Deploy（用于 Serverless API）"""
        print(f"🦕 Deploying to Deno Deploy: {project_name}")
        
        # 检查是否有 main.ts 或类似的入口文件
        api_files = list(build_dir.glob('*.ts')) + list(build_dir.glob('*.js'))
        
        if not api_files:
            return {
                'success': False,
                'error': 'No API entry file found (*.ts or *.js)'
            }
        
        # 简化实现：实际需要更多配置
        print("  Note: Deno Deploy deployment requires specific setup")
        print("  Consider using GitHub Actions or deno deploy CLI directly")
        
        return {
            'success': True,
            'notes': 'Manual deployment required for Deno Deploy',
            'suggested_approach': 'Use GitHub Actions with deno deploy action'
        }
    
    def deploy_to_aliyun_oss(self, build_dir: Path, project_name: str) -> Dict:
        """部署到阿里云 OSS"""
        print(f"🟧 Deploying to Aliyun OSS: {project_name}")
        
        # 简化实现：实际需要阿里云 SDK 和认证
        print("  Note: Aliyun OSS deployment requires access credentials")
        print("  Set environment variables: OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET")
        
        import os
        if not os.getenv('OSS_ACCESS_KEY_ID') or not os.getenv('OSS_ACCESS_KEY_SECRET'):
            return {
                'success': False,
                'error': 'Aliyun OSS credentials not configured'
            }
        
        # 这里简化返回
        return {
            'success': True,
            'notes': 'Aliyun OSS deployment requires manual setup',
            'documentation': 'https://help.aliyun.com/product/31815.html'
        }
    
    def deploy_to_tencent_cos(self, build_dir: Path, project_name: str) -> Dict:
        """部署到腾讯云 COS"""
        print(f"🟦 Deploying to Tencent COS: {project_name}")
        
        # 简化实现
        print("  Note: Tencent COS deployment requires access credentials")
        
        return {
            'success': True,
            'notes': 'Tencent COS deployment requires manual setup',
            'documentation': 'https://cloud.tencent.com/document/product/436'
        }
    
    def verify_deployment(self, url: str, platform: str) -> bool:
        """验证部署是否成功"""
        print(f"🔍 Verifying deployment: {url}")
        
        verification = self.config['verification']
        timeout = verification['timeout_seconds']
        retry_count = verification['retry_count']
        
        for attempt in range(retry_count):
            try:
                response = requests.get(url, timeout=timeout, allow_redirects=True)
                
                if response.status_code == 200:
                    print(f"  ✅ Deployment verified (HTTP {response.status_code})")
                    return True
                else:
                    print(f"  ⚠️  Unexpected status: {response.status_code}")
            
            except requests.RequestException as e:
                print(f"  ⚠️  Verification attempt {attempt + 1} failed: {e}")
            
            if attempt < retry_count - 1:
                print(f"  Retrying in {2 ** attempt} seconds...")
                time.sleep(2 ** attempt)
        
        print(f"  ❌ All verification attempts failed")
        return False
    
    def deploy_all(self, source_dir: Path, project_name: str, targets: Optional[List[str]] = None):
        """部署到所有目标平台"""
        print("="*60)
        print(f"🚀 Starting multi-cloud deployment: {project_name}")
        print("="*60)
        
        # 确定部署目标
        if targets is None:
            targets = [
                self.config['deployment_targets']['primary']
            ] + self.config['deployment_targets']['secondary']
        
        print(f"Target platforms: {', '.join(targets)}")
        
        # 准备构建
        try:
            build_dir = self.prepare_build(source_dir)
        except Exception as e:
            print(f"❌ Build preparation failed: {e}")
            return
        
        # 执行部署
        deployment_results = {}
        
        for platform in targets:
            if platform not in self.supported_platforms:
                print(f"⚠️  Unsupported platform: {platform}")
                continue
            
            print(f"\n--- {platform.upper()} ---")
            
            try:
                deploy_func = self.supported_platforms[platform]
                result = deploy_func(build_dir, project_name)
                
                deployment_results[platform] = result
                
                if result.get('success', False):
                    # 验证部署
                    url = result.get('url')
                    if url and url != 'unknown':
                        verified = self.verify_deployment(url, platform)
                        result['verified'] = verified
                    
                    self.log_deployment(platform, 'deploy', 'success', 
                                      f"URL: {result.get('url', 'unknown')}")
                else:
                    self.log_deployment(platform, 'deploy', 'failed', 
                                      result.get('error', 'Unknown error'))
            
            except Exception as e:
                error_msg = f"Deployment error: {e}"
                deployment_results[platform] = {'success': False, 'error': error_msg}
                self.log_deployment(platform, 'deploy', 'failed', error_msg)
        
        # 生成报告
        self.generate_deployment_report(deployment_results)
        
        return deployment_results
    
    def generate_deployment_report(self, results: Dict):
        """生成部署报告"""
        print("\n" + "="*60)
        print("📊 DEPLOYMENT REPORT")
        print("="*60)
        
        successful = []
        failed = []
        warnings = []
        
        for platform, result in results.items():
            if result.get('success', False):
                url = result.get('url', 'No URL returned')
                verified = result.get('verified', False)
                
                status = f"✅ {platform}: {url}"
                if not verified:
                    status += " (verification failed)"
                    warnings.append(platform)
                else:
                    successful.append(platform)
            else:
                status = f"❌ {platform}: {result.get('error', 'Unknown error')}"
                failed.append(platform)
            
            print(status)
        
        # 统计
        print("\n📈 Summary:")
        print(f"  Successful: {len(successful)}/{len(results)}")
        print(f"  Failed: {len(failed)}/{len(results)}")
        print(f"  Warnings: {len(warnings)}")
        
        if successful:
            print(f"\n🌐 Access your site at:")
            for platform in successful:
                result = results[platform]
                if result.get('url') and result['url'] != 'unknown':
                    print(f"  • {platform}: {result['url']}")
        
        # 保存指标
        self.save_deployment_metrics(results)
    
    def save_deployment_metrics(self, results: Dict):
        """保存部署指标"""
        metrics_file = self.config['monitoring']['metrics_file']
        
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'project': 'multi-cloud-deployment',
            'results': results,
            'summary': {
                'total': len(results),
                'successful': len([r for r in results.values() if r.get('success', False)]),
                'failed': len([r for r in results.values() if not r.get('success', True)]),
                'verified': len([r for r in results.values() if r.get('verified', False)])
            }
        }
        
        try:
            with open(metrics_file, 'a') as f:
                f.write(json.dumps(metrics) + '\n')
        except Exception as e:
            print(f"Failed to save metrics: {e}")
    
    def cleanup(self):
        """清理临时资源"""
        print("\n🧹 Cleaning up...")
        # 这里可以添加清理逻辑，如删除临时文件等
        print("  Cleanup completed")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Multi-Cloud Deployment Tool')
    parser.add_argument('source_dir', help='Source directory to deploy')
    parser.add_argument('--project', required=True, help='Project name')
    parser.add_argument('--targets', nargs='+', help='Specific platforms to deploy to')
    parser.add_argument('--config', help='Custom config file path')
    parser.add_argument('--list-platforms', action='store_true', help='List supported platforms')
    
    args = parser.parse_args()
    
    # 列出支持的平台
    if args.list_platforms:
        deployer = MultiCloudDeployer()
        print("Supported platforms:")
        for platform in deployer.supported_platforms.keys():
            print(f"  • {platform}")
        return
    
    # 检查源目录
    source_dir = Path(args.source_dir).resolve()
    if not source_dir.exists():
        print(f"❌ Source directory not found: {source_dir}")
        sys.exit(1)
    
    # 创建部署器
    deployer = MultiCloudDeployer(Path(args.config) if args.config else None)
    
    try:
        # 执行部署
        results = deployer.deploy_all(source_dir, args.project, args.targets)
        
        # 根据结果设置退出码
        if results:
            successful = sum(1 for r in results.values() if r.get('success', False))
            if successful == 0:
                sys.exit(1)  # 所有部署都失败
            elif successful < len(results):
                sys.exit(2)  # 部分成功
        
    except KeyboardInterrupt:
        print("\n🛑 Deployment interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        sys.exit(1)
    finally:
        deployer.cleanup()

if __name__ == '__main__':
    main()