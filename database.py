"""
Модуль базы данных для управления целями (SQLite).
Хранит информацию о целях, статусах и уведомлениях.
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "goals.db")


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Создает необходимые таблицы, если их нет."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    category TEXT DEFAULT 'Общее',
                    deadline TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    status TEXT NOT NULL DEFAULT 'active', -- 'active', 'completed', 'failed'
                    notified_1d INTEGER DEFAULT 0,
                    notified_expired INTEGER DEFAULT 0
                )
            """)
            
            # Если база только что создана, добавим демонстрационные примеры
            cursor.execute("SELECT COUNT(*) FROM goals")
            if cursor.fetchone()[0] == 0:
                now = datetime.now()
                from datetime import timedelta
                
                # 1. Срочная цель (сегодня в 23:59)
                d1 = (now + timedelta(hours=18)).strftime("%Y-%m-%d %H:%M:%S")
                # 2. На 3 дня
                d2 = (now + timedelta(days=3)).replace(hour=20, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")
                # 3. На неделю
                d3 = (now + timedelta(days=7)).replace(hour=18, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")
                # 4. Проваленная цель (дедлайн прошёл вчера)
                d4 = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
                
                created_now = now.strftime("%Y-%m-%d %H:%M:%S")
                
                cursor.executemany("""
                    INSERT INTO goals (title, description, category, deadline, created_at, status, notified_1d, notified_expired)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    ("🚀 Протестировать напоминатель и настроить фильтры", "Создайте свою первую цель или отредактируйте существующие карточки.", "Личное", d1, created_now, "active", 1, 0),
                    ("📚 Прочитать 30 страниц книги или статьи", "Полезная привычка на ближайшие 3 дня.", "Учеба", d2, created_now, "active", 0, 0),
                    ("🏃 Сделать 3 пробежки или зарядки за неделю", "Следите за здоровьем и повышайте тонус.", "Здоровье / Спорт", d3, created_now, "active", 0, 0),
                    ("⏰ Невыполненная старая задача (пример провала)", "Срок этой цели истёк вчера, поэтому она автоматически попала в проваленные. Вы можете продлить её или удалить!", "Работа / Проекты", d4, created_now, "failed", 1, 1),
                ])

            conn.commit()

    def add_goal(self, title: str, description: str, deadline: datetime, category: str = "Общее") -> int:
        """Добавляет новую цель."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        deadline_str = deadline.strftime("%Y-%m-%d %H:%M:%S")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO goals (title, description, category, deadline, created_at, status)
                VALUES (?, ?, ?, ?, ?, 'active')
            """, (title.strip(), description.strip(), category.strip(), deadline_str, now_str))
            conn.commit()
            return cursor.lastrowid

    def update_goal(self, goal_id: int, title: str, description: str, deadline: datetime, category: str = "Общее"):
        """Обновляет информацию о цели."""
        deadline_str = deadline.strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE goals 
                SET title = ?, description = ?, category = ?, deadline = ?
                WHERE id = ?
            """, (title.strip(), description.strip(), category.strip(), deadline_str, goal_id))
            conn.commit()

    def set_status(self, goal_id: int, status: str):
        """Меняет статус цели: 'active', 'completed', 'failed'."""
        completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if status == "completed" else None
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE goals 
                SET status = ?, completed_at = ?
                WHERE id = ?
            """, (status, completed_at, goal_id))
            conn.commit()

    def delete_goal(self, goal_id: int):
        """Удаляет цель из базы."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
            conn.commit()

    def get_goal(self, goal_id: int) -> Optional[Dict]:
        """Возвращает цель по ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM goals WHERE id = ?", (goal_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def check_and_update_expired_goals(self) -> List[Dict]:
        """
        Проверяет активные цели, чей дедлайн наступил.
        Автоматически переводит их в статус 'failed' и возвращает список новоиспечённых проваленных целей.
        """
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        
        expired_goals = []
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM goals 
                WHERE status = 'active' AND deadline < ?
            """, (now_str,))
            rows = cursor.fetchall()
            
            for row in rows:
                g = dict(row)
                expired_goals.append(g)
                cursor.execute("""
                    UPDATE goals 
                    SET status = 'failed', notified_expired = 1
                    WHERE id = ?
                """, (g["id"],))
            
            conn.commit()
            
        return expired_goals

    def get_goals_needing_reminder(self) -> List[Dict]:
        """
        Возвращает активные цели, до дедлайна которых осталось менее 24 часов,
        и уведомление за 1 день ещё не было отправлено.
        """
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        
        reminders = []
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM goals 
                WHERE status = 'active' 
                  AND deadline >= ? 
                  AND notified_1d = 0
            """, (now_str,))
            rows = cursor.fetchall()
            
            for row in rows:
                g = dict(row)
                d_time = datetime.strptime(g["deadline"], "%Y-%m-%d %H:%M:%S")
                diff = d_time - now
                if diff.total_seconds() <= 86400: # меньше 24 часов
                    reminders.append(g)
                    cursor.execute("UPDATE goals SET notified_1d = 1 WHERE id = ?", (g["id"],))
            conn.commit()
            
        return reminders

    def get_goals(self, filter_type: str = "active", search_query: str = "", sort_by: str = "deadline_asc") -> List[Dict]:
        """
        Возвращает цели с учётом фильтра, поиска и сортировки.
        filter_type:
          - 'active': Все активные
          - 'urgent_1d': До 1 дня (до 24 ч)
          - 'days_3': До 3 дней
          - 'week_1': До 7 дней
          - 'weeks_2': До 14 дней
          - 'month_1': До 30 дней
          - 'failed': Проваленные цели
          - 'completed': Выполненные цели
          - 'all': Все цели
        """
        now = datetime.now()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM goals WHERE 1=1"
            params = []
            
            if search_query:
                query += " AND (title LIKE ? OR description LIKE ? OR category LIKE ?)"
                wildcard = f"%{search_query.strip()}%"
                params.extend([wildcard, wildcard, wildcard])
            
            cursor.execute(query, params)
            all_rows = [dict(r) for r in cursor.fetchall()]

        filtered = []
        for g in all_rows:
            d_time = datetime.strptime(g["deadline"], "%Y-%m-%d %H:%M:%S")
            diff_seconds = (d_time - now).total_seconds()
            diff_days = diff_seconds / 86400.0

            if filter_type == "active":
                if g["status"] == "active":
                    filtered.append(g)
            elif filter_type == "urgent_1d":
                if g["status"] == "active" and 0 <= diff_days <= 1.0:
                    filtered.append(g)
            elif filter_type == "days_3":
                if g["status"] == "active" and 0 <= diff_days <= 3.0:
                    filtered.append(g)
            elif filter_type == "week_1":
                if g["status"] == "active" and 0 <= diff_days <= 7.0:
                    filtered.append(g)
            elif filter_type == "weeks_2":
                if g["status"] == "active" and 0 <= diff_days <= 14.0:
                    filtered.append(g)
            elif filter_type == "month_1":
                if g["status"] == "active" and 0 <= diff_days <= 30.0:
                    filtered.append(g)
            elif filter_type == "failed":
                if g["status"] == "failed":
                    filtered.append(g)
            elif filter_type == "completed":
                if g["status"] == "completed":
                    filtered.append(g)
            elif filter_type == "all":
                filtered.append(g)

        # Сортировка
        if sort_by == "deadline_asc":
            filtered.sort(key=lambda x: x["deadline"])
        elif sort_by == "deadline_desc":
            filtered.sort(key=lambda x: x["deadline"], reverse=True)
        elif sort_by == "created_desc":
            filtered.sort(key=lambda x: x["created_at"], reverse=True)
        elif sort_by == "title_asc":
            filtered.sort(key=lambda x: x["title"].lower())

        return filtered

    def get_statistics(self) -> Dict[str, int]:
        """Возвращает общую статистику по целям."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, COUNT(*) as cnt FROM goals GROUP BY status")
            rows = cursor.fetchall()
            
            stats = {"total": 0, "active": 0, "completed": 0, "failed": 0}
            for row in rows:
                st = row["status"]
                cnt = row["cnt"]
                if st in stats:
                    stats[st] = cnt
                stats["total"] += cnt
                
            return stats
