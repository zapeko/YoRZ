import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import os
import threading
import sys
import builtins
import re
import json
import urllib.request
import ctypes
import webbrowser
from PIL import Image, ImageDraw

from modules import paths

# Версия программы (обновляйте здесь при выпуске новой версии)
APP_VERSION = "2.1.2"

# Быстрая проверка при запуске (только копирование недостающих файлов)
paths.ensure_user_data_exists()

# Для совместимости с остальным кодом, но теперь с правильным разделением
current_dir = paths.APP_DIR
user_dir = paths.USER_DATA_DIR

os.chdir(current_dir)
if current_dir not in sys.path:
    sys.path.append(current_dir)

from modules import yorz
from modules import typographer
from modules import extraction
from modules import sorting
from modules import twin
from modules import yellow_dic_forming

DEFAULT_SETTINGS = {
    "theme": "Dark",
    "console_font_size": 20,
    "highlight_alpha": 20,
    "console_font_family": "Consolas",
    "console_font_style": "normal",
    "typo_zwnbsp": True,
    "typo_html_nbsp": True,
    "typo_nbsp": True,
    "typo_shy": True,
    "typo_spaces": True,
    "typo_letter_digit_spaces": True,
    "typo_punctuation": True,
    "typo_dashes": True,
    "typo_merge_lines": True,
    "typo_keep_leading_dashes": False,
    "typo_remove_all_empty": False,
    "typo_deyo": False
}

def load_settings():
    settings = DEFAULT_SETTINGS.copy()
    settings_file = os.path.join(user_dir, "yorz_settings.json")
    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                settings.update(loaded)
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")
    return settings

def save_settings(settings):
    settings_file = os.path.join(user_dir, "yorz_settings.json")
    if settings != DEFAULT_SETTINGS:
        try:
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")
    else:
        if os.path.exists(settings_file):
            try:
                os.remove(settings_file)
            except Exception:
                pass

SETTINGS = load_settings()

# Устанавливаем тему из настроек
appearance_mode = SETTINGS["theme"]
if appearance_mode == "Aquamarine":
    ctk.set_appearance_mode("Dark")
else:
    ctk.set_appearance_mode(appearance_mode)
ctk.set_default_color_theme("blue")

class StdoutRedirector:
    """Перенаправляет стандартный вывод (print) в текстовое поле GUI с поддержкой базовых ANSI-цветов"""
    def __init__(self, root_app):
        self.root_app = root_app
        self.ansi_escape = re.compile(r'(\x1B\[[0-9;]*m)')
        
    def write(self, string):
        target_tb = self.root_app.log_textboxes.get(self.root_app.running_tool)
        if not target_tb:
            target_tb = self.root_app.active_log_textbox
        if target_tb:
            target_tb.after(0, self._insert_colored_text, target_tb, string)

    def _insert_colored_text(self, target_tb, text):
        target_tb.configure(state="normal")
        parts = self.ansi_escape.split(text)
        current_tag = None
        
        for part in parts:
            if part.startswith('\x1B['):
                if part == '\x1B[0m':
                    current_tag = None
                elif part == '\x1B[33m':
                    current_tag = "color_33"
                elif part == '\x1B[36m':
                    current_tag = "color_36"
                elif part == '\x1B[32m':
                    current_tag = "color_32"
                elif part == '\x1B[31m':
                    current_tag = "color_31"
            else:
                if part:
                    if current_tag:
                        target_tb.insert("end", part, current_tag)
                    else:
                        target_tb.insert("end", part)
                        
        target_tb.configure(state="disabled")
        if target_tb != self.root_app.log_textboxes.get("guide"):
            target_tb.see("end")

    def flush(self):
        pass

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        # Используем цвет фона приложения как ключ прозрачности, чтобы убрать ореол
        is_dark = ctk.get_appearance_mode() == "Dark"
        app_bg_color = "#242424" if is_dark else "#ebebeb"
        
        if sys.platform == "win32":
            tw.attributes("-transparentcolor", app_bg_color)
            
        tw.configure(bg=app_bg_color)
        
        # Используем CTkFrame для закругленных углов и толстой рамки
        # Цвет рамки теперь совпадает с цветом полосы прокрутки/боковой панели
        frame = ctk.CTkFrame(tw, corner_radius=15, border_width=3, 
                            border_color=("gray86", "gray17"), 
                            fg_color=("gray95", "gray15"))
        frame.pack()
        
        label = ctk.CTkLabel(frame, text=self.text, justify='left',
                           font=("Segoe UI", 16, "bold"), wraplength=450)
        label.pack(padx=15, pady=10)

    def leave(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

TOOLS_CONFIG = {
    "guide": {
        "name": "Описание",
        "needs_file": False,
        "desc": """Добро пожаловать в Ёфикатор YoRZ!

Это программа для автоматизированного восстановления буквы «ё» в текстах (форматы: .txt, .fb2, .epub, .md).
Логика программы кардинально отличается от всех известных программ-ёфикаторов, то есть расставляет букву «ё» вместо «е» во всех словах, если этих слов нет в словарях. Построена на последовательной обработке текста с помощью набора специализированных словарей.

Чтобы добиться наилучшего результата, следуйте этим шагам:

\x1b[33mШаг 1: Подготовка текста (Инструмент: "Типограф")\x1b[0m
--------------------------------------------------
Тексты, скачанные из интернета, часто содержат ошибки форматирования: лишние пробелы, неразрывные пробелы вместо обычных, мягкие переносы, дефисы вместо тире. Типограф приводит текст к единому стандарту, что критически важно для корректного срабатывания регулярных выражений при ёфикации.

Результат: Создается файл `_fixed` (например, `book_fixed.txt`), который вы будете использовать на следующих этапах.

\x1b[33mШаг 2: Извлечение слов (Инструмент: "Извлечение слов")\x1b[0m
--------------------------------------------------------
Программа просматривает ваш текст и выписывает все слова, содержащие буквы "е" или "ё" и соответствуют определённым параметрам.

Результат: Файл `_extraction.txt` со словами, которых ещё нет в базе yellow_base.txt. Проверьте слова и расставьте букву "ё", где требуется. Слова помеченные (!) требуют особого внимания, так как в базе есть аналоги этих слов с буквой "ё" вместо "е" или с буквой "е" вместо "ё". В таких случаях, если слово неверное в таком написании, то его удалить. Если верное и имеет другой смысл, то оставить. После проверки скопировать все слова и добавить в базу `yellow_base.txt`.

Для удобства, вместе с файлом `_extraction.txt` создаётся файл `for_blacklist.txt`, который содержит слова помеченные (!) в `_extraction.txt`. После проверки добавьте эти слова в `blacklist.txt`, и запустите инструмент "Извлечение слов" ещё раз.

\x1b[33mШаг 3: Сортировка (Инструмент: "Сортировка базы")\x1b[0m
---------------------------------------------------
Инструмент сортирует слова в файле `yellow_base.txt` по алфавиту и удаляет любые дубликаты. Это ускоряет работу программы и избавляет базу от мусора, который мог появиться на предыдущем шаге при ручном добавлении слов.

Результат: Файл `yellow_base.txt` будет перезаписан отсортированными данными.

Этим же инструментом можно отсортировать слова в `blacklist.txt`.

\x1b[33mШаг 4: Поиск омографов (Инструмент: "Поиск омографов")\x1b[0m
--------------------------------------------------------
Омографы — это слова, которые пишутся одинаково без «ё», но имеют разный смысл (например, "все" и "всё", "мел" и "мёл").
Программа сканирует `yellow_base.txt` и ищет такие пары слов.

Результат: Новые пары будут автоматически добавлены в словарь `orange.dic` под комментарием "Добавлено автоматически".

\x1b[33mШаг 5: Сборка словаря (Инструмент: "Сборка словаря")\x1b[0m
------------------------------------------------------
Программа не читает базу слов напрямую во время ёфикации, ей нужен готовый, оптимизированный словарь.
Инструмент собирает финальный рабочий словарь `yellow.dic`, объединяя неизменяемые корни (`yellow_root.txt`), вашу пополняемую базу (`yellow_base.txt`) и дополнительные слова (`yellow_add.txt`).

Результат: Обновляется файл `yellow.dic`. Он содержит готовые регулярные выражения и оптимизирован для быстрой работы.

\x1b[33mШаг 6: Ёфикация текста (Инструмент: "Ёфикация текста")\x1b[0m
--------------------------------------------------------
Финальный этап. Непосредственно сама расстановка буквы «ё» в вашем тексте.
Программа применяет все словари (синий, зелёный, оранжевый и жёлтый) к подготовленному тексту. Для оранжевого словаря программа предложит вам выбрать правильный вариант в консоли.

Результат:
1. Файл с суффиксом `_yo.html`. Вы можете открыть его в браузере, чтобы визуально (по цветовой подсветке) проверить, какие замены и по каким словарям были сделаны.
2. Чистый файл с суффиксом `_yo` в формате, соответствующем формату входного файла (.txt, .md, .fb2 или .epub).

Вы можете приостановить ёфикацию большого текста нажав на "Остановить". При следующем запуске программа предложит продолжить или начать сначала."""
    },
    "typographer": {
        "name": "Типограф (Подготовка)",
        "needs_file": True,
        "desc": "Подготавливает текст перед ёфикацией: исправляет пробелы, тире, неразрывные пробелы и пунктуацию.\n\nВход: Выбранный файл (.txt, .fb2, .epub, .md)\nРезультат: Файл с суффиксом _fixed. Выберите этот файл на слеующем шаге (извлечение слов) и для последующей ёфикации."
    },
    "extraction": {
        "name": "Извлечение слов",
        "needs_file": True,
        "desc": "Извлекает неизвестные слова из текста для пополнения базы словарей.\n\nВход: Выбранный файл (.txt, .md, .fb2 или .epub)\nРезультат: Файл с суффиксом _extraction.txt.\n\nВНИМАНИЕ: Требуется ручная проверка файла! Расставьте букву «ё» там, где это необходимо, и добавьте слова в базу yellow_base.txt."
    },
    "sorting": {
        "name": "Сортировка базы",
        "needs_file": True,
        "desc": "Сортирует слова по алфавиту и удаляет дубликаты в базе словаря.\n\nВход: Выбранный файл (yellow_base.txt или blacklist.txt)\nРезультат: Выбранный файл автоматически перезаписывается отсортированными данными."
    },
    "twin": {
        "name": "Поиск омографов",
        "needs_file": False,
        "desc": "Ищет пары слов-омографов (слова, которые пишутся одинаково без «ё», но имеют разный смысл, например: все/всё).\n\nВход: Автоматически сканирует yellow_base.txt (выбор файла не требуется).\nРезультат: Автоматически дописывает новые пары в словарь омографов orange.dic под заголовком # --- Добавлено автоматически ---."
    },
    "yellow_dic": {
        "name": "Сборка словаря",
        "needs_file": False,
        "desc": "Собирает финальный рабочий словарь yellow.dic из корней (yellow_root.txt), базы (yellow_base.txt) и дополнений (yellow_add.txt).\n\nВход: Файлы yellow_root.txt, yellow_base.txt, yellow_add.txt (выбор файла не требуется).\nРезультат: Обновлённый файл yellow.dic, который сразу готов к использованию при ёфикации."
    },
    "yorz": {
        "name": "Ёфикация текста",
        "needs_file": True,
        "desc": "Основной движок ёфикации. Применяет правила из всех словарей (синего, зелёного, оранжевого и жёлтого) к выбранному тексту.\n\nВход: Выбранный файл (.txt, .md, .fb2 или .epub)\n\nРезультат:\n1. Файл с суффиксом `_yo.html`. Вы можете открыть его в браузере, чтобы визуально (по цветовой подсветке) проверить, какие замены и по каким словарям были сделаны.\n2. Чистый файл с суффиксом `_yo` в формате, соответствующем формату входного файла.\n\nВы можете приостановить ёфикацию большого текста нажав на `Остановить`. При следующем запуске программа предложит продолжить или начать сначала."
    },
}

def create_arrow_image(direction="left", size=(16, 16), color="white"):
    img = Image.new("RGBA", size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    w, h = size
    if direction == "left":
        points = [(w, 0), (w, h), (0, h//2)]
    else:
        points = [(0, 0), (0, h), (w, h//2)]
    draw.polygon(points, fill=color)
    return img

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YoRZ - Ёфикатор")
        self.geometry("1100x750")
        self.minsize(900, 600)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, minsize=280, weight=0)
        self.grid_columnconfigure(1, weight=1)

        self.base_font_size = 18
        self.console_font_size = int(SETTINGS.get("console_font_size", 20))
        self.console_font_family = SETTINGS.get("console_font_family", "Consolas")
        self.console_font_style = SETTINGS.get("console_font_style", "normal")

        # Настраиваем стиль шрифта консоли
        weight = "bold" if self.console_font_style == "bold" else "normal"
        slant = "italic" if self.console_font_style == "italic" else "roman"

        self.main_font = ctk.CTkFont(family="Segoe UI", size=self.base_font_size)
        self.bold_font = ctk.CTkFont(family="Segoe UI", size=self.base_font_size, weight="bold")
        self.header_font = ctk.CTkFont(family="Segoe UI", size=30, weight="bold")
        self.logo_font = ctk.CTkFont(family="Segoe UI", size=32, weight="bold")
        self.console_font = ctk.CTkFont(family=self.console_font_family, size=self.console_font_size, weight=weight, slant=slant)

        # --- Настройка иконки окна ---
        # Определяем путь к иконке для работы как в .py, так и в .exe (через sys._MEIPASS или Nuitka)
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            base_icon_path = sys._MEIPASS
        elif "__compiled__" in globals():
            base_icon_path = os.path.dirname(os.path.abspath(__file__))
        else:
            base_icon_path = os.path.abspath(".")
        
        icon_path = os.path.join(base_icon_path, "app.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        # --- Боковая панель ---
        self.sidebar_frame = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(8, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text=f"YoRZ v{APP_VERSION}", font=self.logo_font)
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 40))

        self.sidebar_btns = {}
        for i, (tool_id, config) in enumerate(TOOLS_CONFIG.items()):
            btn = ctk.CTkButton(
                self.sidebar_frame, 
                text=config["name"], 
                anchor="w", 
                font=self.bold_font, 
                height=40,
                fg_color="transparent", 
                text_color=("gray10", "gray90"), 
                hover_color=("gray70", "gray30"),
                command=lambda tid=tool_id: self.select_tool(tid)
            )
            # Добавляем отступ после "Описание", чтобы визуально отделить его
            pady = (5, 25) if tool_id == "guide" else 5
            btn.grid(row=i+1, column=0, padx=20, pady=pady, sticky="ew")
            self.sidebar_btns[tool_id] = btn

        # Словари
        self.btn_open_dict = ctk.CTkButton(
            self.sidebar_frame,
            text="Словари...",
            anchor="w",
            font=self.bold_font,
            height=40,
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            command=self.open_dictionaries_folder
        )
        self.btn_open_dict.grid(row=10, column=0, padx=20, pady=(25, 5), sticky="ew")

        # Настройки
        self.btn_tab_settings = ctk.CTkButton(
            self.sidebar_frame, 
            text="Настройки", 
            anchor="w", 
            font=self.bold_font, 
            height=40,
            fg_color="transparent", 
            text_color=("gray10", "gray90"), 
            hover_color=("gray70", "gray30"), 
            command=self.select_settings
        )
        self.btn_tab_settings.grid(row=11, column=0, padx=20, pady=5, sticky="ew")

        # GitHub
        self.btn_tab_github = ctk.CTkButton(
            self.sidebar_frame,
            text="GitHub",
            anchor="w",
            font=self.bold_font,
            height=40,
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            command=lambda: webbrowser.open("https://github.com/zapeko/YoRZ")
        )
        self.btn_tab_github.grid(row=12, column=0, padx=20, pady=(5, 20), sticky="ew")

        # --- Универсальная рабочая область ---
        self.tool_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        self.tool_frame.grid_rowconfigure(3, weight=1) 
        self.tool_frame.grid_columnconfigure(1, weight=1) 

        self.header_label = ctk.CTkLabel(self.tool_frame, text="Заголовок инструмента", font=self.header_font, height=40)
        self.header_label.grid(row=0, column=0, columnspan=2, padx=0, pady=(0, 20), sticky="w")

        # Блок выбора файла
        self.file_picker_frame = ctk.CTkFrame(self.tool_frame, fg_color="transparent", height=40)
        self.file_picker_frame.grid_propagate(False)
        self.file_picker_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.file_picker_frame.grid_columnconfigure(1, weight=1)
        
        self.file_path_var = ctk.StringVar(value="Файл не выбран")
        self.btn_select_file = ctk.CTkButton(self.file_picker_frame, text="Выбрать файл...", font=self.bold_font, command=self.select_file, height=35)
        self.btn_select_file.grid(row=0, column=0, padx=(0, 20), sticky="w")
        
        self.lbl_file_path = ctk.CTkLabel(self.file_picker_frame, textvariable=self.file_path_var, font=self.main_font, text_color="gray50", height=35)
        self.lbl_file_path.grid(row=0, column=1, padx=0, sticky="w")

        # Панель кнопок управления
        self.action_frame = ctk.CTkFrame(self.tool_frame, fg_color="transparent")
        self.action_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 20))
        # Запустить занимает 4/5, Остановить - 1/5
        self.action_frame.grid_columnconfigure(0, weight=5)
        self.action_frame.grid_columnconfigure(1, weight=1)

        self.btn_start = ctk.CTkButton(self.action_frame, text="Запустить", font=self.bold_font, height=45, fg_color="#1f538d", hover_color="#14375d", command=self.start_processing)
        self.btn_start.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.btn_stop = ctk.CTkButton(self.action_frame, text="Остановить", font=self.bold_font, height=45, fg_color="#8d1f1f", hover_color="#5d1414", state="disabled", command=self.stop_processing)
        self.btn_stop.grid(row=0, column=1, padx=(5, 0), sticky="ew")

        # Консоль
        sidebar_bg = self.sidebar_frame.cget("fg_color")
        if isinstance(sidebar_bg, (list, tuple)):
            light_sidebar = sidebar_bg[0]
            dark_sidebar = sidebar_bg[1]
        else:
            light_sidebar = dark_sidebar = sidebar_bg
            
        if light_sidebar == "transparent":
            light_sidebar = "gray86"
        if dark_sidebar == "transparent":
            dark_sidebar = "gray17"
            
        sidebar_color = (light_sidebar, dark_sidebar)

        self.log_textboxes = {}
        for tool_id in TOOLS_CONFIG:
            tb = ctk.CTkTextbox(
                self.tool_frame, font=self.console_font, state="disabled", wrap="word", fg_color="transparent",
                scrollbar_button_color=sidebar_color,
                scrollbar_button_hover_color=sidebar_color
            )
            tb.bind("<Control-c>", self.copy_selected_text)
            tb.bind("<Control-C>", self.copy_selected_text)
            tb.bind("<Button-3>", self.show_context_menu)
            tb.bind("<Control-MouseWheel>", self.zoom_console_font)
            tb.bind("<Control-Button-4>", self.zoom_console_font)
            tb.bind("<Control-Button-5>", self.zoom_console_font)
            self.log_textboxes[tool_id] = tb

        self.update_text_tags()

        self.active_log_textbox = None
        self.running_tool = None

        # Панель омографов
        self.choice_frame = ctk.CTkFrame(self.tool_frame, fg_color="transparent")
        self.choice_frame.grid_remove() # Скрываем по умолчанию

        for i in range(5):
            self.choice_frame.grid_columnconfigure(i, weight=1)

        self.btn_choice_1 = ctk.CTkButton(self.choice_frame, text="1 (Оригинал)", font=self.bold_font, height=40, command=lambda: self.submit_choice('1'))
        self.btn_choice_2 = ctk.CTkButton(self.choice_frame, text="2 (Ё-вариант)", font=self.bold_font, height=40, command=lambda: self.submit_choice('2'))
        self.btn_choice_3 = ctk.CTkButton(self.choice_frame, text="3 (Ориг. везде)", font=self.bold_font, height=40, command=lambda: self.submit_choice('3'))
        self.btn_choice_4 = ctk.CTkButton(self.choice_frame, text="4 (Ё-вар. везде)", font=self.bold_font, height=40, command=lambda: self.submit_choice('4'))
        self.btn_choice_5 = ctk.CTkButton(self.choice_frame, text="Пропустить (Enter)", font=self.bold_font, height=40, fg_color="gray", hover_color="darkgray", command=lambda: self.submit_choice(''))
        self.choice_buttons = [self.btn_choice_1, self.btn_choice_2, self.btn_choice_3, self.btn_choice_4, self.btn_choice_5]

        # Прогресс бар
        self.progress_frame = ctk.CTkFrame(self.tool_frame, fg_color="transparent")
        self.progress_frame.grid_columnconfigure(0, weight=1)
        self.progress_frame.grid_remove() # Скрываем по умолчанию
        
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            progress_color=self.btn_choice_1.cget("fg_color"),
            height=10,
            fg_color=sidebar_color
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew")
        self.progress_bar.set(0)

        # --- Вкладка: Настройки ---
        self.settings_frame = ctk.CTkScrollableFrame(
            self, corner_radius=10, fg_color="transparent",
            scrollbar_button_color=sidebar_color,
            scrollbar_button_hover_color=sidebar_color
        )
        ctk.CTkLabel(self.settings_frame, text="Настройки", font=self.header_font).pack(anchor="w", pady=(0, 30))
        
        # Настройки Типографа
        typo_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        typo_frame.pack(anchor="w", pady=(0, 20), fill="x")
        ctk.CTkLabel(typo_frame, text="Настройки Типографа:", font=self.bold_font).pack(anchor="w", pady=(0, 10))

        grid_frame = ctk.CTkFrame(typo_frame, fg_color="transparent")
        grid_frame.pack(anchor="w", padx=10)

        typo_settings_map = [
            ("typo_zwnbsp", "Удалять ZWNBSP (\\ufeff)", "Удаляет невидимый символ нулевой ширины, который часто возникает при копировании текста из интернета и разбивает слова на части.\nПример: Слово[ZWNBSP]слово ➔ Слово слово"),
            ("typo_html_nbsp", "Заменять HTML-пробелы (&nbsp;)", "Преобразует HTML-сущности неразрывных пробелов в обычные текстовые пробелы, чтобы ёфикатор корректно искал слова.\nПример: Он&nbsp;пошёл домой ➔ Он пошёл домой"),
            ("typo_nbsp", "Заменять неразрывные пробелы", "Заменяет юникодные символы неразрывного (\\u00a0) и идеографического пробела (\\u3000) на обычные.\nПример: 20[NBSP]кг ➔ 20 кг"),
            ("typo_shy", "Удалять мягкие переносы (\\xad)", "Полностью удаляет невидимые символы переноса, которые указывают читалке, где разорвать слово.\nПример: пе-ре-нос (где дефисы невидимые) ➔ перенос"),
            ("typo_spaces", "Удалять лишние пробелы", "Убирает множественные пробелы подряд, некорректные пробелы перед запятыми/точками и в начале строк.\nПример: Привет   всем , как дела ? ➔ Привет всем, как дела?"),
            ("typo_letter_digit_spaces", "Разделять буквы и цифры пробелом", "Вставляет пробел между буквами и цифрами согласно правилам типографики. Снимите галочку, чтобы сохранить слитное написание форматов.\nПример: FB2 ➔ FB 2 | 100МГц ➔ 100 МГц"),
            ("typo_punctuation", "Исправлять пунктуацию", "Интеллектуально нормализует знаки препинания, убирая лишние точки, вопросы и восклицания.\nПример: Что!!!!??? ➔ Что?! | Привет.. ➔ Привет..."),
            ("typo_dashes", "Заменять дефисы на тире", "Умная замена обычных дефисов (-) на длинное или среднее тире в диалогах, между словами и в цифрах.\nПример: - Привет. ➔ — Привет. | 1990-2000 ➔ 1990–2000"),
            ("typo_merge_lines", "Склеивать разорванные абзацы", "Объединяет строки, если предыдущая не заканчивается точкой, а следующая начинается с маленькой буквы.\nВНИМАНИЕ: Обязательно отключайте для стихов!"),
            ("typo_keep_leading_dashes", "Сохранять дефисы в начале строк", "Предотвращает замену дефисов на тире в начале строк. Полезно, если в тексте много маркированных списков.\nПример: - Первый пункт ➔ - Первый пункт"),
            ("typo_remove_all_empty", "Удалять абсолютно все пустые строки", "Сжимает текст в монолит. По умолчанию Типограф оставляет одну пустую строку между абзацами для читаемости; включение опции уберёт и её."),
            ("typo_deyo", "Деёфикация текста", "Заменяет все буквы Ё/ё на Е/е. Полезно, если исходный текст ёфицирован неправильно или частично, и вы хотите начать процесс заново.\nПример: Ещё ёжик ➔ Еще ежик")
            ]

        self.typo_vars = {}
        self.typo_checkboxes = [] # Список для смены тем
        self.tooltips = [] # Сохраняем ссылки, чтобы сборщик мусора не удалил
        for i, (key, text, tooltip_text) in enumerate(typo_settings_map):
            var = ctk.BooleanVar(value=SETTINGS.get(key, DEFAULT_SETTINGS[key]))
            self.typo_vars[key] = var
            cb = ctk.CTkCheckBox(grid_frame, text=text, variable=var, font=self.main_font, cursor="hand2", command=self.save_typo_settings)
            cb.grid(row=i//2, column=i%2, padx=(0, 40), pady=10, sticky="w")
            self.typo_checkboxes.append(cb)
            self.tooltips.append(ToolTip(cb, tooltip_text))

        # Выбор темы
        theme_settings_row = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        theme_settings_row.pack(anchor="w", pady=10)
        
        ctk.CTkLabel(theme_settings_row, text="Тема:", font=self.bold_font).pack(side="left", padx=(0, 20))
        
        self.theme_map = {"Тёмная": "Dark", "Светлая": "Light", "Аквамарин": "Aquamarine"}
        self.reverse_theme_map = {"Dark": "Тёмная", "Light": "Светлая", "Aquamarine": "Аквамарин"}
        
        current_theme_ru = self.reverse_theme_map.get(SETTINGS.get("theme", "Dark"), "Тёмная")
        
        self.theme_optionmenu = ctk.CTkOptionMenu(
            theme_settings_row,
            values=["Тёмная", "Светлая", "Аквамарин"],
            font=self.bold_font,
            dropdown_font=self.bold_font,
            command=self.change_theme
        )
        self.theme_optionmenu.set(current_theme_ru)
        self.theme_optionmenu.pack(side="left")

        # Прозрачность фона выделения
        self.alpha_frame = ctk.CTkFrame(theme_settings_row, fg_color="transparent")
        
        ctk.CTkLabel(self.alpha_frame, text="Прозрачность фона:", font=self.bold_font).pack(side="left", padx=(40, 10))
        
        # Кнопки со стрелками
        arr_left_light = create_arrow_image("left", color="#1F6AA5", size=(16, 16))
        arr_left_dark = create_arrow_image("left", color="#3B8ED0", size=(16, 16))
        arr_right_light = create_arrow_image("right", color="#1F6AA5", size=(16, 16))
        arr_right_dark = create_arrow_image("right", color="#3B8ED0", size=(16, 16))

        self.img_left = ctk.CTkImage(light_image=arr_left_light, dark_image=arr_left_dark, size=(16, 16))
        self.img_right = ctk.CTkImage(light_image=arr_right_light, dark_image=arr_right_dark, size=(16, 16))

        self.btn_alpha_dec = ctk.CTkLabel(self.alpha_frame, text="", image=self.img_left, cursor="hand2")
        self.btn_alpha_dec.bind("<ButtonPress-1>", lambda e: self._start_alpha_change('dec'))
        self.btn_alpha_dec.bind("<ButtonRelease-1>", lambda e: self._stop_alpha_change())
        self.btn_alpha_dec.bind("<Leave>", lambda e: self._stop_alpha_change())
        self.btn_alpha_dec.pack(side="left", padx=5)
        
        self.lbl_alpha = ctk.CTkLabel(self.alpha_frame, text=str(SETTINGS.get("highlight_alpha", 50)), font=self.bold_font, width=40)
        self.lbl_alpha.pack(side="left")
        
        self.btn_alpha_inc = ctk.CTkLabel(self.alpha_frame, text="", image=self.img_right, cursor="hand2")
        self.btn_alpha_inc.bind("<ButtonPress-1>", lambda e: self._start_alpha_change('inc'))
        self.btn_alpha_inc.bind("<ButtonRelease-1>", lambda e: self._stop_alpha_change())
        self.btn_alpha_inc.bind("<Leave>", lambda e: self._stop_alpha_change())
        self.btn_alpha_inc.pack(side="left", padx=5)

        if current_theme_ru == "Светлая":
            self.alpha_frame.pack(side="left")

        # Настройка шрифта
        self.font_slider_var = ctk.DoubleVar(value=self.console_font_size)
        
        font_settings_row = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        font_settings_row.pack(anchor="w", pady=10)
        
        ctk.CTkLabel(font_settings_row, text="Размер шрифта консоли:", font=self.bold_font).pack(side="left", padx=(0, 20))
        self.font_slider = ctk.CTkSlider(font_settings_row, width=300, from_=10, to=36, number_of_steps=26, variable=self.font_slider_var, command=self.update_console_font_size)
        self.font_slider.pack(side="left", padx=20)
        
        def on_slider_scroll(event):
            step = 1 if event.delta > 0 else -1
            current = self.font_slider_var.get()
            new_val = current + step
            if 10 <= new_val <= 36:
                self.font_slider_var.set(new_val)
                self.update_console_font_size(new_val)
                
        self.font_slider.bind("<MouseWheel>", on_slider_scroll)
        self.font_slider.bind("<Enter>", lambda e: self.font_slider.configure(cursor="hand2"))
        self.font_slider.bind("<Leave>", lambda e: self.font_slider.configure(cursor=""))

        self.lbl_font_size = ctk.CTkLabel(font_settings_row, text=str(int(self.console_font_size)), font=self.bold_font)
        self.lbl_font_size.pack(side="left")

        font_family_row = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        font_family_row.pack(anchor="w", pady=10)

        ctk.CTkLabel(font_family_row, text="Шрифт консоли:", font=self.bold_font).pack(side="left", padx=(0, 20))
        fonts = ["Consolas", "Courier New", "Lucida Console", "Cascadia Code", "Fira Code", "Arial", "Times New Roman"]
        self.font_family_dropdown = ctk.CTkOptionMenu(
            font_family_row,
            values=fonts,
            command=self.update_console_font_family,
            font=self.bold_font,
            dropdown_font=self.bold_font,
        )
        self.font_family_dropdown.set(self.console_font_family)
        self.font_family_dropdown.pack(side="left", padx=20)

        font_style_row = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        font_style_row.pack(anchor="w", pady=10)

        ctk.CTkLabel(font_style_row, text="Стиль шрифта консоли:", font=self.bold_font).pack(side="left", padx=(0, 20))
        styles_map = {"normal": "Обычный", "bold": "Жирный", "italic": "Курсив"}
        styles_reverse_map = {v: k for k, v in styles_map.items()}
        self.font_style_dropdown = ctk.CTkOptionMenu(
            font_style_row,
            values=list(styles_map.values()),
            command=lambda v: self.update_console_font_style(styles_reverse_map[v]),
            font=self.bold_font,
            dropdown_font=self.bold_font,
        )
        self.font_style_dropdown.set(styles_map.get(self.console_font_style, "Обычный"))
        self.font_style_dropdown.pack(side="left", padx=20)

        # --- Обновление программы ---
        update_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        update_frame.pack(anchor="w", pady=20)
        
        self.btn_check_update = ctk.CTkButton(update_frame, text="Проверить обновление", font=self.bold_font, height=40, command=self.check_update)
        self.btn_check_update.pack(side="left", padx=(0, 10))
        
        self.btn_download_update = ctk.CTkButton(update_frame, text="Скачать", font=self.bold_font, height=40, state="disabled", command=self.download_update)
        self.btn_download_update.pack(side="left", padx=(0, 10))

        self.btn_sync_dicts = ctk.CTkButton(update_frame, text="Синхронизировать словари", font=self.bold_font, height=40, command=self.sync_dictionaries)
        self.btn_sync_dicts.pack(side="left")

        self.lbl_update_status = ctk.CTkLabel(self.settings_frame, text="", font=self.bold_font, text_color="gray")

        self.lbl_update_status.pack(anchor="w", pady=(0, 10))

        # Перенаправление stdout
        sys.stdout = StdoutRedirector(self)
        self.original_input = builtins.input

        # Состояние ожидания
        self.is_waiting_for_input = False
        self.bind_keyboard_shortcuts()

        # Хранилище путей для каждого инструмента для сохранения состояния между переключениями
        self.tool_paths = {
            "typographer": "Файл не выбран",
            "extraction": "Файл не выбран",
            "sorting": paths.get_path("dictionaries/yellow_base.txt"),
            "yorz": "Файл не выбран"
        }

        # По умолчанию выбираем первый инструмент
        self.current_tab = None
        self.current_tool = "guide"
        self.select_tool("guide")
        self.apply_theme_to_all()

    def get_theme_colors(self):
        theme = SETTINGS.get("theme", "Dark")
        if theme == "Aquamarine":
            return {
                "primary": "#48D1CC",
                "hover": "#3CB371",
                "text": "black",
                "sidebar_active": "#48D1CC",
                "sidebar_active_text": "black",
                "button_color": "#20B2AA",
                "button_hover": "#008B8B",
                "checkmark": "black",
                "progress_color": "#48D1CC",
                "disabled_text": "gray30"
            }
        else:
            # Стандартный синий цвет CustomTkinter для тёмной/светлой тем
            # Для тёмной темы ctk использует #1f538d
            return {
                "primary": "#1f538d",
                "hover": "#14375d",
                "text": "white",
                "sidebar_active": "#1f538d",
                "sidebar_active_text": "white",
                "button_color": "#14375d",
                "button_hover": "#0e2642",
                "checkmark": "white",
                "progress_color": "#1f538d",
                "disabled_text": "gray60"
            }

    def apply_theme_to_all(self):
        colors = self.get_theme_colors()
        
        # Обновляем основные кнопки
        self.btn_start.configure(fg_color=colors["primary"], hover_color=colors["hover"], text_color=colors["text"])
        self.btn_select_file.configure(fg_color=colors["primary"], hover_color=colors["hover"], text_color=colors["text"], text_color_disabled=colors["disabled_text"])
        self.btn_check_update.configure(fg_color=colors["primary"], hover_color=colors["hover"], text_color=colors["text"])
        self.btn_sync_dicts.configure(fg_color=colors["primary"], hover_color=colors["hover"], text_color=colors["text"])
        
        # Обновляем кнопку Скачать всегда, чтобы цвет применялся даже если она отключена
        self.btn_download_update.configure(fg_color=colors["primary"], hover_color=colors["hover"], text_color=colors["text"], text_color_disabled=colors["disabled_text"])
        
        # Обновляем выпадающие списки (OptionMenus)
        if hasattr(self, "theme_optionmenu"):
            self.theme_optionmenu.configure(fg_color=colors["primary"], button_color=colors["button_color"], button_hover_color=colors["button_hover"], text_color=colors["text"])
        if hasattr(self, "font_family_dropdown"):
            self.font_family_dropdown.configure(fg_color=colors["primary"], button_color=colors["button_color"], button_hover_color=colors["button_hover"], text_color=colors["text"])
        if hasattr(self, "font_style_dropdown"):
            self.font_style_dropdown.configure(fg_color=colors["primary"], button_color=colors["button_color"], button_hover_color=colors["button_hover"], text_color=colors["text"])

        # Обновляем кружочек ползунка
        if hasattr(self, "font_slider"):
            self.font_slider.configure(button_color=colors["primary"], button_hover_color=colors["hover"], progress_color=colors["primary"])

        # Кнопки выбора омографов
        for btn in self.choice_buttons:
            if btn != self.btn_choice_5: # Кнопка 5 серая
                btn.configure(fg_color=colors["primary"], hover_color=colors["hover"], text_color=colors["text"])

        # Прогресс бар
        if hasattr(self, "progress_bar"):
            self.progress_bar.configure(progress_color=colors["progress_color"])

        # Чекбоксы типографа
        for cb in self.typo_checkboxes:
            cb.configure(fg_color=colors["primary"], hover_color=colors["hover"], checkmark_color=colors["checkmark"])

        # Обновляем иконки стрелок
        self.update_arrow_icons()
        
        # Обновляем активную вкладку в сайдбаре
        if self.current_tab == "settings":
            self.select_settings()
        elif self.current_tab == "tool":
            self.select_tool(self.current_tool)

    def update_arrow_icons(self):
        theme = SETTINGS.get("theme", "Dark")
        if theme == "Aquamarine":
            # В аквамариновой теме используем один цвет для обоих режимов (т.к. она всегда Dark)
            color_light = "#48D1CC"
            color_dark = "#48D1CC"
        else:
            color_light = "#1F6AA5"
            color_dark = "#3B8ED0"
            
        arr_left_light = create_arrow_image("left", color=color_light, size=(16, 16))
        arr_left_dark = create_arrow_image("left", color=color_dark, size=(16, 16))
        arr_right_light = create_arrow_image("right", color=color_light, size=(16, 16))
        arr_right_dark = create_arrow_image("right", color=color_dark, size=(16, 16))
        
        self.img_left.configure(light_image=arr_left_light, dark_image=arr_left_dark)
        self.img_right.configure(light_image=arr_right_light, dark_image=arr_right_dark)

    def open_dictionaries_folder(self):
        dict_path = os.path.join(user_dir, "dictionaries")
        if not os.path.exists(dict_path):
            os.makedirs(dict_path)
        try:
            os.startfile(dict_path)
        except Exception as e:
            self.write_log(f"Не удалось открыть папку: {e}")

    def reset_sidebar_colors(self):
        for btn in self.sidebar_btns.values():
            btn.configure(fg_color="transparent", text_color=("gray10", "gray90"))
        self.btn_tab_settings.configure(fg_color="transparent", text_color=("gray10", "gray90"))

    def select_tool(self, tool_id):
        if getattr(self, "running_tool", None) is not None:
            if tool_id != self.running_tool:
                return

        # Сохраняем текущий путь для текущего инструмента перед переключением
        if self.current_tool in self.tool_paths and tool_id != self.current_tool:
            self.tool_paths[self.current_tool] = self.file_path_var.get()

        colors = self.get_theme_colors()
        self.reset_sidebar_colors()
        self.sidebar_btns[tool_id].configure(fg_color=colors["sidebar_active"], text_color=colors["sidebar_active_text"])

        if self.current_tab != "tool":
            self.settings_frame.grid_forget()
            self.tool_frame.grid(row=0, column=1, padx=30, pady=30, sticky="nsew")
            self.current_tab = "tool"

        self.current_tool = tool_id

        config = TOOLS_CONFIG[tool_id]
        self.header_label.configure(text=config["name"])
        
        if self.active_log_textbox:
            self.active_log_textbox.grid_forget()
            
        self.active_log_textbox = self.log_textboxes[tool_id]
        self.active_log_textbox.grid(row=3, column=0, columnspan=2, padx=0, pady=0, sticky="nsew")

        # Управление кнопками Запустить/Остановить
        if tool_id == "yorz":
            self.btn_stop.grid(row=0, column=1, padx=(5, 0), sticky="ew")
            self.action_frame.grid_columnconfigure(0, weight=5)
            self.action_frame.grid_columnconfigure(1, weight=1)
        else:
            self.btn_stop.grid_remove()
            self.action_frame.grid_columnconfigure(0, weight=1)
            self.action_frame.grid_columnconfigure(1, weight=0)

        # Управление кнопкой выбора файла в зависимости от инструмента
        if tool_id == "guide":
            self.file_picker_frame.grid_remove()
            self.action_frame.grid_remove()
        else:
            self.file_picker_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
            self.action_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 20))
            
            # Загружаем сохраненный путь для выбранного инструмента
            saved_path = self.tool_paths.get(tool_id, "Файл не выбран")
            if config["needs_file"]:
                self.btn_select_file.configure(state="normal")
                self.file_path_var.set(saved_path)
            else:
                self.btn_select_file.configure(state="disabled")
                self.file_path_var.set("Выбор файла не требуется")

        # Вывод описания только если лог пустой (чтобы сохранять старые выводы)
        if self.active_log_textbox.get("1.0", "end-1c").strip() == "":
            if tool_id != "guide":
                print(f"\x1b[36mВыбран инструмент:\x1b[0m {config['name']}\n")
            print(f"{config['desc']}\n")
            if tool_id == "guide":
                self.after(50, lambda: self.active_log_textbox.see("1.0"))
            if tool_id != "guide":
                print("-" * 60)
                if config["needs_file"]:
                    print("Ожидание выбора файла...")
                else:
                    print("Готов к запуску.")

    def select_settings(self):
        colors = self.get_theme_colors()
        self.reset_sidebar_colors()
        self.btn_tab_settings.configure(fg_color=colors["sidebar_active"], text_color=colors["sidebar_active_text"])

        if self.current_tab != "settings":
            self.tool_frame.grid_forget()
            self.settings_frame.grid(row=0, column=1, padx=30, pady=30, sticky="nsew")
            self.current_tab = "settings"
    def change_theme(self, choice_ru):
        theme_en = self.theme_map[choice_ru]
        if theme_en == "Aquamarine":
            ctk.set_appearance_mode("Dark")
        else:
            ctk.set_appearance_mode(theme_en)
        
        SETTINGS["theme"] = theme_en
        save_settings(SETTINGS)
        self.update_text_tags()
        self.apply_theme_to_all()
        
        if theme_en == "Light":
            self.alpha_frame.pack(side="left")
        else:
            self.alpha_frame.pack_forget()

    def save_typo_settings(self):
        for key, var in self.typo_vars.items():
            SETTINGS[key] = var.get()
        save_settings(SETTINGS)

    def dec_alpha(self):
        val = SETTINGS.get("highlight_alpha", 100)
        if val > 0:
            val = max(0, val - 5)
            SETTINGS["highlight_alpha"] = val
            self.lbl_alpha.configure(text=str(val))
            save_settings(SETTINGS)
            self.update_text_tags()

    def inc_alpha(self):
        val = SETTINGS.get("highlight_alpha", 100)
        if val < 100:
            val = min(100, val + 5)
            SETTINGS["highlight_alpha"] = val
            self.lbl_alpha.configure(text=str(val))
            save_settings(SETTINGS)
            self.update_text_tags()

    def _start_alpha_change(self, action):
        self._alpha_change_running = True
        self._alpha_change_action = action
        self._do_alpha_change()

    def _do_alpha_change(self):
        if hasattr(self, '_alpha_change_running') and self._alpha_change_running:
            if self._alpha_change_action == 'inc':
                self.inc_alpha()
            elif self._alpha_change_action == 'dec':
                self.dec_alpha()
            self._alpha_job = self.after(100, self._do_alpha_change)

    def _stop_alpha_change(self, event=None):
        self._alpha_change_running = False
        if hasattr(self, '_alpha_job') and self._alpha_job is not None:
            self.after_cancel(self._alpha_job)
            self._alpha_job = None

    def mix_colors(self, fg_hex, bg_hex, alpha_pct):
        alpha = alpha_pct / 100.0
        fg_r = int(fg_hex[1:3], 16)
        fg_g = int(fg_hex[3:5], 16)
        fg_b = int(fg_hex[5:7], 16)
        bg_r = int(bg_hex[1:3], 16)
        bg_g = int(bg_hex[3:5], 16)
        bg_b = int(bg_hex[5:7], 16)
        r = int(fg_r * alpha + bg_r * (1 - alpha))
        g = int(fg_g * alpha + bg_g * (1 - alpha))
        b = int(fg_b * alpha + bg_b * (1 - alpha))
        return f"#{r:02x}{g:02x}{b:02x}"

    def update_text_tags(self):
        theme_en = SETTINGS.get("theme", "Dark")
        alpha = SETTINGS.get("highlight_alpha", 100)
        # Смешиваем с чисто-белым цветом, чтобы при прозрачности получались чистые пастельные тона (без "грязи")
        bg_light = SETTINGS.get("light_theme_bg_mix", "#FFFFFF")
        for tb in self.log_textboxes.values():
            if theme_en == "Light":
                # Здесь можно напрямую задать цвета светлой темы, например, c33 = "#FFFFE0" (Светло-жёлтый)
                c33 = SETTINGS.get("light_color_yellow", self.mix_colors("#FFD700", bg_light, alpha))
                c36 = SETTINGS.get("light_color_blue", self.mix_colors("#00FFFF", bg_light, alpha))
                c32 = SETTINGS.get("light_color_green", self.mix_colors("#32CD32", bg_light, alpha))
                c31 = SETTINGS.get("light_color_orange", self.mix_colors("#FF4500", bg_light, alpha))

                tb.tag_config("color_33", foreground="black", background=c33)
                tb.tag_config("color_36", foreground="black", background=c36)
                tb.tag_config("color_32", foreground="black", background=c32)
                tb.tag_config("color_31", foreground="black", background=c31)
            else:
                tb.tag_config("color_33", foreground="#FFD700", background="")
                tb.tag_config("color_36", foreground="#00FFFF", background="")
                tb.tag_config("color_32", foreground="#32CD32", background="")
                tb.tag_config("color_31", foreground="#FF4500", background="")

    def update_console_font_size(self, value):
        size = int(value)
        self.lbl_font_size.configure(text=str(size))
        self.console_font.configure(size=size)
        SETTINGS["console_font_size"] = size
        save_settings(SETTINGS)

    def update_console_font_family(self, value):
        self.console_font.configure(family=value)
        self.console_font_family = value
        SETTINGS["console_font_family"] = value
        save_settings(SETTINGS)

    def update_console_font_style(self, value):
        weight = "bold" if value == "bold" else "normal"
        slant = "italic" if value == "italic" else "roman"
        self.console_font.configure(weight=weight, slant=slant)
        self.console_font_style = value
        SETTINGS["console_font_style"] = value
        save_settings(SETTINGS)

    def sync_dictionaries(self):
        self.btn_sync_dicts.configure(state="disabled")
        
        def progress_cb(msg):
            color = "green" if "завершена" in msg else "orange"
            if "Ошибка" in msg: color = "red"
            self.after(0, lambda m=msg, c=color: self.lbl_update_status.configure(text=m, text_color=c))
            
        def task():
            try:
                paths.initialize_user_data(verbose=False) # Сначала сливаем с локальными (на всякий случай)
                success = paths.sync_dictionaries_from_github(progress_callback=progress_cb)
                if not success:
                    self.after(0, lambda: self.lbl_update_status.configure(text="Ошибка онлайн-синхронизации.", text_color="red"))
            except Exception as e:
                self.after(0, lambda: self.lbl_update_status.configure(text=f"Ошибка: {e}", text_color="red"))
            finally:
                self.after(0, lambda: self.btn_sync_dicts.configure(state="normal"))
                
        threading.Thread(target=task, daemon=True).start()

    def check_update(self):
        def task():
            self.after(0, lambda: self.btn_check_update.configure(state="disabled"))
            self.after(0, lambda: self.lbl_update_status.configure(text="Проверка...", text_color="gray"))
            
            # Используем константу версии
            current_version = APP_VERSION

            try:
                url = "https://raw.githubusercontent.com/zapeko/YoRZ/main/version.txt"
                with urllib.request.urlopen(url, timeout=5) as response:
                    new_version = response.read().decode('utf-8').strip()
                
                self.new_version = new_version
                
                # Функция для преобразования версии в кортеж чисел
                def parse_version(v):
                    return tuple(map(int, (v.split("."))))
                
                try:
                    is_newer = parse_version(new_version) > parse_version(current_version)
                except Exception:
                    # Если версия не парсится, откатываемся на строковое сравнение (с защитой от понижения версии)
                    is_newer = new_version != current_version and new_version > current_version

                if is_newer:
                    self.after(0, lambda: self.lbl_update_status.configure(text=f"Текущая версия: {current_version}. Новая версия: {new_version}", text_color="green"))
                    self.after(0, lambda: self.btn_download_update.configure(state="normal"))
                else:
                    self.after(0, lambda: self.lbl_update_status.configure(text=f"Текущая версия: {current_version}. Обновление не требуется.", text_color="gray"))
                    self.after(0, lambda: self.btn_download_update.configure(state="disabled"))
            except Exception as e:
                self.after(0, lambda: self.lbl_update_status.configure(text=f"Ошибка проверки: {e}", text_color="red"))
            finally:
                self.after(0, lambda: self.btn_check_update.configure(state="normal"))
                
        threading.Thread(target=task, daemon=True).start()

    def download_update(self):
        # (1) Возможность выбора директории и (2) фиксированное имя YoRZ.exe
        save_path = filedialog.asksaveasfilename(
            initialfile="YoRZ.exe",
            defaultextension=".exe",
            filetypes=[("Исполняемые файлы", "*.exe"), ("Все файлы", "*.*")],
            title="Выберите место для сохранения новой версии"
        )
        
        if not save_path:
            return

        def task():
            self.after(0, lambda: self.btn_download_update.configure(state="disabled"))
            self.after(0, lambda: self.lbl_update_status.configure(text="Скачивание...", text_color="gray"))
            try:
                # Магическая ссылка GitHub: всегда качает YoRZ.exe из последнего (latest) релиза
                url = "https://github.com/zapeko/YoRZ/releases/latest/download/YoRZ.exe"
                
                urllib.request.urlretrieve(url, save_path)
                filename = os.path.basename(save_path)
                self.after(0, lambda: self.lbl_update_status.configure(text=f"Сохранено: {filename}", text_color="green"))
            except Exception as e:
                self.after(0, lambda: self.lbl_update_status.configure(text=f"Ошибка скачивания: {e}", text_color="red"))
                self.after(0, lambda: self.btn_download_update.configure(state="normal"))

        threading.Thread(target=task, daemon=True).start()
    def copy_selected_text(self, event=None, widget=None):
        try:
            w = widget if widget else event.widget
            selected_text = w.selection_get()
            if selected_text:
                self.clipboard_clear()
                self.clipboard_append(selected_text)
                return "break"
        except Exception:
            pass

    def show_context_menu(self, event):
        try:
            # Check if there is any selected text first
            selected_text = event.widget.selection_get()
            if selected_text:
                menu = tk.Menu(self, tearoff=0)
                menu.add_command(label="Копировать", command=lambda: self.copy_selected_text(widget=event.widget))
                menu.tk_popup(event.x_root, event.y_root)
        except Exception:
            pass

    def zoom_console_font(self, event):
        step = 0
        if event.num == 4 or getattr(event, 'delta', 0) > 0:
            step = 2
        elif event.num == 5 or getattr(event, 'delta', 0) < 0:
            step = -2

        if step != 0:
            new_size = self.console_font_size + step
            if 10 <= new_size <= 36:
                self.console_font_size = new_size
                self.font_slider_var.set(new_size)
                self.update_console_font_size(new_size)
    def bind_keyboard_shortcuts(self):
        self.bind("1", lambda e: self.submit_choice('1'))
        self.bind("2", lambda e: self.submit_choice('2'))
        self.bind("3", lambda e: self.submit_choice('3'))
        self.bind("4", lambda e: self.submit_choice('4'))
        self.bind("<Return>", lambda e: self.submit_choice(''))
        
        self.bind("<KP_1>", lambda e: self.submit_choice('1'))
        self.bind("<KP_2>", lambda e: self.submit_choice('2'))
        self.bind("<KP_3>", lambda e: self.submit_choice('3'))
        self.bind("<KP_4>", lambda e: self.submit_choice('4'))
        self.bind("<KP_Enter>", lambda e: self.submit_choice(''))

    def select_file(self):
        if self.current_tool == "sorting":
            initial_dir = os.path.join(user_dir, "dictionaries")
            filetypes = (
                ("Базы словарей", "*.txt"),
            )
            filepath = filedialog.askopenfilename(title="Выберите yellow_base.txt или blacklist.txt", initialdir=initial_dir, filetypes=filetypes)
            if filepath:
                filename = os.path.basename(filepath).lower()
                if filename not in ["yellow_base.txt", "blacklist.txt"]:
                    print("\x1b[31m>> Ошибка: Для сортировки можно выбрать только yellow_base.txt или blacklist.txt!\x1b[0m")
                    return
                self.file_path_var.set(filepath)
                self.tool_paths[self.current_tool] = filepath
                print(f"\x1b[32m>> Выбран файл для сортировки:\x1b[0m {filepath}")
        else:
            filetypes = (
                ("Все поддерживаемые форматы", "*.txt;*.fb2;*.epub;*.md"),
                ("Текстовые файлы", "*.txt"),
                ("FB2 книги", "*.fb2"),
                ("EPUB архивы", "*.epub"),
                ("Markdown файлы", "*.md")
            )
            filepath = filedialog.askopenfilename(title="Выберите файл для обработки", filetypes=filetypes)
            if filepath:
                self.file_path_var.set(filepath)
                self.tool_paths[self.current_tool] = filepath
                
                # Если выбран файл в Типографе, автоматически прописываем пути с _fixed в другие инструменты
                if self.current_tool == "typographer":
                    base_dir = os.path.dirname(os.path.abspath(filepath))
                    base_name, ext = os.path.splitext(os.path.basename(filepath))
                    fixed_path = os.path.join(base_dir, f"{base_name}_fixed{ext}")
                    
                    self.tool_paths["extraction"] = fixed_path
                    self.tool_paths["yorz"] = fixed_path
                    print(f"\x1b[32m>> Выбран файл:\x1b[0m {filepath}")
                    print(f"\x1b[36m>> Автоматически установлены пути для извлечения и ёфикации:\x1b[0m {fixed_path}")
                else:
                    print(f"\x1b[32m>> Выбран файл:\x1b[0m {filepath}")

    def start_processing(self):
        config = TOOLS_CONFIG[self.current_tool]
        filepath = self.file_path_var.get()
        
        if config["needs_file"] and (filepath == "Файл не выбран" or not os.path.exists(filepath)):
            if self.current_tool in ["extraction", "yorz"] and "_fixed" in filepath:
                print(f"\x1b[31m>> Ошибка: Файл {filepath} ещё не существует!\x1b[0m")
                print("\x1b[33m>> Пожалуйста, сначала выберите исходный файл в инструменте «Типограф» и запустите его для создания _fixed версии.\x1b[0m")
            else:
                print("\x1b[31m>> Ошибка: Пожалуйста, выберите существующий файл!\x1b[0m")
            return

        self.running_tool = self.current_tool
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.btn_select_file.configure(state="disabled")
            
        print(f"\n{'='*60}\n\x1b[33m>> Запуск инструмента:\x1b[0m {config['name']}\n{'='*60}")
        
        threading.Thread(target=self.process_file_thread, args=(filepath, self.current_tool), daemon=True).start()

    def stop_processing(self):
        if self.running_tool == "yorz":
            yorz.SHOULD_STOP = True
        else:
            print(f"\n\x1b[33m>> Остановка доступна только для процесса ёфикации.\x1b[0m")

        # Если мы ждём ввода пользователя, принудительно прерываем ожидание
        if getattr(self, "is_waiting_for_input", False):
            self.submit_choice('')

    def process_file_thread(self, filepath, tool_id):
        builtins.input = self.custom_input
        builtins.gui_custom_input = self.custom_input
        builtins.gui_update_progress = self.update_progress
        try:
            # Если файл не выбран, передаём пустую строку, чтобы модули использовали свои дефолты
            f = filepath if filepath not in ("Файл не выбран", "Выбор файла не требуется") else ""

            if tool_id == "yorz":
                yorz.run(input_file=f if f else "book.txt", app_version=APP_VERSION)
            elif tool_id == "typographer":
                options = {
                    'zwnbsp': SETTINGS.get('typo_zwnbsp', True),
                    'html_nbsp': SETTINGS.get('typo_html_nbsp', True),
                    'nbsp': SETTINGS.get('typo_nbsp', True),
                    'shy': SETTINGS.get('typo_shy', True),
                    'spaces': SETTINGS.get('typo_spaces', True),
                    'letter_digit_spaces': SETTINGS.get('typo_letter_digit_spaces', True),
                    'punctuation': SETTINGS.get('typo_punctuation', True),
                    'dashes': SETTINGS.get('typo_dashes', True),
                    'merge_lines': SETTINGS.get('typo_merge_lines', True),
                    'keep_leading_dashes': SETTINGS.get('typo_keep_leading_dashes', False),
                    'remove_all_empty': SETTINGS.get('typo_remove_all_empty', False),
                    'deyo': SETTINGS.get('typo_deyo', False)
                }
                typographer.run(input_file=f if f else "book.txt", options=options, app_version=APP_VERSION)
            elif tool_id == "extraction":
                extraction.run(input_filename=f if f else "book.txt")
            elif tool_id == "sorting":
                sorting.run(input_filename=f if f else "dictionaries/yellow_base.txt")
            elif tool_id == "twin":
                twin.run()
            elif tool_id == "yellow_dic":
                yellow_dic_forming.run()

            print(f"\n\x1b[32m>> ГОТОВО! Работа успешно завершена.\x1b[0m")

        except BaseException as e:
            if isinstance(e, KeyboardInterrupt) or (hasattr(yorz, 'SHOULD_STOP') and yorz.SHOULD_STOP):
                print(f"\n\x1b[33m>> Ёфикация текста остановлена с возможностью продолжения.\x1b[0m")
            else:
                print(f"\n\x1b[31m>> Критическая ошибка:\x1b[0m {e}")
        finally:
            builtins.input = self.original_input
            if hasattr(builtins, 'gui_update_progress'):
                delattr(builtins, 'gui_update_progress')
            self.after(0, self.restore_ui_state)

    def update_progress(self, percent):
        self.after(0, self._set_progress, percent)

    def _set_progress(self, percent):
        if not self.progress_frame.grid_info():
            self.progress_frame.grid(row=5, column=0, columnspan=2, pady=(10, 0), sticky="ew")
        if not self.progress_bar.grid_info():
            self.progress_bar.grid(row=0, column=0, sticky="ew")
        self.progress_bar.set(percent)

    def restore_ui_state(self):
        self.running_tool = None
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.progress_bar.grid_remove()
        self.progress_frame.grid_remove()
        self.progress_bar.set(0)
        # Включаем кнопку выбора файла только если инструмент в ней нуждается
        config = TOOLS_CONFIG[self.current_tool]
        if config["needs_file"]:
            self.btn_select_file.configure(state="normal")
        
        # Полностью скрываем кнопки выбора после завершения работы инструмента
        for btn in self.choice_buttons:
            btn.grid_remove()
        self.choice_frame.grid_remove()

    def custom_input(self, prompt="", button_labels=None):
        print(prompt, end="")
        self.input_event = threading.Event()
        self.user_choice = ""
        self.is_waiting_for_input = True
        
        # Если переданы свои названия кнопок, временно меняем текст на кнопках
        self.current_button_labels = button_labels
        
        self.after(0, self.show_choice_buttons)
        self.input_event.wait()
        
        self.is_waiting_for_input = False
        print(self.user_choice)
        return self.user_choice

    def show_choice_buttons(self):
        labels = self.current_button_labels or [
            "1 (Оригинал)", "2 (Ё-вариант)", "3 (Ориг. везде)", "4 (Ё-вар. везде)", "Пропустить (Enter)"
        ]
        
        if not self.choice_frame.grid_info():
            self.choice_frame.grid(row=4, column=0, columnspan=2, pady=(10, 0), sticky="ew")

        for i, btn in enumerate(self.choice_buttons):
            if i < len(labels):
                btn.configure(text=labels[i])
                if not btn.grid_info():
                    btn.grid(row=0, column=i, padx=5, sticky="ew")
            else:
                if btn.grid_info():
                    btn.grid_remove()

        target_tb = self.log_textboxes.get(self.running_tool)
        if target_tb:
            self.after(50, lambda: target_tb.see("end"))

    def submit_choice(self, choice):
        if not self.is_waiting_for_input: return
        # Никак не меняем кнопки, чтобы не было никаких визуальных сдвигов
        self.user_choice = choice
        self.input_event.set()

if __name__ == "__main__":
    app = App()
    app.mainloop()
