import os
import re
from colorama import Fore, Style
from . import paths

def find_word_pairs(input_file=None, orange_file=None):
    if input_file is None: input_file = paths.get_path('dictionaries/yellow_base.txt')
    if orange_file is None: orange_file = paths.get_path('dictionaries/orange.dic')

    if not os.path.exists(input_file):
        print(f"{Fore.RED}Файл {input_file} не найден!{Style.RESET_ALL}")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        words = {line.strip() for line in f if line.strip() and not line.strip().startswith('#')}
    
    pairs = set()
    for word in words:
        if 'ё' in word.lower(): continue
        if 'е' not in word.lower(): continue
        for i, char in enumerate(word):
            if char.lower() == 'е':
                candidate = word[:i] + ('ё' if char == 'е' else 'Ё') + word[i+1:]
                if candidate in words:
                    pairs.add(f"{word}|{candidate}")

    if not pairs:
        print(f"{Fore.YELLOW}Новых пар омографов не найдено.{Style.RESET_ALL}")
        return

    # Загружаем существующие правила из orange.dic, чтобы не дублировать
    existing_regexes = []
    orange_lines = []
    if os.path.exists(orange_file):
        with open(orange_file, 'r', encoding='utf-8') as f:
            orange_lines = f.readlines()
            for line in orange_lines:
                if '|' in line and not line.strip().startswith('#'):
                    # Левая часть правила может быть регулярным выражением (например, вечерк\w+)
                    left_part = line.split('|')[0].strip()
                    try:
                        # Компилируем регулярное выражение для полного совпадения
                        pattern = re.compile(f"^{left_part}$", re.IGNORECASE)
                        existing_regexes.append(pattern)
                    except re.error:
                        pass

    new_pairs = []
    for pair in sorted(list(pairs)):
        left = pair.split('|')[0].strip()
        # Проверяем, не подпадает ли слово под одно из существующих регулярных выражений
        is_covered = any(pattern.match(left) for pattern in existing_regexes)
        if not is_covered:
            new_pairs.append(pair + '\n')

    if new_pairs:
        has_auto_header = any("# --- Добавлено автоматически ---" in line for line in orange_lines)
        with open(orange_file, 'a', encoding='utf-8') as f:
            if not has_auto_header:
                f.write("\n# --- Добавлено автоматически ---\n")
            f.writelines(new_pairs)
        print(f"{Fore.GREEN}Найдено и добавлено новых пар в orange.dic: {len(new_pairs)}{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}Все найденные пары уже есть в orange.dic.{Style.RESET_ALL}")

def run(input_file=None, orange_file=None):
    find_word_pairs(input_file, orange_file)

if __name__ == '__main__':
    run()
