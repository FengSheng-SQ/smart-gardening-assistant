"""
数据库配置和模型
使用SQLite存储用户和聊天记录
"""
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
import sqlite3
from contextlib import contextmanager


# 数据库目录
DB_DIR = Path("data")
DB_PATH = DB_DIR / "gardening_assistant.db"


@contextmanager
def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 返回字典式行
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """初始化数据库表"""
    DB_DIR.mkdir(parents=True, exist_ok=True)

    with get_db() as conn:
        cursor = conn.cursor()

        # 用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                default_chat_mode TEXT DEFAULT 'fast'
            )
        """)

        # 聊天记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message_text TEXT NOT NULL,
                is_user BOOLEAN NOT NULL,
                audio_filename TEXT,
                image_filename TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                chat_mode TEXT DEFAULT 'fast',
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        # 检查并添加 image_filename 字段（对于已存在的数据库）
        cursor.execute("PRAGMA table_info(chat_messages)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'image_filename' not in columns:
            cursor.execute("ALTER TABLE chat_messages ADD COLUMN image_filename TEXT")
            print("✅ 已添加 image_filename 字段到 chat_messages 表")

        # 检查并添加 chat_mode 字段（对于已存在的数据库）
        if 'chat_mode' not in columns:
            cursor.execute("ALTER TABLE chat_messages ADD COLUMN chat_mode TEXT DEFAULT 'fast'")
            print("✅ 已添加 chat_mode 字段到 chat_messages 表")

        # 检查并添加 users 表的 default_chat_mode 字段
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in cursor.fetchall()]
        if 'default_chat_mode' not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN default_chat_mode TEXT DEFAULT 'fast'")
            print("✅ 已添加 default_chat_mode 字段到 users 表")

        # 创建索引以加速查询
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_user_time
            ON chat_messages (user_id, created_at DESC)
        """)

        print(f"✅ 数据库初始化成功: {DB_PATH}")

        # 创建默认管理员账户
        _create_default_admin(cursor)


def _create_default_admin(cursor):
    """创建默认管理员账户"""
    try:
        from passlib.context import CryptContext
        # 尝试使用 bcrypt
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        password_hash = pwd_context.hash("admin123")
    except Exception as e:
        print(f"⚠️  bcrypt 不可用，使用 fallback: {e}")
        # 使用简单的SHA256哈希作为fallback
        import hashlib
        password_hash = hashlib.sha256("admin123".encode()).hexdigest()

    # 检查是否已存在管理员
    cursor.execute("SELECT id FROM users WHERE username = ?", ("admin",))
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            ("admin", password_hash)
        )
        print("✅ 默认管理员账户已创建")
        print("   用户名: admin")
        print("   密码: admin123")
    else:
        print("ℹ️  管理员账户已存在")


# 数据库操作类
class Database:
    """数据库操作封装"""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        import hashlib

        # 检查是否为 bcrypt 哈希（以 $2b$ 或 $2a$ 开头）
        if hashed_password.startswith("$2"):
            try:
                from passlib.context import CryptContext
                pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                return pwd_context.verify(plain_password, hashed_password)
            except Exception:
                pass

        # 使用 SHA256 验证（fallback）
        return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password

    @staticmethod
    def get_password_hash(password: str) -> str:
        """生成密码哈希"""
        try:
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            return pwd_context.hash(password)
        except Exception:
            # Fallback 到 SHA256
            import hashlib
            return hashlib.sha256(password.encode()).hexdigest()

    # 用户操作
    @staticmethod
    def get_user_by_username(username: str) -> Optional[dict]:
        """根据用户名获取用户"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, password_hash, created_at FROM users WHERE username = ?",
                (username,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    @staticmethod
    def create_user(username: str, password: str) -> Optional[int]:
        """创建新用户"""
        password_hash = Database.get_password_hash(password)
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, password_hash)
                )
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None  # 用户名已存在

    @staticmethod
    def update_last_login(user_id: int):
        """更新最后登录时间"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (datetime.now(), user_id)
            )

    @staticmethod
    def get_user_chat_mode(user_id: int) -> Optional[str]:
        """获取用户默认聊天模式"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT default_chat_mode FROM users WHERE id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            if row:
                return row[0] or 'fast'  # 默认返回 'fast'
            return 'fast'

    @staticmethod
    def update_user_chat_mode(user_id: int, chat_mode: str) -> bool:
        """更新用户默认聊天模式"""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET default_chat_mode = ? WHERE id = ?",
                    (chat_mode, user_id)
                )
                return cursor.rowcount > 0
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"❌ 更新用户聊天模式失败: {e}")
            return False

    # 聊天记录操作
    @staticmethod
    def save_chat_message(user_id: int, message_text: str, is_user: bool, audio_filename: Optional[str] = None, image_filename: Optional[str] = None, chat_mode: str = 'fast') -> int:
        """保存聊天消息"""
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"💾 Database.save_chat_message 被调用: user_id={user_id}, is_user={is_user}, chat_mode={chat_mode}, text={message_text[:30]}...")

        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO chat_messages
                       (user_id, message_text, is_user, audio_filename, image_filename, chat_mode)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (user_id, message_text, is_user, audio_filename, image_filename, chat_mode)
                )
                msg_id = cursor.lastrowid
                logger.info(f"✅ 消息已保存到数据库: message_id={msg_id}, chat_mode={chat_mode}")
                return msg_id
        except Exception as e:
            logger.error(f"❌ 保存消息到数据库失败: {e}")
            raise

    @staticmethod
    def get_chat_history(user_id: int, limit: int = 100) -> list:
        """获取用户聊天历史"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, message_text, is_user, audio_filename, image_filename, created_at
                   FROM chat_messages
                   WHERE user_id = ?
                   ORDER BY id ASC
                   LIMIT ?""",
                (user_id, limit)
            )
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def clear_chat_history(user_id: int) -> int:
        """清空用户聊天历史"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
            return cursor.rowcount

    @staticmethod
    def delete_chat_message(message_id: int, user_id: int) -> bool:
        """删除单条聊天消息（验证user_id以确保只能删除自己的消息）"""
        import logging
        logger = logging.getLogger(__name__)

        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM chat_messages WHERE id = ? AND user_id = ?",
                    (message_id, user_id)
                )
                deleted = cursor.rowcount > 0
                if deleted:
                    logger.info(f"✅ 消息已删除: message_id={message_id}, user_id={user_id}")
                else:
                    logger.warning(f"⚠️  消息不存在或无权删除: message_id={message_id}, user_id={user_id}")
                return deleted
        except Exception as e:
            logger.error(f"❌ 删除消息失败: {e}")
            return False

    @staticmethod
    def delete_chat_messages(message_ids: list, user_id: int) -> int:
        """批量删除聊天消息（验证user_id以确保只能删除自己的消息）"""
        import logging
        logger = logging.getLogger(__name__)

        if not message_ids:
            return 0

        try:
            with get_db() as conn:
                cursor = conn.cursor()
                # 构建占位符字符串
                placeholders = ','.join(['?' for _ in message_ids])
                query = f"DELETE FROM chat_messages WHERE id IN ({placeholders}) AND user_id = ?"
                params = message_ids + [user_id]

                cursor.execute(query, params)
                deleted_count = cursor.rowcount
                logger.info(f"✅ 批量删除消息: 删除了 {deleted_count} 条消息, user_id={user_id}")
                return deleted_count
        except Exception as e:
            logger.error(f"❌ 批量删除消息失败: {e}")
            return 0
