#!/usr/bin/env python
"""Django management entrypoint."""
import os
import sys


def main():
    # Windows console mặc định cp1252, không support tiếng Việt — reconfigure UTF-8
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except AttributeError:
            pass

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Không import được Django. Kiểm tra venv đã activate chưa và đã `pip install -r requirements.txt` chưa."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
