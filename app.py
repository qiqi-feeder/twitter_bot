"""
Twitter 自动发推系统主入口
基于 Flask 框架，提供 Web API 和定时任务功能
"""

from flask import Flask, request, jsonify
import signal
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.config_loader import config_loader
from utils.logger import logger
from utils.proxy import proxy_manager
from auth.token_manager import token_manager
from llm.llm_client import llm_client
from twitter.api_client import twitter_client
from scheduler.job_scheduler import job_scheduler


def create_app():
    """创建 Flask 应用"""
    app = Flask(__name__)
    
    # 加载配置
    flask_config = config_loader.get_flask_config()
    app.config.update(flask_config)
    
    return app


# 创建 Flask 应用实例
app = create_app()


@app.route('/')
def index():
    """首页"""
    return jsonify({
        'message': 'Twitter 自动发推系统',
        'version': '1.0.0',
        'status': 'running'
    })


@app.route('/status')
def status():
    """系统状态检查"""
    try:
        # 检查各个组件状态
        status_info = {
            'system': 'running',
            'proxy': {
                'enabled': proxy_manager.is_proxy_enabled(),
                'working': proxy_manager.test_proxy() if proxy_manager.is_proxy_enabled() else True
            },
            'twitter': {
                'credentials_valid': token_manager.validate_credentials(),
                'connection_ok': twitter_client.test_connection()
            },
            'openai': {
                'api_key_valid': llm_client.validate_api_key()
            },
            'scheduler': job_scheduler.get_job_status()
        }
        
        return jsonify(status_info)
        
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        return jsonify({
            'error': '获取系统状态失败',
            'message': str(e)
        }), 500


@app.route('/tweet/post', methods=['POST'])
def post_tweet():
    """手动发推接口"""
    try:
        # 获取请求数据
        data = request.get_json() or {}
        custom_content = data.get('content')
        
        # 执行发推
        result = job_scheduler.manual_tweet(custom_content)
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'message': '推文发送成功',
                'data': {
                    'tweet_id': result.get('tweet_id'),
                    'tweet_url': result.get('tweet_url'),
                    'content': result.get('content')
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': '推文发送失败',
                'error': result.get('error')
            }), 400
            
    except Exception as e:
        logger.error(f"手动发推失败: {e}")
        return jsonify({
            'success': False,
            'message': '发推时发生错误',
            'error': str(e)
        }), 500


@app.route('/tweet/generate', methods=['POST'])
def generate_tweet():
    """生成推文内容接口"""
    try:
        # 获取请求数据
        data = request.get_json() or {}
        custom_prompt = data.get('prompt')
        count = data.get('count', 1)
        
        if count > 5:
            return jsonify({
                'success': False,
                'message': '一次最多生成5条推文'
            }), 400
        
        # 生成推文
        if count == 1:
            tweet_content = llm_client.generate_tweet(custom_prompt)
            if tweet_content:
                return jsonify({
                    'success': True,
                    'data': {
                        'content': tweet_content,
                        'length': len(tweet_content)
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '生成推文失败'
                }), 500
        else:
            tweets = llm_client.generate_multiple_tweets(count)
            return jsonify({
                'success': True,
                'data': {
                    'tweets': [
                        {
                            'content': tweet,
                            'length': len(tweet)
                        } for tweet in tweets
                    ],
                    'count': len(tweets)
                }
            })
            
    except Exception as e:
        logger.error(f"生成推文失败: {e}")
        return jsonify({
            'success': False,
            'message': '生成推文时发生错误',
            'error': str(e)
        }), 500


@app.route('/user/info')
def user_info():
    """获取用户信息"""
    try:
        user_data = twitter_client.get_user_info()
        
        if user_data:
            return jsonify({
                'success': True,
                'data': user_data
            })
        else:
            return jsonify({
                'success': False,
                'message': '获取用户信息失败'
            }), 500
            
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取用户信息时发生错误',
            'error': str(e)
        }), 500


@app.route('/tweets/recent')
def recent_tweets():
    """获取最近的推文"""
    try:
        count = request.args.get('count', 5, type=int)
        if count > 20:
            count = 20
        
        tweets = twitter_client.get_recent_tweets(count)
        
        return jsonify({
            'success': True,
            'data': {
                'tweets': tweets,
                'count': len(tweets)
            }
        })
        
    except Exception as e:
        logger.error(f"获取最近推文失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取最近推文时发生错误',
            'error': str(e)
        }), 500


def signal_handler(signum, frame):
    """信号处理器，用于优雅关闭"""
    logger.info("接收到关闭信号，正在关闭系统...")
    
    # 停止调度器
    job_scheduler.stop()
    
    logger.info("系统已关闭")
    sys.exit(0)


def initialize_system():
    """初始化系统"""
    logger.info("正在初始化 Twitter 自动发推系统...")
    
    # 测试代理连接
    if proxy_manager.is_proxy_enabled():
        if not proxy_manager.test_proxy():
            logger.warning("代理连接测试失败，但系统将继续运行")
    
    # 验证 Twitter 凭据
    if not token_manager.validate_credentials():
        logger.error("Twitter 凭据验证失败，请检查配置")
        return False
    
    # 测试 Twitter 连接
    if not twitter_client.test_connection():
        logger.error("Twitter API 连接测试失败")
        return False
    
    # 验证 OpenAI API Key
    if not llm_client.validate_api_key():
        logger.error("OpenAI API Key 验证失败，请检查配置")
        return False
    
    # 启动调度器
    job_scheduler.start()
    
    logger.info("系统初始化完成")
    return True


if __name__ == '__main__':
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 初始化系统
        if not initialize_system():
            logger.error("系统初始化失败，退出")
            sys.exit(1)
        
        # 获取 Flask 配置
        flask_config = config_loader.get_flask_config()
        host = flask_config.get('host', '0.0.0.0')
        port = flask_config.get('port', 5000)
        debug = flask_config.get('debug', False)
        
        logger.info(f"启动 Flask 应用，地址: http://{host}:{port}")
        
        # 启动 Flask 应用
        app.run(
            host=host,
            port=port,
            debug=debug,
            threaded=True
        )
        
    except KeyboardInterrupt:
        logger.info("接收到键盘中断信号")
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        logger.error(f"启动应用时发生错误: {e}")
        sys.exit(1)
