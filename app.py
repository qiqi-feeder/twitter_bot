"""
Twitter 自动发推系统主入口
基于 Flask 框架，提供 Web API 和定时任务功能
"""
import threading
from get_data.main import run_once  #
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import signal
import sys
import os
import time
import pytz

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
    
    # 设置 Secret Key (用于 Session)
    app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev_secret_key_123')
    
    return app


# 创建 Flask 应用实例
app = create_app()

# 认证拦截器
@app.before_request
def require_login():
    # 允许访问的端点
    allowed_endpoints = ['login', 'static', 'status','post_tweet','manual_run_once','run_bot']
    if request.endpoint in allowed_endpoints:
        return

    # 检查 Session
    from flask import session, redirect, url_for
    if not session.get('logged_in'):
        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    from flask import render_template, session, redirect, url_for
    
    if request.method == 'GET':
        if session.get('logged_in'):
            return redirect(url_for('compose_page'))
        return render_template('login.html')
    
    # 处理登录请求
    data = request.get_json() or {}
    password = data.get('password')
    
    # 获取配置的密码
    flask_config = config_loader.get_flask_config()
    correct_password = flask_config.get('web_password', 'admin') # 默认密码 admin
    
    # 从 config.local.yaml 读取 (如果 config_loader 没有读取到)
    # 这里假设 config_loader 已经处理了合并逻辑
    # 为了保险，我们再读一次 config.local.yaml
    try:
        import yaml
        with open(os.path.join(os.path.dirname(__file__), 'config', 'config.local.yaml'), 'r') as f:
            local_config = yaml.safe_load(f)
            if local_config and 'web_password' in local_config:
                correct_password = local_config['web_password']
    except Exception:
        pass

    if password == correct_password:
        session['logged_in'] = True
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Incorrect password'}), 401


@app.route('/logout')
def logout():
    """退出登录"""
    from flask import session, redirect, url_for
    session.pop('logged_in', None)
    return redirect(url_for('login'))


@app.route('/')
def index():
    """首页 (重定向到发推页面)"""
    from flask import redirect, url_for
    return redirect(url_for('compose_page'))


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


@app.route('/compose')
def compose_page():
    """发推页面"""
    from flask import render_template
    return render_template('compose.html')
@app.route('/tweet/post', methods=['POST'])
def post_tweet():
    """发布推文（支持立即发送和定时发送）"""
    try:
        # 处理 multipart/form-data
        content = request.form.get('content')
        scheduled_time = request.form.get('scheduled_time')
        tz = request.form.get('timezone', 'America/New_York')

        if not content or not content.strip():
            return jsonify({
                'success': False,
                'message': '内容不能为空'
            }), 400

        # 保存上传的图片
        media_files = []
        if 'images' in request.files:
            files = request.files.getlist('images')
            upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)

            for file in files:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    filename = f"{int(time.time())}_{filename}"  # 防重名
                    file_path = os.path.join(upload_dir, filename)
                    file.save(file_path)
                    media_files.append(file_path)
                    logger.info(f"已保存上传图片: {file_path}")

        # 发送推文
        try:
            if scheduled_time:
                result = job_scheduler.schedule_one_off_tweet(content, scheduled_time, media_files, tz)
            else:
                result = job_scheduler.manual_tweet(content, media_files)
        except Exception as e:
            logger.error(f"推文发送失败（job_scheduler）: {e}")
            return jsonify({
                'success': False,
                'message': '发送失败',
                'error': str(e)
            }), 500

        # 确保 result 是 dict，并有 success 字段
        if not isinstance(result, dict):
            logger.error(f"job_scheduler 返回异常: {result}")
            return jsonify({
                'success': False,
                'message': '发送失败',
                'error': 'job_scheduler 返回非 dict 类型'
            }), 500

        if result.get('success'):
            return jsonify({
                'success': True,
                'message': '推文发送成功' if not scheduled_time else result.get('message'),
                'data': result
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', '发送失败'),
                'error': result.get('error')
            }), 400

    except Exception as e:
        logger.error(f"处理发推请求失败: {e}")
        return jsonify({
            'success': False,
            'message': '系统错误',
            'error': str(e)
        }), 500


# @app.route('/tweet/post', methods=['POST'])
# def post_tweet():
#     """发布推文（支持立即发送和定时发送）"""
#     try:
#         # 处理 multipart/form-data
#         content = request.form.get('content')
#         scheduled_time = request.form.get('scheduled_time')
#         timezone = request.form.get('timezone', 'America/New_York')
        
#         # 保存上传的图片
#         media_files = []
#         if 'images' in request.files:
#             files = request.files.getlist('images')
#             # 确保上传目录存在
#             upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
#             if not os.path.exists(upload_dir):
#                 os.makedirs(upload_dir)
                
#             for file in files:
#                 if file and file.filename:
#                     filename = secure_filename(file.filename)
#                     # 添加时间戳防止重名
#                     filename = f"{int(time.time())}_{filename}"
#                     file_path = os.path.join(upload_dir, filename)
#                     file.save(file_path)
#                     media_files.append(file_path)
#                     logger.info(f"已保存上传图片: {file_path}")

#         if scheduled_time:
#             result = job_scheduler.schedule_one_off_tweet(content, scheduled_time, media_files, timezone)
#         else:
#             result = job_scheduler.manual_tweet(content, media_files)
            
#         # 注意：不再自动清理图片，以便在历史记录中查看
#         # 实际生产环境中可能需要一个定期清理任务
        
#         if result.get('success'):
#             return jsonify({
#                 'success': True,
#                 'message': '推文发送成功' if not scheduled_time else result.get('message'),
#                 'data': result
#             })
#         else:
#             return jsonify({
#                 'success': False,
#                 'message': '发送失败',
#                 'error': result.get('error')
#             }), 400

#     except Exception as e:
#         logger.error(f"处理发推请求失败: {e}")
#         return jsonify({
#             'success': False,
#             'message': '系统错误',
#             'error': str(e)
#         }), 500


@app.route('/api/history', methods=['GET'])
def get_history():
    """获取发推历史记录"""
    from history.history_manager import history_manager
    import shutil
    
    try:
        history = history_manager.get_history(limit=50)
        
        # 确保上传目录存在
        upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        
        # 处理图片路径，转换为 URL
        for record in history:
            if record.get('media_files'):
                processed_files = []
                for file_path in record['media_files']:
                    try:
                        filename = os.path.basename(file_path)
                        
                        # 检查文件是否已经在 static/uploads
                        if 'static/uploads' in file_path:
                            url = f"/static/uploads/{filename}"
                            processed_files.append(url)
                        else:
                            # 兼容旧路径（如 tmp/）
                            # 如果文件存在，将其复制到 static/uploads
                            if os.path.exists(file_path):
                                target_path = os.path.join(upload_dir, filename)
                                # 如果目标文件不存在，或者源文件更新，则复制
                                if not os.path.exists(target_path):
                                    shutil.copy2(file_path, target_path)
                                    logger.info(f"迁移旧图片到 uploads: {filename}")
                                
                                url = f"/static/uploads/{filename}"
                                processed_files.append(url)
                            else:
                                # 文件丢失，保留原路径或标记错误
                                logger.warning(f"图片文件未找到: {file_path}")
                                processed_files.append(file_path)
                    except Exception as e:
                        logger.error(f"处理图片路径失败 {file_path}: {e}")
                        processed_files.append(file_path)
                        
                record['media_urls'] = processed_files
                
        return jsonify({
            'success': True,
            'data': history
        })
    except Exception as e:
        logger.error(f"获取历史记录失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/settings', methods=['GET'])
def get_settings():
    """获取当前设置"""
    try:
        twitter_config = config_loader.get_twitter_config()
        return jsonify({
            'success': True,
            'data': {
                'enable_auto_post': twitter_config.get('enable_auto_post', False)
            }
        })
    except Exception as e:
        logger.error(f"获取设置失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/settings/update', methods=['POST'])
def update_settings():
    """更新设置"""
    try:
        data = request.get_json() or {}
        
        if 'enable_auto_post' in data:
            success = config_loader.update_twitter_config('enable_auto_post', data['enable_auto_post'])
            if success:
                return jsonify({
                    'success': True,
                    'message': '设置已更新'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '保存设置失败'
                }), 500
                
        return jsonify({
            'success': False,
            'message': '无效的设置项'
        }), 400
        
    except Exception as e:
        logger.error(f"更新设置失败: {e}")
        return jsonify({
            'success': False,
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


@app.route('/recap/manual', methods=['POST'])
def manual_recap():
    """手动触发每日大盘复盘"""
    try:
        logger.info("收到手动触发大盘复盘请求")

        # 执行大盘复盘
        result = job_scheduler.manual_daily_recap()

        if result.get('success'):
            return jsonify({
                'success': True,
                'message': '大盘复盘发布成功',
                'data': {
                    'thread_url': result.get('thread_url'),
                    'tweet_count': result.get('tweet_count'),
                    'tweets': result.get('tweets')
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': '大盘复盘发布失败',
                'error': result.get('error')
            }), 400

    except Exception as e:
        logger.error(f"手动触发大盘复盘失败: {e}")
        return jsonify({
            'success': False,
            'message': '触发大盘复盘时发生错误',
            'error': str(e)
        }), 500


@app.route('/recap/fetch-data', methods=['POST'])
def fetch_market_data():
    """手动获取市场数据"""
    try:
        logger.info("收到手动获取市场数据请求")

        from data_sources.fetch_real_data import fetch_all_market_data
        data = fetch_all_market_data(save_to_file=True)

        if data:
            return jsonify({
                'success': True,
                'message': '市场数据获取成功',
                'data': data
            })
        else:
            return jsonify({
                'success': False,
                'message': '市场数据获取失败'
            }), 400

    except Exception as e:
        logger.error(f"获取市场数据失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取市场数据时发生错误',
            'error': str(e)
        }), 500


@app.route('/recap/generate', methods=['POST'])
def generate_recap():
    """生成复盘内容（不发布）"""
    try:
        logger.info("收到生成复盘内容请求")

        # 获取自定义提示词
        data = request.get_json() or {}
        custom_prompt = data.get('custom_prompt')

        from recap.generate_summary import generate_daily_recap
        thread = generate_daily_recap(custom_prompt)

        if thread:
            return jsonify({
                'success': True,
                'message': '复盘内容生成成功',
                'data': {
                    'tweet_count': len(thread),
                    'tweets': thread
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': '复盘内容生成失败'
            }), 400

    except Exception as e:
        logger.error(f"生成复盘内容失败: {e}")
        return jsonify({
            'success': False,
            'message': '生成复盘内容时发生错误',
            'error': str(e)
        }), 500


def signal_handler(signum, frame):
    """信号处理器，用于优雅关闭"""
    logger.info("接收到关闭信号，正在关闭系统...")
    
    # 停止调度器
    job_scheduler.stop()
    
    logger.info("系统已关闭")
    sys.exit(0)

@app.route('/tweet/run-bot', methods=['POST'])
def run_bot():
    """
    手动触发自动推文流程（获取 Telegram → ChromaDB → 聚类 → 发推）
    """
    try:
        # 用线程运行，避免阻塞 Flask
        threading.Thread(target=run_once).start()
        return jsonify({
            'success': True,
            'message': '自动推文任务已启动'
        })
    except Exception as e:
        logger.error(f"触发自动推文失败: {e}")
        return jsonify({
            'success': False,
            'message': '触发自动推文失败',
            'error': str(e)
        }), 500

@app.route("/tweet/run-once", methods=["POST"])
def manual_run_once():
    try:
        run_once()
        return jsonify({
            "success": True,
            "msg": "已手动触发完整发推流程"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500




@app.route('/api/jobs/<job_id>/cancel', methods=['POST'])
def cancel_job(job_id):
    """取消定时任务"""
    try:
        result = job_scheduler.cancel_job(job_id)
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
    
    # 验证 LLM API Key（非阻塞，仅警告）
    if not llm_client.validate_api_key():
        logger.warning("LLM API Key 验证失败，LLM 功能将不可用，但系统将继续运行")
    
    # 设置每日大盘复盘任务（如果启用）
    scheduler_config = config_loader.get_scheduler_config()
    daily_recap_config = scheduler_config.get('daily_recap', {})

    if daily_recap_config.get('enabled', False):
        recap_time = daily_recap_config.get('recap_time', '20:00')
        job_scheduler.setup_daily_recap_job(recap_time)
        logger.info(f"每日大盘复盘已启用，时间: {recap_time}")
    else:
        logger.info("每日大盘复盘未启用")

    # 初始化系统里加
    job_scheduler.setup_crypto_hot_job()
    
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
