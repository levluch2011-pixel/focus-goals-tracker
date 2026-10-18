"""
Модальные окна создания и редактирования целей с быстрыми пресетами сроков.
"""

import customtkinter as ctk
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict


class GoalDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_save: Callable, goal_data: Optional[Dict] = None):
        super().__init__(parent)
        self.parent = parent
        self.on_save = on_save
        self.goal_data = goal_data

        is_edit = goal_data is not None
        title_text = "✏️ Редактировать цель" if is_edit else "➕ Новая цель"
        self.title(title_text)
        self.geometry("560x680")
        self.minsize(520, 620)
        self.resizable(False, False)

        # Центрирование окна относительно родителя
        self.transient(parent)
        self.grab_set()

        try:
            parent.update_idletasks()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_x()
            py = parent.winfo_y()
            dx = max(0, px + int((pw - 560) / 2))
            dy = max(0, py + int((ph - 680) / 2))
            self.geometry(f"560x680+{dx}+{dy}")
        except Exception:
            self.geometry("560x680")

        # Дата по умолчанию (завтра в 23:59)
        if is_edit:
            self.current_deadline = datetime.strptime(goal_data["deadline"], "%Y-%m-%d %H:%M:%S")
        else:
            self.current_deadline = (datetime.now() + timedelta(days=1)).replace(hour=23, minute=59, second=0)

        self._build_ui(is_edit)
        self.update_deadline_ui()

    def _build_ui(self, is_edit: bool):
        # Основной контейнер с отступами
        main_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Заголовок
        header_label = ctk.CTkLabel(
            main_frame,
            text="✏️ Редактирование цели" if is_edit else "🎯 Создание новой цели",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        header_label.pack(anchor="w", pady=(0, 15))

        # Поле "Название"
        name_label = ctk.CTkLabel(main_frame, text="Название цели *", font=ctk.CTkFont(size=14, weight="bold"))
        name_label.pack(anchor="w", pady=(5, 2))
        
        self.title_entry = ctk.CTkEntry(
            main_frame,
            placeholder_text="Например: Выучить 50 новых слов по английскому",
            height=38,
            font=ctk.CTkFont(size=13)
        )
        self.title_entry.pack(fill="x", pady=(0, 10))
        if is_edit and self.goal_data:
            self.title_entry.insert(0, self.goal_data.get("title", ""))

        # Поле "Категория"
        cat_label = ctk.CTkLabel(main_frame, text="Категория", font=ctk.CTkFont(size=13, weight="bold"))
        cat_label.pack(anchor="w", pady=(5, 2))

        categories = ["Общее", "Работа / Проекты", "Учеба", "Здоровье / Спорт", "Финансы", "Личное"]
        self.cat_option = ctk.CTkComboBox(main_frame, values=categories, height=35)
        self.cat_option.pack(fill="x", pady=(0, 10))
        if is_edit and self.goal_data:
            self.cat_option.set(self.goal_data.get("category", "Общее"))
        else:
            self.cat_option.set("Общее")

        # Поле "Описание / Заметки"
        desc_label = ctk.CTkLabel(main_frame, text="Описание и детали (необязательно)", font=ctk.CTkFont(size=13, weight="bold"))
        desc_label.pack(anchor="w", pady=(5, 2))

        self.desc_textbox = ctk.CTkTextbox(main_frame, height=90, font=ctk.CTkFont(size=13))
        self.desc_textbox.pack(fill="x", pady=(0, 15))
        if is_edit and self.goal_data and self.goal_data.get("description"):
            self.desc_textbox.insert("1.0", self.goal_data["description"])

        # Секция срока / Дедлайна
        deadline_header = ctk.CTkLabel(
            main_frame, 
            text="⏰ Срок выполнения (Дедлайн)", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        deadline_header.pack(anchor="w", pady=(5, 5))

        # Быстрые кнопки пресетов
        preset_hint = ctk.CTkLabel(
            main_frame, 
            text="Быстрый выбор срока:", 
            text_color="gray", 
            font=ctk.CTkFont(size=12)
        )
        preset_hint.pack(anchor="w", pady=(0, 5))

        presets_row1 = ctk.CTkFrame(main_frame, fg_color="transparent")
        presets_row1.pack(fill="x", pady=(0, 5))

        btn_today = ctk.CTkButton(
            presets_row1, text="⚡ Сегодня (23:59)", height=32,
            fg_color="#3B82F6", hover_color="#2563EB",
            command=lambda: self.apply_preset(days=0, end_of_day=True)
        )
        btn_today.pack(side="left", fill="x", expand=True, padx=(0, 4))

        btn_1d = ctk.CTkButton(
            presets_row1, text="⏳ 1 день", height=32,
            fg_color="#3B82F6", hover_color="#2563EB",
            command=lambda: self.apply_preset(days=1, end_of_day=True)
        )
        btn_1d.pack(side="left", fill="x", expand=True, padx=4)

        btn_3d = ctk.CTkButton(
            presets_row1, text="📅 3 дня", height=32,
            fg_color="#3B82F6", hover_color="#2563EB",
            command=lambda: self.apply_preset(days=3, end_of_day=True)
        )
        btn_3d.pack(side="left", fill="x", expand=True, padx=(4, 0))

        presets_row2 = ctk.CTkFrame(main_frame, fg_color="transparent")
        presets_row2.pack(fill="x", pady=(0, 10))

        btn_1w = ctk.CTkButton(
            presets_row2, text="🗓️ 1 неделя", height=32,
            fg_color="#4F46E5", hover_color="#4338CA",
            command=lambda: self.apply_preset(days=7, end_of_day=True)
        )
        btn_1w.pack(side="left", fill="x", expand=True, padx=(0, 4))

        btn_2w = ctk.CTkButton(
            presets_row2, text="🗓️ 2 недели", height=32,
            fg_color="#4F46E5", hover_color="#4338CA",
            command=lambda: self.apply_preset(days=14, end_of_day=True)
        )
        btn_2w.pack(side="left", fill="x", expand=True, padx=4)

        btn_1m = ctk.CTkButton(
            presets_row2, text="🌙 1 месяц", height=32,
            fg_color="#4F46E5", hover_color="#4338CA",
            command=lambda: self.apply_preset(days=30, end_of_day=True)
        )
        btn_1m.pack(side="left", fill="x", expand=True, padx=(4, 0))

        # Точные поля ввода даты и времени
        date_frame = ctk.CTkFrame(main_frame, fg_color=("gray90", "gray17"), corner_radius=8)
        date_frame.pack(fill="x", pady=(5, 10), padx=2, ipady=8)

        inputs_sub = ctk.CTkFrame(date_frame, fg_color="transparent")
        inputs_sub.pack(pady=4)

        # День
        ctk.CTkLabel(inputs_sub, text="День:").grid(row=0, column=0, padx=4, sticky="e")
        self.day_var = ctk.StringVar()
        self.day_menu = ctk.CTkComboBox(
            inputs_sub, values=[f"{d:02d}" for d in range(1, 32)],
            width=65, height=30, variable=self.day_var, command=self.on_datetime_change
        )
        self.day_menu.grid(row=0, column=1, padx=(0, 10))

        # Месяц
        ctk.CTkLabel(inputs_sub, text="Месяц:").grid(row=0, column=2, padx=4, sticky="e")
        self.month_var = ctk.StringVar()
        self.month_menu = ctk.CTkComboBox(
            inputs_sub, values=[f"{m:02d}" for m in range(1, 13)],
            width=65, height=30, variable=self.month_var, command=self.on_datetime_change
        )
        self.month_menu.grid(row=0, column=3, padx=(0, 10))

        # Год
        ctk.CTkLabel(inputs_sub, text="Год:").grid(row=0, column=4, padx=4, sticky="e")
        current_year = datetime.now().year
        self.year_var = ctk.StringVar()
        self.year_menu = ctk.CTkComboBox(
            inputs_sub, values=[str(y) for y in range(current_year, current_year + 6)],
            width=80, height=30, variable=self.year_var, command=self.on_datetime_change
        )
        self.year_menu.grid(row=0, column=5, padx=(0, 10))

        # Время
        ctk.CTkLabel(inputs_sub, text="Время:").grid(row=0, column=6, padx=4, sticky="e")
        self.time_var = ctk.StringVar()
        time_presets = [
            "09:00", "12:00", "15:00", "18:00", "20:00", "22:00", "23:59"
        ]
        self.time_menu = ctk.CTkComboBox(
            inputs_sub, values=time_presets,
            width=80, height=30, variable=self.time_var, command=self.on_datetime_change
        )
        self.time_menu.grid(row=0, column=7)

        # Лейбл предпросмотра дедлайна
        self.deadline_preview = ctk.CTkLabel(
            main_frame,
            text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#10B981"
        )
        self.deadline_preview.pack(fill="x", pady=(2, 10))

        # Сообщение об ошибке
        self.error_label = ctk.CTkLabel(
            main_frame,
            text="",
            text_color="#EF4444",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.error_label.pack(fill="x", pady=(0, 5))

        # Кнопки Сохранить / Отмена
        actions_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        actions_frame.pack(fill="x", pady=(10, 5))

        cancel_btn = ctk.CTkButton(
            actions_frame,
            text="Отмена",
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            height=38,
            command=self.destroy
        )
        cancel_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        save_btn = ctk.CTkButton(
            actions_frame,
            text="💾 Сохранить цель",
            fg_color="#10B981",
            hover_color="#059669",
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.save_goal
        )
        save_btn.pack(side="left", fill="x", expand=True, padx=(8, 0))

    def apply_preset(self, days: int, end_of_day: bool = True):
        """Устанавливает дедлайн на основе выбранного пресета."""
        target = datetime.now() + timedelta(days=days)
        if end_of_day:
            target = target.replace(hour=23, minute=59, second=0)
        self.current_deadline = target
        self.update_deadline_ui()

    def update_deadline_ui(self):
        """Синхронизирует виджеты с current_deadline."""
        self.day_var.set(f"{self.current_deadline.day:02d}")
        self.month_var.set(f"{self.current_deadline.month:02d}")
        self.year_var.set(str(self.current_deadline.year))
        self.time_var.set(f"{self.current_deadline.hour:02d}:{self.current_deadline.minute:02d}")
        self.update_preview_text()

    def on_datetime_change(self, *args):
        """Вызывается при ручном изменении выпадающих списков."""
        try:
            day = int(self.day_var.get())
            month = int(self.month_var.get())
            year = int(self.year_var.get())
            time_parts = self.time_var.get().split(":")
            hour = int(time_parts[0])
            minute = int(time_parts[1]) if len(time_parts) > 1 else 0
            
            self.current_deadline = datetime(year, month, day, hour, minute, 0)
            self.update_preview_text()
            self.error_label.configure(text="")
        except Exception:
            self.deadline_preview.configure(text="⚠️ Некорректная дата", text_color="#EF4444")

    def update_preview_text(self):
        now = datetime.now()
        diff = self.current_deadline - now
        total_seconds = diff.total_seconds()

        date_str = self.current_deadline.strftime("%d.%m.%Y в %H:%M")

        if total_seconds < 0:
            self.deadline_preview.configure(
                text=f"Срок: {date_str} (уже истёк!)",
                text_color="#EF4444"
            )
        else:
            days = int(total_seconds // 86400)
            hours = int((total_seconds % 86400) // 3600)
            mins = int((total_seconds % 3600) // 60)
            
            parts = []
            if days > 0:
                parts.append(f"{days} дн.")
            if hours > 0:
                parts.append(f"{hours} ч.")
            if mins > 0 or not parts:
                parts.append(f"{mins} мин.")
                
            left_str = " ".join(parts)
            self.deadline_preview.configure(
                text=f"🎯 Дедлайн: {date_str} (осталось: {left_str})",
                text_color="#10B981"
            )

    def save_goal(self):
        title = self.title_entry.get().strip()
        if not title:
            self.error_label.configure(text="Пожалуйста, укажите название цели!")
            self.title_entry.focus()
            return

        desc = self.desc_textbox.get("1.0", "end-1c").strip()
        category = self.cat_option.get().strip() or "Общее"

        self.on_save(
            title=title,
            description=desc,
            category=category,
            deadline=self.current_deadline,
            goal_id=self.goal_data["id"] if self.goal_data else None
        )
        self.destroy()
