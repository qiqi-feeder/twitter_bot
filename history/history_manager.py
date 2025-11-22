import json
import os
import time
from datetime import datetime
from typing import List, Dict, Optional
from utils.logger import logger

class HistoryManager:
    """
    历史记录管理器
    负责管理发推历史记录的存储和检索
    """
    
    def __init__(self, data_dir: str = 'data'):
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), data_dir)
        self.history_file = os.path.join(self.data_dir, 'history.json')
        self._ensure_data_dir()
        
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
    def _load_history(self) -> List[Dict]:
        """加载历史记录"""
        if not os.path.exists(self.history_file):
            return []
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载历史记录失败: {e}")
            return []
            
    def _save_history(self, history: List[Dict]):
        """保存历史记录"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存历史记录失败: {e}")
            
    def add_record(self, job_id: str, content: str, scheduled_time: str, status: str = 'pending', media_files: List[str] = None):
        """
        添加一条新记录
        
        Args:
            job_id: 任务 ID
            content: 推文内容
            scheduled_time: 计划发送时间 (ISO 格式)
            status: 状态 (pending, sent, failed, cancelled)
            media_files: 媒体文件列表
        """
        history = self._load_history()
        
        record = {
            'id': job_id,
            'content': content,
            'scheduled_time': scheduled_time,
            'status': status,
            'created_at': datetime.now().isoformat(),
            'media_files': media_files or [],
            'tweet_id': None,
            'tweet_url': None,
            'error': None
        }
        
        history.append(record)
        self._save_history(history)
        logger.info(f"已添加历史记录: {job_id}")
        
    def update_status(self, job_id: str, status: str, tweet_id: str = None, tweet_url: str = None, error: str = None):
        """
        更新记录状态
        
        Args:
            job_id: 任务 ID
            status: 新状态
            tweet_id: 推文 ID (仅成功时)
            tweet_url: 推文 URL (仅成功时)
            error: 错误信息 (仅失败时)
        """
        history = self._load_history()
        updated = False
        
        for record in history:
            if record['id'] == job_id:
                record['status'] = status
                if tweet_id:
                    record['tweet_id'] = tweet_id
                if tweet_url:
                    record['tweet_url'] = tweet_url
                if error:
                    record['error'] = error
                updated = True
                break
                
        if updated:
            self._save_history(history)
            logger.info(f"已更新历史记录状态: {job_id} -> {status}")
        else:
            logger.warning(f"未找到历史记录: {job_id}")
            
    def get_history(self, limit: int = 50) -> List[Dict]:
        """
        获取历史记录列表 (按时间倒序)
        
        Args:
            limit: 返回记录数量限制
            
        Returns:
            历史记录列表
        """
        history = self._load_history()
        # 按创建时间倒序排序
        history.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return history[:limit]

    def get_record(self, job_id: str) -> Optional[Dict]:
        """获取单条记录"""
        history = self._load_history()
        for record in history:
            if record['id'] == job_id:
                return record
        return None

# 全局实例
history_manager = HistoryManager()
