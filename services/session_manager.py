"""
会话状态管理
"""
import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class SearchSession:
    """搜索会话状态"""
    keyword: str
    tag_type: Optional[str] = None
    order: str = ''
    current_page: int = 1
    total_pages: int = 1
    log_id: Optional[str] = None
    session_id: Optional[str] = None


class SessionManager:
    """会话管理器"""

    def __init__(self, data_path: Path):
        self.sessions_file = data_path / "sessions.json"
        self._ensure_file()

    def _ensure_file(self):
        """确保会话文件存在"""
        self.sessions_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.sessions_file.exists():
            self.sessions_file.write_text(json.dumps({}), encoding='utf-8')

    def _load(self) -> dict:
        """加载会话数据"""
        try:
            return json.loads(self.sessions_file.read_text(encoding='utf-8'))
        except Exception:
            return {}

    def _save(self, data: dict):
        """保存会话数据"""
        self.sessions_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    def get(self, user_id: str) -> Optional[SearchSession]:
        """获取用户会话"""
        data = self._load()
        if user_id in data:
            return SearchSession(**data[user_id])
        return None

    def set(self, user_id: str, session: SearchSession):
        """设置用户会话"""
        data = self._load()
        data[user_id] = asdict(session)
        self._save(data)

    def remove(self, user_id: str):
        """移除用户会话"""
        data = self._load()
        if user_id in data:
            del data[user_id]
            self._save(data)

    def exists(self, user_id: str) -> bool:
        """检查会话是否存在"""
        return user_id in self._load()