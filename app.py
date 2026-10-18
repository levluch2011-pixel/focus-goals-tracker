"""
Главное окно приложения Трекера и Напоминателя Целей на CustomTkinter.
"""

import customtkinter as ctk
from datetime import datetime
from typing import Dict, List, Optional
import tkinter.messagebox as messagebox

from database import Database
from notifier import Notifier
from dialogs import GoalDialog


class GoalTrackerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.db = Database()

        # Настройки темы
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("🎯 Напоминатель и Трекер Целей")
        
        # Центрирование окна по центру экрана пользователя
        window_width = 1060
        window_height = 700
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        pos_x = max(0, int((screen_width - window_width) / 2))
        pos_y = max(0, int((screen_height - window_height) / 2))
        self.geometry(f"{window_width}x{window_height}+{pos_x}+{pos_y}")
        self.minsize(860, 560)

        # Состояние фильтрации: по умолчанию показываем все активные цели
        self.current_filter = "active"
        self.current_sort = "deadline_asc"
        self.search_text = ""

        self._build_layout()
        self.set_filter("active")

        # Фоновый опрос для автопроверки проваленных целей и дедлайнов (каждые 30 секунд)
        self.after(30000, self._periodic_check)

    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ------------------ ЛЕВАЯ ПАНЕЛЬ (SIDEBAR) ------------------
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(13, weight=1) # Распорка для выталкивания темы вниз

        # Логотип и название
        logo_label = ctk.CTkLabel(
            self.sidebar,
            text="🎯 МОИ ЦЕЛИ",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        logo_label.grid(row=0, column=0, padx=20, pady=(20, 15), sticky="w")

        # Кнопка создания новой цели
        add_btn = ctk.CTkButton(
            self.sidebar,
            text="➕ Новая цель",
            height=40,
            fg_color="#10B981",
            hover_color="#059669",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.open_add_dialog
        )
        add_btn.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="ew")

        # Заголовок раздела сроков
        filter_section_lbl = ctk.CTkLabel(
            self.sidebar,
            text="СОРТИРОВКА ПО СРОКАМ",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="gray"
        )
        filter_section_lbl.grid(row=2, column=0, padx=20, pady=(10, 5), sticky="w")

        # Кнопки фильтров по срокам
        self.filter_buttons = {}

        time_filters = [
            ("urgent_1d", "⚡ Остался 1 день", "#F59E0B"),
            ("days_3", "⏳ На 3 дня", "#3B82F6"),
            ("week_1", "📅 На неделю", "#3B82F6"),
            ("weeks_2", "🗓️ На 2 недели", "#3B82F6"),
            ("month_1", "🌙 На месяц", "#3B82F6"),
            ("active", "📌 Все активные", "#6366F1"),
        ]

        curr_row = 3
        for f_key, f_title, color in time_filters:
            btn = ctk.CTkButton(
                self.sidebar,
                text=f_title,
                anchor="w",
                height=34,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray80", "gray25"),
                font=ctk.CTkFont(size=13),
                command=lambda k=f_key: self.set_filter(k)
            )
            btn.grid(row=curr_row, column=0, padx=12, pady=2, sticky="ew")
            self.filter_buttons[f_key] = btn
            curr_row += 1

        # Заголовок раздела статусов
        status_section_lbl = ctk.CTkLabel(
            self.sidebar,
            text="СТАТУСЫ",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="gray"
        )
        status_section_lbl.grid(row=curr_row, column=0, padx=20, pady=(15, 5), sticky="w")
        curr_row += 1

        status_filters = [
            ("failed", "❌ Проваленные цели", "#EF4444"),
            ("completed", "✅ Выполненные цели", "#10B981"),
            ("all", "📋 Все цели", "#64748B"),
        ]

        for f_key, f_title, color in status_filters:
            btn = ctk.CTkButton(
                self.sidebar,
                text=f_title,
                anchor="w",
                height=34,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray80", "gray25"),
                font=ctk.CTkFont(size=13),
                command=lambda k=f_key: self.set_filter(k)
            )
            btn.grid(row=curr_row, column=0, padx=12, pady=2, sticky="ew")
            self.filter_buttons[f_key] = btn
            curr_row += 1

        # Нижняя панель темы и информации
        bottom_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom_frame.grid(row=14, column=0, padx=15, pady=15, sticky="ew")

        theme_lbl = ctk.CTkLabel(bottom_frame, text="Тема оформления:", font=ctk.CTkFont(size=11), text_color="gray")
        theme_lbl.pack(anchor="w", pady=(0, 2))

        self.theme_option = ctk.CTkOptionMenu(
            bottom_frame,
            values=["Тёмная", "Светлая"],
            height=28,
            command=self.change_theme
        )
        self.theme_option.pack(fill="x")
        self.theme_option.set("Тёмная")

        # ------------------ ОСНОВНАЯ ОБЛАСТЬ (MAIN CONTENT) ------------------
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=15)
        self.main_container.grid_rowconfigure(2, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        # 1. Верхняя панель управления (Поиск, Сортировка, Заголовок)
        top_bar = ctk.CTkFrame(self.main_container, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        # Заголовок текущего раздела
        self.current_title_lbl = ctk.CTkLabel(
            top_bar,
            text="⚡ Остался 1 день",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        self.current_title_lbl.pack(side="left")

        # Поиск и Сортировка справа
        right_tools = ctk.CTkFrame(top_bar, fg_color="transparent")
        right_tools.pack(side="right")

        # Поиск
        self.search_entry = ctk.CTkEntry(
            right_tools,
            placeholder_text="🔍 Поиск цели...",
            width=200,
            height=34
        )
        self.search_entry.pack(side="left", padx=(0, 8))
        self.search_entry.bind("<KeyRelease>", self.on_search_change)

        # Выпадающий список сортировки
        self.sort_option = ctk.CTkOptionMenu(
            right_tools,
            values=[
                "Сначала ближайшие сроки",
                "Сначала дальние сроки",
                "Сначала новые добавленные",
                "По алфавиту (А-Я)"
            ],
            width=210,
            height=34,
            command=self.on_sort_change
        )
        self.sort_option.pack(side="left")

        # 2. Карточки статистики
        self.stats_frame = ctk.CTkFrame(self.main_container, fg_color=("gray90", "gray17"), corner_radius=10)
        self.stats_frame.grid(row=1, column=0, sticky="ew", pady=(0, 12), ipady=4)
        
        self.stats_labels = {}
        stat_items = [
            ("total", "📋 Всего целей: 0", ("gray20", "gray80")),
            ("active", "📌 В процессе: 0", "#3B82F6"),
            ("urgent", "⚡ Горят (1 день): 0", "#F59E0B"),
            ("completed", "✅ Выполнено: 0", "#10B981"),
            ("failed", "❌ Провалено: 0", "#EF4444"),
        ]

        for i, (k, text, col) in enumerate(stat_items):
            lbl = ctk.CTkLabel(
                self.stats_frame,
                text=text,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=col
            )
            lbl.pack(side="left", expand=True, padx=8, pady=4)
            self.stats_labels[k] = lbl

        # 3. Список целей (Scrollable frame)
        self.cards_scroll = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        self.cards_scroll.grid(row=2, column=0, sticky="nsew")

    def set_filter(self, filter_key: str):
        """Переключает фильтр целей."""
        self.current_filter = filter_key

        # Обновляем внешний вид кнопок сайдбара
        for k, btn in self.filter_buttons.items():
            if k == filter_key:
                btn.configure(fg_color=("gray75", "#374151"), font=ctk.CTkFont(size=13, weight="bold"))
            else:
                btn.configure(fg_color="transparent", font=ctk.CTkFont(size=13))

        titles_map = {
            "urgent_1d": "⚡ До дедлайна остался 1 день (Срочные)",
            "days_3": "⏳ Цели на 3 дня",
            "week_1": "📅 Цели на неделю (до 7 дней)",
            "weeks_2": "🗓️ Цели на 2 недели (до 14 дней)",
            "month_1": "🌙 Цели на месяц (до 30 дней)",
            "active": "📌 Все активные цели",
            "failed": "❌ Проваленные цели",
            "completed": "✅ Успешно выполненные цели",
            "all": "📋 Все цели в базе",
        }
        self.current_title_lbl.configure(text=titles_map.get(filter_key, "Цели"))
        self.refresh_cards()

    def on_sort_change(self, choice: str):
        mapping = {
            "Сначала ближайшие сроки": "deadline_asc",
            "Сначала дальние сроки": "deadline_desc",
            "Сначала новые добавленные": "created_desc",
            "По алфавиту (А-Я)": "title_asc"
        }
        self.current_sort = mapping.get(choice, "deadline_asc")
        self.refresh_cards()

    def on_search_change(self, event=None):
        self.search_text = self.search_entry.get().strip()
        self.refresh_cards()

    def change_theme(self, choice: str):
        if choice == "Тёмная":
            ctk.set_appearance_mode("dark")
        else:
            ctk.set_appearance_mode("light")

    def _periodic_check(self):
        """Периодическая проверка просроченных целей и отправка напоминаний."""
        # 1. Автоперевод просроченных целей в 'failed'
        expired = self.db.check_and_update_expired_goals()
        for g in expired:
            Notifier.notify_expired(g["title"])

        # 2. Напоминания за 24ч
        reminders = self.db.get_goals_needing_reminder()
        for g in reminders:
            now = datetime.now()
            d_time = datetime.strptime(g["deadline"], "%Y-%m-%d %H:%M:%S")
            hours_left = max(1, int((d_time - now).total_seconds() // 3600))
            Notifier.notify_reminder(g["title"], hours_left)

        # 3. Обновление интерфейса
        self.refresh_all()

        # Планируем следующий запуск через 30 секунд
        self.after(30000, self._periodic_check)

    def refresh_all(self):
        """Полное обновление статистики, кнопок и списка карточек."""
        # Проверяем просроченные перед выводом
        expired = self.db.check_and_update_expired_goals()
        for g in expired:
            Notifier.notify_expired(g["title"])

        self.update_statistics()
        self.refresh_cards()

    def update_statistics(self):
        """Обновляет бейджи статистики вверху."""
        stats = self.db.get_statistics()
        now = datetime.now()
        
        # Считаем горящие (urgent <= 1d)
        urgent_goals = self.db.get_goals(filter_type="urgent_1d")
        urgent_cnt = len(urgent_goals)

        self.stats_labels["total"].configure(text=f"📋 Всего: {stats['total']}")
        self.stats_labels["active"].configure(text=f"📌 В процессе: {stats['active']}")
        self.stats_labels["urgent"].configure(text=f"⚡ Горят: {urgent_cnt}")

        total_done_or_failed = stats["completed"] + stats["failed"]
        if total_done_or_failed > 0:
            comp_pct = int((stats["completed"] / total_done_or_failed) * 100)
            fail_pct = int((stats["failed"] / total_done_or_failed) * 100)
            self.stats_labels["completed"].configure(text=f"✅ Выполнено: {stats['completed']} ({comp_pct}%)")
            self.stats_labels["failed"].configure(text=f"❌ Провалено: {stats['failed']} ({fail_pct}%)")
        else:
            self.stats_labels["completed"].configure(text=f"✅ Выполнено: {stats['completed']}")
            self.stats_labels["failed"].configure(text=f"❌ Провалено: {stats['failed']}")

    def refresh_cards(self):
        """Перерисовывает список карточек целей в скролле."""
        for widget in self.cards_scroll.winfo_children():
            widget.destroy()

        goals = self.db.get_goals(
            filter_type=self.current_filter,
            search_query=self.search_text,
            sort_by=self.current_sort
        )

        if not goals:
            empty_frame = ctk.CTkFrame(self.cards_scroll, fg_color="transparent")
            empty_frame.pack(fill="both", expand=True, pady=60)
            
            icon = "🎉" if self.current_filter == "urgent_1d" else "📝"
            empty_title = "В этом разделе пока нет целей"
            if self.current_filter == "urgent_1d":
                empty_title = "Горящих целей на ближайший день нет! Отличная работа."
            elif self.current_filter == "failed":
                empty_title = "Проваленных целей нет! Так держать!"

            ctk.CTkLabel(
                empty_frame,
                text=icon,
                font=ctk.CTkFont(size=48)
            ).pack()

            ctk.CTkLabel(
                empty_frame,
                text=empty_title,
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color="gray"
            ).pack(pady=(10, 5))

            if self.current_filter in ["urgent_1d", "active"]:
                ctk.CTkButton(
                    empty_frame,
                    text="➕ Поставить новую цель",
                    fg_color="#10B981",
                    hover_color="#059669",
                    command=self.open_add_dialog
                ).pack(pady=10)
            return

        for goal in goals:
            self._render_goal_card(goal)

    def _render_goal_card(self, goal: Dict):
        """Отрисовывает одну карточку цели."""
        now = datetime.now()
        deadline = datetime.strptime(goal["deadline"], "%Y-%m-%d %H:%M:%S")
        diff = deadline - now
        total_seconds = diff.total_seconds()
        diff_days = total_seconds / 86400.0

        status = goal["status"]

        # Цветовое кодирование карточки
        card_border_width = 1

        if status == "completed":
            card_border_color = "#10B981"
            badge_text = "✅ Выполнено"
            badge_color = "#10B981"
        elif status == "failed":
            card_border_color = "#EF4444"
            badge_text = "❌ Провалена"
            badge_color = "#EF4444"
        else:
            # Active
            if total_seconds < 0:
                card_border_color = "#EF4444"
                badge_text = "⚠️ Срок истёк"
                badge_color = "#EF4444"
            elif diff_days <= 1.0:
                card_border_color = "#F59E0B"
                card_border_width = 2
                badge_text = "⚡ Срочно (до 1 дня)"
                badge_color = "#F59E0B"
            elif diff_days <= 3.0:
                card_border_color = "#3B82F6"
                badge_text = "⏳ До 3 дней"
                badge_color = "#3B82F6"
            elif diff_days <= 7.0:
                card_border_color = "#6366F1"
                badge_text = "📅 До недели"
                badge_color = "#6366F1"
            elif diff_days <= 14.0:
                card_border_color = "#8B5CF6"
                badge_text = "🗓️ До 2 недель"
                badge_color = "#8B5CF6"
            else:
                card_border_color = "#64748B"
                badge_text = "🌙 До месяца+"
                badge_color = "#64748B"

        card = ctk.CTkFrame(
            self.cards_scroll,
            fg_color=("gray95", "gray18"),
            border_color=card_border_color,
            border_width=card_border_width,
            corner_radius=10
        )
        card.pack(fill="x", pady=6, padx=4)

        # Контейнер содержимого карточки
        content_box = ctk.CTkFrame(card, fg_color="transparent")
        content_box.pack(fill="x", padx=15, pady=12)

        # 1. Верхняя строка: Категория, Бейдж статуса/срока, Дата
        top_row = ctk.CTkFrame(content_box, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 6))

        # Категория
        cat_lbl = ctk.CTkLabel(
            top_row,
            text=f"📂 {goal.get('category', 'Общее')}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("gray40", "gray60")
        )
        cat_lbl.pack(side="left")

        # Бейдж срока / статуса
        status_badge = ctk.CTkLabel(
            top_row,
            text=f" {badge_text} ",
            fg_color=badge_color,
            text_color="#FFFFFF",
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            height=20
        )
        status_badge.pack(side="left", padx=10)

        # Обратный отсчет / статус дедлайна
        countdown_text = self._format_countdown(deadline, status)
        time_lbl = ctk.CTkLabel(
            top_row,
            text=countdown_text,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=badge_color if status != "completed" else "#10B981"
        )
        time_lbl.pack(side="right")

        # 2. Название цели
        title_font = ctk.CTkFont(size=16, weight="bold")
        title_lbl = ctk.CTkLabel(
            content_box,
            text=goal["title"],
            font=title_font,
            anchor="w",
            justify="left",
            wraplength=650
        )
        title_lbl.pack(anchor="w", pady=(0, 4))

        # 3. Описание цели (если есть)
        if goal.get("description"):
            desc_lbl = ctk.CTkLabel(
                content_box,
                text=goal["description"],
                font=ctk.CTkFont(size=13),
                text_color=("gray30", "gray70"),
                anchor="w",
                justify="left",
                wraplength=650
            )
            desc_lbl.pack(anchor="w", pady=(0, 6))

        # 4. Нижняя строка: Точная дата дедлайна и Кнопки действий
        bottom_row = ctk.CTkFrame(content_box, fg_color="transparent")
        bottom_row.pack(fill="x", pady=(6, 0))

        deadline_str = deadline.strftime("%d.%m.%Y, %H:%M")
        created_str = datetime.strptime(goal["created_at"], "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y")
        
        info_text = f"Дедлайн: {deadline_str}  •  Создана: {created_str}"
        if status == "completed" and goal.get("completed_at"):
            comp_str = datetime.strptime(goal["completed_at"], "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y %H:%M")
            info_text += f"  •  Завершена: {comp_str}"

        info_lbl = ctk.CTkLabel(
            bottom_row,
            text=info_text,
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        info_lbl.pack(side="left")

        # Кнопки действий справа
        actions_box = ctk.CTkFrame(bottom_row, fg_color="transparent")
        actions_box.pack(side="right")

        g_id = goal["id"]

        if status == "active":
            # Кнопка Выполнено
            done_btn = ctk.CTkButton(
                actions_box,
                text="✅ Выполнить",
                height=28,
                width=100,
                fg_color="#10B981",
                hover_color="#059669",
                font=ctk.CTkFont(size=12, weight="bold"),
                command=lambda gid=g_id, t=goal["title"]: self.mark_completed(gid, t)
            )
            done_btn.pack(side="left", padx=4)

            # Кнопка Провалено (ручной перевод)
            fail_btn = ctk.CTkButton(
                actions_box,
                text="❌ Провалена",
                height=28,
                width=95,
                fg_color="#EF4444",
                hover_color="#DC2626",
                font=ctk.CTkFont(size=12),
                command=lambda gid=g_id: self.mark_failed(gid)
            )
            fail_btn.pack(side="left", padx=4)

            # Кнопка Редактировать
            edit_btn = ctk.CTkButton(
                actions_box,
                text="✏️ Изменить",
                height=28,
                width=85,
                fg_color=("gray75", "gray28"),
                hover_color=("gray65", "gray35"),
                font=ctk.CTkFont(size=12),
                command=lambda g=goal: self.open_edit_dialog(g)
            )
            edit_btn.pack(side="left", padx=4)

        elif status == "failed":
            # Для проваленной цели: возможность продлить / возобновить
            reopen_btn = ctk.CTkButton(
                actions_box,
                text="🔄 Продлить / Вернуть",
                height=28,
                width=140,
                fg_color="#3B82F6",
                hover_color="#2563EB",
                font=ctk.CTkFont(size=12, weight="bold"),
                command=lambda g=goal: self.open_edit_dialog(g, reopen=True)
            )
            reopen_btn.pack(side="left", padx=4)

            # Или сразу закрыть как выполненную
            force_done_btn = ctk.CTkButton(
                actions_box,
                text="✅ Выполнено",
                height=28,
                width=95,
                fg_color="#10B981",
                hover_color="#059669",
                font=ctk.CTkFont(size=12),
                command=lambda gid=g_id, t=goal["title"]: self.mark_completed(gid, t)
            )
            force_done_btn.pack(side="left", padx=4)

        elif status == "completed":
            # Вернуть в активные
            reactivate_btn = ctk.CTkButton(
                actions_box,
                text="↩️ Возобновить",
                height=28,
                width=110,
                fg_color=("gray75", "gray28"),
                hover_color=("gray65", "gray35"),
                font=ctk.CTkFont(size=12),
                command=lambda gid=g_id: self.mark_active(gid)
            )
            reactivate_btn.pack(side="left", padx=4)

        # Кнопка Удалить
        del_btn = ctk.CTkButton(
            actions_box,
            text="🗑️",
            height=28,
            width=32,
            fg_color="transparent",
            hover_color=("gray80", "gray25"),
            text_color="#EF4444",
            font=ctk.CTkFont(size=14),
            command=lambda gid=g_id, t=goal["title"]: self.confirm_delete(gid, t)
        )
        del_btn.pack(side="left", padx=(4, 0))

    def _format_countdown(self, deadline: datetime, status: str) -> str:
        """Форматирует человеко-читаемое оставшееся или просроченное время."""
        if status == "completed":
            return "Успешно достигнута"

        now = datetime.now()
        diff = deadline - now
        total_seconds = diff.total_seconds()

        if total_seconds < 0:
            past_seconds = abs(total_seconds)
            days = int(past_seconds // 86400)
            hours = int((past_seconds % 86400) // 3600)
            if days > 0:
                return f"Просрочено на {days} дн. {hours} ч."
            elif hours > 0:
                mins = int((past_seconds % 3600) // 60)
                return f"Просрочено на {hours} ч. {mins} мин."
            else:
                mins = max(1, int(past_seconds // 60))
                return f"Просрочено на {mins} мин."
        else:
            days = int(total_seconds // 86400)
            hours = int((total_seconds % 86400) // 3600)
            mins = int((total_seconds % 3600) // 60)
            
            if days > 0:
                return f"Осталось: {days} дн. {hours} ч."
            elif hours > 0:
                return f"Осталось: {hours} ч. {mins} мин."
            else:
                return f"Осталось: {mins} мин."

    def open_add_dialog(self):
        """Открывает диалог добавления новой цели."""
        GoalDialog(self, on_save=self._on_save_goal)

    def open_edit_dialog(self, goal: Dict, reopen: bool = False):
        """Открывает диалог изменения существующей цели."""
        def handle_save(title, description, category, deadline, goal_id):
            self.db.update_goal(goal_id, title, description, deadline, category)
            if reopen:
                # Если цель была провалена, а дедлайн продлили в будущее — возвращаем статус в 'active'
                if deadline > datetime.now():
                    self.db.set_status(goal_id, "active")
            self.refresh_all()

        GoalDialog(self, on_save=handle_save, goal_data=goal)

    def _on_save_goal(self, title: str, description: str, category: str, deadline: datetime, goal_id: Optional[int] = None):
        """Callback при сохранении цели."""
        if goal_id:
            self.db.update_goal(goal_id, title, description, deadline, category)
        else:
            self.db.add_goal(title, description, deadline, category)
        self.refresh_all()

    def mark_completed(self, goal_id: int, title: str):
        self.db.set_status(goal_id, "completed")
        Notifier.notify_completed(title)
        self.refresh_all()

    def mark_failed(self, goal_id: int):
        self.db.set_status(goal_id, "failed")
        self.refresh_all()

    def mark_active(self, goal_id: int):
        self.db.set_status(goal_id, "active")
        self.refresh_all()

    def confirm_delete(self, goal_id: int, title: str):
        confirm = messagebox.askyesno(
            "Удаление цели",
            f"Вы уверены, что хотите удалить цель:\n«{title}»?",
            parent=self
        )
        if confirm:
            self.db.delete_goal(goal_id)
            self.refresh_all()
