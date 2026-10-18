"""
Модуль системных уведомлений Windows (Toast notifications) с использованием winotify.
"""

import sys
from typing import Optional

try:
    from winotify import Notification, audio
    WINOTIFY_AVAILABLE = True
except Exception:
    WINOTIFY_AVAILABLE = False


class Notifier:
    APP_ID = "Напоминатель Целей"

    @classmethod
    def send_notification(cls, title: str, message: str, sound_type: str = "default"):
        """Отправляет системное Windows уведомление."""
        if not WINOTIFY_AVAILABLE:
            print(f"[Уведомление] {title}: {message}")
            return

        try:
            toast = Notification(
                app_id=cls.APP_ID,
                title=title,
                msg=message,
                duration="short"
            )
            
            if sound_type == "reminder":
                toast.set_audio(audio.Reminder, loop=False)
            elif sound_type == "alert":
                toast.set_audio(audio.SMS, loop=False)
            else:
                toast.set_audio(audio.Default, loop=False)

            toast.show()
        except Exception as e:
            # Не падаем, если у пользователя выключены уведомления в Windows
            print(f"Ошибка отправки уведомления: {e}", file=sys.stderr)

    @classmethod
    def notify_expired(cls, goal_title: str):
        """Уведомление о провале цели по дедлайну."""
        cls.send_notification(
            title="⚠️ Срок цели истёк!",
            message=f"Цель «{goal_title}» не была закрыта вовремя и перемещена в раздел «Проваленные».",
            sound_type="alert"
        )

    @classmethod
    def notify_reminder(cls, goal_title: str, hours_left: int):
        """Уведомление о приближении дедлайна."""
        if hours_left <= 1:
            time_str = "менее часа"
        else:
            time_str = f"около {hours_left} ч."
            
        cls.send_notification(
            title="⏰ Скоро дедлайн по цели!",
            message=f"До окончания цели «{goal_title}» осталось {time_str}!",
            sound_type="reminder"
        )

    @classmethod
    def notify_completed(cls, goal_title: str):
        """Уведомление об успешном завершении цели."""
        cls.send_notification(
            title="🎉 Цель выполнена!",
            message=f"Поздравляем! Вы успешно достигли цели «{goal_title}».",
            sound_type="default"
        )
