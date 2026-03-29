import os
import sys
import shutil
import re
import urllib.request
import urllib.error

# Определение путей
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
elif "__compiled__" in globals():
    APP_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
else:
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Определение пути к данным пользователя в зависимости от ОС
if sys.platform == "win32":
    appdata = os.environ.get("APPDATA")
    if appdata:
        USER_DATA_DIR = os.path.join(appdata, "YoRZ")
    else:
        USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "YoRZ")
elif sys.platform == "darwin":
    # Для macOS
    USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "YoRZ")
else:
    # Для Linux и других UNIX-подобных систем
    USER_DATA_DIR = os.path.join(os.path.expanduser("~"), ".config", "YoRZ")

USER_DICTS_DIR = os.path.join(USER_DATA_DIR, 'dictionaries')

HEADER_MERGE = "# --- Добавлено при слиянии ---\n"
HEADER_AUTO = "# --- Добавлено автоматически ---\n"

def get_path(relative_path):
    """Возвращает путь к файлу в USER_DATA_DIR."""
    return os.path.join(USER_DATA_DIR, relative_path.replace('/', os.sep))

def merge_text_files(src_file, dest_file, verbose=True):
    """Объединяет строки двух текстовых файлов (уникальные строки)."""
    try:
        if not os.path.exists(dest_file):
            shutil.copy2(src_file, dest_file)
            if verbose: print(f"[SYNC] Файл {os.path.basename(dest_file)} создан.")
            return

        with open(src_file, 'r', encoding='utf-8') as f:
            src_words = {line.strip() for line in f if line.strip() and not line.strip().startswith('#')}
        
        with open(dest_file, 'r', encoding='utf-8') as f:
            dest_lines = f.readlines()
            
        dest_words = {line.strip() for line in dest_lines if line.strip() and not line.strip().startswith('#')}
        new_words = src_words - dest_words

        if new_words:
            # Проверяем, есть ли уже заголовок
            has_header = any(HEADER_MERGE.strip() in line for line in dest_lines)
            
            with open(dest_file, 'a', encoding='utf-8') as f:
                if not has_header:
                    f.write("\n" + HEADER_MERGE)
                for word in sorted(list(new_words)):
                    f.write(word + '\n')
            if verbose: print(f"[SYNC] Файл {os.path.basename(dest_file)} обновлен.")
        else:
            if verbose: print(f"[SYNC] Файл {os.path.basename(dest_file)} не изменился, пропуск записи.")
    except Exception as e:
        print(f"Ошибка при слиянии текстовых файлов {src_file}: {e}")

def merge_dic_files(src_file, dest_file, verbose=True):
    """Объединяет правила в .dic файлах, сливая исключения и не дублируя заголовки."""
    try:
        if not os.path.exists(dest_file):
            shutil.copy2(src_file, dest_file)
            if verbose: print(f"[SYNC] Файл {os.path.basename(dest_file)} создан.")
            return

        with open(src_file, 'r', encoding='utf-8') as f:
            src_lines = f.readlines()
        with open(dest_file, 'r', encoding='utf-8') as f:
            dest_lines = f.readlines()

        dest_rules = {}
        for idx, line in enumerate(dest_lines):
            clean_line = line.strip()
            if '|' in clean_line and not clean_line.startswith('#'):
                parts = clean_line.split('|', 1)
                rule_left = parts[0].strip()
                rule_right = parts[1].strip()
                replacement = rule_right
                exceptions = set()
                if '(' in rule_right and ')' in rule_right:
                    m = re.match(r'^(.*?)\((.*?)\)$', rule_right)
                    if m:
                        replacement = m.group(1).strip()
                        exceptions = {ex.strip() for ex in m.group(2).split(':') if ex.strip()}
                dest_rules[rule_left] = {'replacement': replacement, 'exceptions': exceptions, 'index': idx}

        new_rules = []
        for line in src_lines:
            clean_line = line.strip()
            if '|' in clean_line and not clean_line.startswith('#'):
                parts = clean_line.split('|', 1)
                src_left, src_right = parts[0].strip(), parts[1].strip()
                src_replacement = src_right
                src_exceptions = set()
                if '(' in src_right and ')' in src_right:
                    m = re.match(r'^(.*?)\((.*?)\)$', src_right)
                    if m:
                        src_replacement = m.group(1).strip()
                        src_exceptions = {ex.strip() for ex in m.group(2).split(':') if ex.strip()}

                if src_left in dest_rules:
                    dest_data = dest_rules[src_left]
                    merged_exceptions = dest_data['exceptions'].union(src_exceptions)
                    if merged_exceptions:
                        exc_str = ":".join(sorted(list(merged_exceptions)))
                        new_line = f"{src_left}|{src_replacement} ({exc_str})\n"
                    else:
                        new_line = f"{src_left}|{src_replacement}\n"
                    dest_lines[dest_data['index']] = new_line
                else:
                    new_rules.append(line)

        # Подготавливаем итоговый список строк для проверки
        final_lines = dest_lines.copy()
        if new_rules:
            has_header = any(HEADER_MERGE.strip() in line for line in dest_lines)
            if not has_header:
                final_lines.append("\n" + HEADER_MERGE)
            final_lines.extend(new_rules)

        if final_lines != dest_lines or new_rules: # Simple check for change
            # Actually compare with original content
            with open(dest_file, 'r', encoding='utf-8') as f:
                old_content = f.readlines()
            
            if final_lines != old_content:
                with open(dest_file, 'w', encoding='utf-8') as f:
                    f.writelines(final_lines)
                if verbose: print(f"[SYNC] Файл {os.path.basename(dest_file)} обновлен.")
            else:
                if verbose: print(f"[SYNC] Файл {os.path.basename(dest_file)} не изменился, пропуск записи.")
        else:
            if verbose: print(f"[SYNC] Файл {os.path.basename(dest_file)} не изменился, пропуск записи.")
    except Exception as e:
        print(f"Ошибка при слиянии .dic файлов {src_file}: {e}")

def ensure_user_data_exists():
    """Быстрая проверка при запуске: копирует файлы только если их нет."""
    try:
        if not os.path.exists(USER_DATA_DIR): os.makedirs(USER_DATA_DIR)
        if not os.path.exists(USER_DICTS_DIR): os.makedirs(USER_DICTS_DIR)
        source_dicts = os.path.join(APP_DIR, 'dictionaries')
        if os.path.exists(source_dicts):
            for filename in os.listdir(source_dicts):
                dest_file = os.path.join(USER_DICTS_DIR, filename)
                if not os.path.exists(dest_file):
                    shutil.copy2(os.path.join(source_dicts, filename), dest_file)
        
        settings_file = 'yorz_settings.json'
        src_settings = os.path.join(APP_DIR, settings_file)
        dest_settings = os.path.join(USER_DATA_DIR, settings_file)
        if os.path.exists(src_settings) and not os.path.exists(dest_settings):
            shutil.copy2(src_settings, dest_settings)
        return True
    except Exception as e:
        print(f"Ошибка при проверке данных: {e}")
        return False

def initialize_user_data(verbose=True):
    """Полная синхронизация и слияние словарей (вызывается из настроек)."""
    try:
        ensure_user_data_exists()
        source_dicts = os.path.join(APP_DIR, 'dictionaries')
        if os.path.exists(source_dicts):
            for filename in os.listdir(source_dicts):
                src_file = os.path.join(source_dicts, filename)
                dest_file = os.path.join(USER_DICTS_DIR, filename)
                if filename.endswith('.txt'): merge_text_files(src_file, dest_file, verbose=verbose)
                elif filename.endswith('.dic'): merge_dic_files(src_file, dest_file, verbose=verbose)
        return True
    except Exception as e:
        print(f"Ошибка синхронизации: {e}")
        return False

def verify_orange_dic_in_base():
    """Проверяет, все ли слова из orange.dic есть в yellow_base.txt, и добавляет недостающие."""
    orange_path = get_path("dictionaries/orange.dic")
    base_path = get_path("dictionaries/yellow_base.txt")
    root_path = get_path("dictionaries/yellow_root.txt")
    
    if not os.path.exists(orange_path) or not os.path.exists(base_path) or not os.path.exists(root_path):
        return

    try:
        # Читаем корни для фильтрации
        with open(root_path, 'r', encoding='utf-8') as f:
            raw_roots = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        
        roots_tuples = []
        for r in raw_roots:
            roots_tuples.append((r, r.replace("ё", "е")))

        # Внутренняя функция для проверки корня (аналог из extraction)
        def check_root(word, r, r_v):
            if r[0] == "ё": return word.startswith(r) or word.startswith(r_v)
            if r[-1] == "ё": return word.endswith(r) or word.endswith(r_v)
            if len(r) > 2 and r[1] == "ё": return r in word or r_v in word
            return False

        def has_any_root(word):
            for r, r_v in roots_tuples:
                if check_root(word, r, r_v): return True
            return False

        # Читаем базу
        with open(base_path, 'r', encoding='utf-8') as f:
            base_lines = f.readlines()
            
        base_words = {line.strip() for line in base_lines if line.strip() and not line.strip().startswith('#')}
        words_to_add = set()
        added_pairs = []

        # Читаем orange.dic и извлекаем слова
        with open(orange_path, 'r', encoding='utf-8') as f:
            for line in f:
                clean_line = line.strip()
                if '|' in clean_line and not clean_line.startswith('#'):
                    parts = clean_line.split('|', 1)
                    left = parts[0].strip()
                    right = parts[1].strip()
                    
                    # Убираем исключения из правой части
                    if '(' in right and ')' in right:
                        m = re.match(r'^(.*?)\(', right)
                        if m: right = m.group(1).strip()
                    
                    # Проверяем обе части пары
                    for word in [left, right]:
                        # 1. Проверка на шаблон (регулярные выражения)
                        if any(c in word for c in "\\*+|?[]"):
                            continue
                        
                        # 2. Проверка на наличие корней
                        if not has_any_root(word):
                            continue
                            
                        # 3. Добавляем если еще нет в базе
                        if word and word not in base_words and word not in words_to_add:
                            words_to_add.add(word)
                            if f"{left}|{right}" not in added_pairs:
                                added_pairs.append(f"{left}|{right}")

        # Добавляем в yellow_base.txt
        if words_to_add:
            has_header = any(HEADER_AUTO.strip() in line for line in base_lines)
            with open(base_path, 'a', encoding='utf-8') as f:
                if not has_header:
                    f.write("\n" + HEADER_AUTO)
                for word in sorted(list(words_to_add)):
                    f.write(word + '\n')
            
            # Логируем добавленные пары
            for pair in added_pairs:
                print(f"[SYNC] Внимание: Слова из пары {pair} (из orange.dic) были автоматически добавлены в yellow_base.txt.")
                
    except Exception as e:
        print(f"[SYNC ERROR] Ошибка при проверке orange.dic: {e}")

def sync_dictionaries_from_github(progress_callback=None):
    """
    Скачивает актуальные словари с GitHub и сливает их с пользовательскими.
    progress_callback - опциональная функция для вывода сообщений о статусе.
    """
    repo_url = "https://raw.githubusercontent.com/zapeko/YoRZ/main/dictionaries/"
    files_to_sync = [
        "yellow_root.txt", "yellow_base.txt", "yellow_add.txt", 
        "blacklist.txt", "yellow.dic", "green.dic", "blue.dic", "orange.dic"
    ]
    
    temp_dir = os.path.join(USER_DATA_DIR, "temp_sync")
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
        
    success_count = 0
    try:
        for i, filename in enumerate(files_to_sync):
            if progress_callback:
                progress_callback(f"Скачивание {filename} ({i+1}/{len(files_to_sync)})...")
            print(f"[SYNC] Пытаюсь скачать {filename}...")
            
            url = repo_url + filename
            temp_file = os.path.join(temp_dir, filename)
            dest_file = os.path.join(USER_DICTS_DIR, filename)
            
            try:
                # Используем urlopen вместо urlretrieve для возможности задать timeout
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response, open(temp_file, 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)
                
                print(f"[SYNC] Успешно скачан {filename} во временную папку.")
                # Выполняем умное слияние загруженного файла с локальным
                if filename.endswith('.txt'):
                    merge_text_files(temp_file, dest_file)
                elif filename.endswith('.dic'):
                    merge_dic_files(temp_file, dest_file)
                success_count += 1
            except Exception as e:
                # Если файла нет на GitHub или ошибка сети — пропускаем файл
                print(f"[SYNC ERROR] Ошибка при загрузке/слиянии {filename}: {e}")
                
        if success_count > 0:
            verify_orange_dic_in_base()
            if progress_callback:
                progress_callback("Синхронизация успешно завершена!")
            return True
        else:
            if progress_callback:
                progress_callback("Ошибка: Не удалось скачать ни один словарь с GitHub.")
            return False
    except Exception as e:
        print(f"[SYNC ERROR] Общая ошибка онлайн-синхронизации: {e}")
        if progress_callback:
            progress_callback(f"Ошибка: {e}")
        return False
    finally:
        # Удаляем временную папку после завершения
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

def open_user_data_dir():
    """Открывает папку с пользовательскими словарями в системном проводнике."""
    import subprocess
    path = USER_DICTS_DIR
    if not os.path.exists(path):
        os.makedirs(path)
    
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            # Для Linux
            try:
                subprocess.Popen(["xdg-open", path])
            except FileNotFoundError:
                print(f"Папка находится здесь: {path}")
        return True
    except Exception as e:
        print(f"Не удалось открыть папку автоматически: {e}")
        print(f"Вы можете открыть её вручную: {path}")
        return False


