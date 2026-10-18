"""
Точка входа в приложение «Напоминатель и Трекер Целей».
"""

import sys
import os

# Добавляем текущую директорию в sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import GoalTrackerApp


def main():
    try:
        if sys.platform.startswith("win"):
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            if hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")

        app = GoalTrackerApp()
        app.mainloop()
    except Exception as e:
        print(f"\n[Критическая ошибка запуска приложения]: {e}")
        import traceback
        traceback.print_exc()
        try:
            input("\nНажмите Enter, чтобы закрыть это окно...")
        except Exception:
            pass


if __name__ == "__main__":
    main()
