# Скрипт-ёфикатор YoRZ от Романа Запеко
# Версия: 4.6.0 (28.04.2025)

# Последовательная обработка текста по словарям:
# 1 (синий, автоматически) | blue.dic - словарь регулярных выражений без буквы ё
# 2 (зелёный, автоматически) | green.dic - словарь регулярных выражений с буквой ё
# 3 (оранжевый, выбор варианта) | orange.dic - словарь со словами разного значения
# 4 (жёлтый, автоматически) | yellow.dic - корневой словарь

import re
import os
import sys
import signal
from colorama import init, Fore, Style

init()

def handle_sigint(signum, frame):
    print(f"\n{Fore.RED}Обработка текста прервана! Изменения не сохранены!{Style.RESET_ALL}")
    os._exit(0)

signal.signal(signal.SIGINT, handle_sigint)

def load_yo_dict(file_path):
    """Загрузка словаря yellow.dic с исключениями и шаблонами."""
    yo_dict = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        for line_num, line in enumerate(file, 1):
            line = line.strip()
            if not line or '|' not in line:
                continue

            main_part, *rest = line.split('(', 1)
            parts = main_part.split('|', 1)
            if len(parts) < 2:
                print(f"{Fore.YELLOW}Пропущена строка {line_num}: '{line}' - неверный формат{Style.RESET_ALL}")
                continue
            key_part, replace_part = parts
            key = key_part.strip()
            replace = replace_part.strip()

            # Генерация паттерна и сбор номеров групп для wildcards
            pattern_parts = []
            wildcard_groups = []
            current_group = 1
            for segment in re.split(r'(\\w[\*\+])', key):
                if segment in (r'\w*', r'\w+'):
                    quant = '*' if segment == r'\w*' else '+'
                    pattern_parts.append(f'(\\w{quant})')
                    wildcard_groups.append(current_group)
                    current_group += 1
                else:
                    pattern_parts.append(re.escape(segment))
            pattern_str = r'\b' + ''.join(pattern_parts) + r'\b'

            # Формирование замены с последовательной заменой wildcards
            parts = re.split(r'(\\w[\*\+])', replace)
            for i in range(1, len(parts), 2):
                if parts[i] in (r'\w*', r'\w+'):
                    try:
                        parts[i] = f'\\{wildcard_groups.pop(0)}'
                    except IndexError:
                        print(f"{Fore.YELLOW}Предупреждение: несоответствие количества wildcards в строке {line_num}{Style.RESET_ALL}")
                        break
            replacement = ''.join(parts)

            # Компиляция паттерна
            try:
                pattern = re.compile(pattern_str, re.I)
            except re.error as e:
                print(f"{Fore.RED}Ошибка в строке {line_num}: {e}{Style.RESET_ALL}")
                continue

            # Обработка исключений
            exc_patterns = []
            if rest:
                exc_part = rest[0].split(')', 1)[0].strip()
                for exc in exc_part.split(':'):
                    exc = exc.strip()
                    exc = re.sub(r'\\(w[\*\+])', r'\\\1', exc)
                    try:
                        exc_pattern = re.compile(fr'\b{exc}\b', re.I)
                        exc_patterns.append(exc_pattern)
                    except re.error as e:
                        print(f"{Fore.YELLOW}Ошибка в исключении: {exc} ({e}){Style.RESET_ALL}")

            yo_dict[key] = {
                'replace': replacement,
                'exceptions_compiled': exc_patterns,
                'pattern': pattern,
                'priority': len(key.replace(r'\w', ''))
            }
    return yo_dict

def replace_yo_patterns(text, yo_dict):
    """Замена с учётом шаблонов и исключений."""
    sorted_data = sorted(yo_dict.values(), key=lambda x: (-x['priority'], str(x['pattern'])))

    spans = re.split(r'(<span[^>]*>.*?</span>)', text, flags=re.DOTALL)
    for i in range(0, len(spans), 2):
        part = spans[i]
        for data in sorted_data:
            part = data['pattern'].sub(
                lambda m: (
                    m.group() if any(exc.search(m.group()) for exc in data['exceptions_compiled'])
                    else f'<span class="highlight-yellow">{preserve_case(m, m.expand(data["replace"]))}</span>'
                ),
                part
            )
        spans[i] = part
    return ''.join(spans)

def replace_yo_in_text(text, yo_dict):
    """Заменяет слова без ё на слова с ё в тексте, включая текст внутри тегов <span>."""
    span_pattern = re.compile(r'(<span[^>]*>.*?</span>)', re.DOTALL)
    parts = span_pattern.split(text)
    for i, part in enumerate(parts):
        if span_pattern.match(part):
            match = re.match(r'(<span class="[^"]*">)(.*?)(</span>)', part, re.DOTALL)
            if match:
                opening_tag = match.group(1)
                content = match.group(2)
                closing_tag = match.group(3)
                processed_content = replace_yo_patterns(content, yo_dict)
                parts[i] = opening_tag + processed_content + closing_tag
        else:
            parts[i] = replace_yo_patterns(part, yo_dict)
    return ''.join(parts)

def preserve_case(match, replacement):
    """Сохраняет регистр при замене текста."""
    original_text = match.group()
    original_words = re.findall(r'\w+|\W+', original_text)
    replacement_words = re.findall(r'\w+|\W+', replacement)
    result = []
    for orig_word, repl_word in zip(original_words, replacement_words):
        if orig_word.isupper():
            result.append(repl_word.upper())
        elif orig_word.istitle():
            result.append(repl_word.title())
        else:
            result.append(repl_word.lower())
    return ''.join(result)

def load_yo_variants(file_path):
    """Загрузка словаря orange.dic с шаблонами и исключениями."""
    yo_variants = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        for line_num, line in enumerate(file, 1):
            line = line.strip()
            if not line or '|' not in line:
                continue

            main_part, *rest = line.split('(', 1)
            parts = main_part.split('|', 1)
            if len(parts) < 2:
                print(f"{Fore.YELLOW}Пропущена строка {line_num}: '{line}' - неверный формат{Style.RESET_ALL}")
                continue
            original, replacement = parts
            original, replacement = original.strip(), replacement.strip()

            # Генерация паттерна и сбор номеров групп
            pattern_parts = []
            wildcard_groups = []
            current_group = 1
            for segment in re.split(r'(\\w[\*\+])', original):
                if segment in (r'\w*', r'\w+'):
                    quant = '*' if segment == r'\w*' else '+'
                    pattern_parts.append(f'(\\w{quant})')
                    wildcard_groups.append(current_group)
                    current_group += 1
                else:
                    pattern_parts.append(re.escape(segment))
            pattern_str = r'\b' + ''.join(pattern_parts) + r'\b'

            # Формирование замены
            parts = re.split(r'(\\w[\*\+])', replacement)
            for i in range(1, len(parts), 2):
                if parts[i] in (r'\w*', r'\w+'):
                    try:
                        parts[i] = f'\\{wildcard_groups.pop(0)}'
                    except IndexError:
                        print(f"{Fore.YELLOW}Предупреждение: несоответствие количества wildcards в строке {line_num}{Style.RESET_ALL}")
                        break
            final_repl = ''.join(parts)

            try:
                pattern = re.compile(pattern_str, re.I)
            except re.error as e:
                print(f"{Fore.RED}Ошибка в строке {line_num}: {e}{Style.RESET_ALL}")
                continue

            # Обработка исключений
            exc_patterns = []
            if rest:
                exc_part = rest[0].split(')', 1)[0].strip()
                for exc in exc_part.split(':'):
                    exc = exc.strip()
                    exc = re.sub(r'\\(w[\*\+])', r'\\\1', exc)
                    try:
                        exc_pattern = re.compile(fr'\b{exc}\b', re.I)
                        exc_patterns.append(exc_pattern)
                    except re.error as e:
                        print(f"{Fore.YELLOW}Ошибка в исключении: {exc} ({e}){Style.RESET_ALL}")

            yo_variants[pattern] = {
                'replacement': final_repl,
                'exceptions': exc_patterns
            }
    return yo_variants

def process_yo_variants(text, yo_variants):
    """Обработка вариантов с выводом полной строки и подсветкой только текущего слова."""
    replace_all_choices = {}  # Словарь для запоминания выбора "везде"
    lines = text.split('\n')
    span_pattern = re.compile(r'(<span[^>]*>.*?</span>)', re.DOTALL)

    for line_num, line in enumerate(lines):
        parts = span_pattern.split(line)  # Разбиваем строку на части
        new_parts = parts.copy()  # Копия для обновления текста

        # Обрабатываем только части вне тегов <span>
        for part_idx, part in enumerate(parts):
            if span_pattern.match(part):  # Пропускаем теги <span>
                continue

            # Разбиваем часть на слова и разделители
            words = re.split(r'(\W+)', part)
            for word_idx in range(len(words)):
                word = words[word_idx]
                if not word or not re.match(r'\w+', word):  # Пропускаем неслова
                    continue

                # Проверяем, есть ли выбор "везде"
                replaced = False
                for pattern in yo_variants:
                    if pattern in replace_all_choices:
                        match = pattern.fullmatch(word)
                        if match and not any(exc.search(word) for exc in yo_variants[pattern]['exceptions']):
                            new_word = preserve_case(match, replace_all_choices[pattern])
                            words[word_idx] = f'<span class="highlight-orange">{new_word}</span>'
                            new_parts[part_idx] = ''.join(words)
                            replaced = True
                            break
                if replaced:
                    continue

                # Обрабатываем слово, если оно соответствует шаблону
                for pattern, data in yo_variants.items():
                    match = pattern.fullmatch(word)
                    if not match:
                        continue

                    # Проверяем исключения
                    if any(exc.search(word) for exc in data['exceptions']):
                        continue  # Пропускаем, если слово является исключением

                    base_word = match.group()  # Слово без "ё"
                    yo_word = match.expand(data['replacement'])  # Слово с "ё"

                    if base_word.lower() == yo_word.lower():  # Пропускаем идентичные варианты
                        break

                    # Формируем строку с подсветкой только текущего слова
                    temp_words = words.copy()
                    temp_words[word_idx] = Fore.YELLOW + word + Style.RESET_ALL
                    temp_parts = parts.copy()
                    temp_parts[part_idx] = ''.join(temp_words)
                    highlighted_line = re.sub(r'<[^>]*>', '', ''.join(temp_parts))

                    # Выводим строку и запрашиваем выбор
                    print(f"\n{Fore.CYAN}Строка {line_num+1}:{Style.RESET_ALL}")
                    print(highlighted_line)
                    print(f"{Fore.GREEN}Варианты: 1 или 3 >>> {base_word.lower()} | {yo_word.lower()} <<< 2 или 4")
                    choice_input = input("Выберите [1/2/3,4-везде/Enter-пропустить]: ").strip()

                    new_word = word  # По умолчанию оставляем без изменений
                    if choice_input:
                        choice = choice_input[0]
                        if choice == '1':
                            new_word = base_word
                        elif choice == '2':
                            new_word = yo_word
                        elif choice == '3':
                            replace_all_choices[pattern] = base_word
                            new_word = base_word
                        elif choice == '4':
                            replace_all_choices[pattern] = yo_word
                            new_word = yo_word
                        else:
                            print(f"{Fore.RED}Неверный ввод. Пропускаем.{Style.RESET_ALL}")
                            new_word = word

                    # Обновляем слово в тексте
                    new_word = preserve_case(match, new_word)
                    words[word_idx] = f'<span class="highlight-orange">{new_word}</span>'
                    new_parts[part_idx] = ''.join(words)
                    break

        # Обновляем строку
        lines[line_num] = ''.join(new_parts)

    return '\n'.join(lines)

def load_dict_with_exceptions(file_path):
    """Загрузка словаря green.dic с поддержкой исключений."""
    replacements_dict = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        for line_num, line in enumerate(file, 1):
            line = line.strip()
            if not line or '|' not in line:
                continue

            main_part, *rest = line.split('(', 1)
            parts = main_part.split('|', 1)
            if len(parts) < 2:
                print(f"{Fore.YELLOW}Пропущена строка {line_num}: '{line}' - неверный формат{Style.RESET_ALL}")
                continue
            original, replacement = parts
            original, replacement = original.strip(), replacement.strip()

            # Обработка исключений
            exc_patterns = []
            if rest:
                exc_part = rest[0].split(')', 1)[0].strip()
                for exc in exc_part.split(':'):
                    exc = exc.strip()
                    exc = re.sub(r'\\(w[\*\+])', r'\\\1', exc)
                    try:
                        exc_pattern = re.compile(fr'\b{exc}\b', re.I)
                        exc_patterns.append(exc_pattern)
                    except re.error as e:
                        print(f"{Fore.YELLOW}Ошибка в исключении: {exc} ({e}){Style.RESET_ALL}")

            replacements_dict[original] = {
                'replacement': replacement,
                'exceptions': exc_patterns
            }
    return replacements_dict

def apply_replacements(text, replacements_dict, span_class):
    """Применяет замены из словаря только к тексту вне тегов <span>, с учётом исключений."""
    span_pattern = re.compile(r'(<span[^>]*>.*?</span>)')
    parts = span_pattern.split(text)
    for i, part in enumerate(parts):
        if not span_pattern.match(part):
            for original, data in replacements_dict.items():
                replacement = data['replacement']
                exceptions = data['exceptions']
                if r'\w*' in original or r'\w+' in original:
                    # Генерация паттерна
                    pattern_parts = []
                    wildcard_groups = []
                    current_group = 1
                    for segment in re.split(r'(\\w[\*\+])', original):
                        if segment in (r'\w*', r'\w+'):
                            quant = '*' if segment == r'\w*' else '+'
                            pattern_parts.append(f'(\\w{quant})')
                            wildcard_groups.append(current_group)
                            current_group += 1
                        else:
                            pattern_parts.append(re.escape(segment))
                    pattern_str = r'\b' + ''.join(pattern_parts) + r'\b'

                    # Формирование замены
                    repl_parts = re.split(r'(\\w[\*\+])', replacement)
                    for j in range(1, len(repl_parts), 2):
                        if repl_parts[j] in (r'\w*', r'\w+'):
                            try:
                                repl_parts[j] = f'\\{wildcard_groups.pop(0)}'
                            except IndexError:
                                print(f"{Fore.YELLOW}Предупреждение: несоответствие wildcards в {original}|{replacement}{Style.RESET_ALL}")
                                break
                    fixed_replacement = ''.join(repl_parts)

                    regex = re.compile(pattern_str, re.I)
                    part = regex.sub(
                        lambda m: (
                            m.group() if any(exc.search(m.group()) for exc in exceptions)
                            else f'<span class="{span_class}">{preserve_case(m, m.expand(fixed_replacement))}</span>'
                        ),
                        part
                    )
                else:
                    escaped_original = re.escape(original).replace(r'\ ', r'\s+')
                    pattern = r'(?<!\w)' + escaped_original + r'(?!\w)'
                    part = re.sub(
                        pattern,
                        lambda m: (
                            m.group() if any(exc.search(m.group()) for exc in exceptions)
                            else f'<span class="{span_class}">{preserve_case(m, replacement)}</span>'
                        ),
                        part,
                        flags=re.I
                    )
            parts[i] = part
    return ''.join(parts)

def replace_expressions(input_file, regular_file, yo_no_regular_file, output_html_file, yo_dict_file, yo_variant_file):
    """Основная функция обработки текста."""
    yo_dict = load_yo_dict(yo_dict_file)
    yo_variants = load_yo_variants(yo_variant_file)

    with open(yo_no_regular_file, 'r', encoding='utf-8') as f:
        yo_no_regular_dict = {}
        for line in f:
            if '|' in line:
                parts = line.split('|', 1)
                if len(parts) == 2:
                    key, value = parts[0].strip(), parts[1].strip()
                    yo_no_regular_dict[key] = {'replacement': value, 'exceptions': []}

    regex_dict = load_dict_with_exceptions(regular_file)

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            text = f.read()
    except UnicodeDecodeError:
        print(f"{Fore.RED}Исходный текст не соответствует кодировке UTF-8.{Style.RESET_ALL}")
        sys.exit(1)

    highlighted_text = apply_replacements(text, yo_no_regular_dict, "highlight-blue")
    highlighted_text = apply_replacements(highlighted_text, regex_dict, "highlight-green")
    highlighted_text = process_yo_variants(highlighted_text, yo_variants)
    highlighted_text = replace_yo_in_text(highlighted_text, yo_dict)

    html_content = []
    for line in highlighted_text.split('\n'):
        if line.strip():
            html_content.append(f"<p>{line}</p>")
        else:
            html_content.append("<p>&nbsp;</p>")

    base_name = os.path.splitext(os.path.basename(input_file))[0]

    with open(output_html_file, 'w', encoding='utf-8') as f:
        f.write(f"""<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"
  "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">

<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>{base_name}</title>
<style>
html {{color: #000000; background-color: #FFFAFA;}}
body {{text-align : justify }}
p {{text-indent: 2em;  margin-bottom: 0em; margin-top: 0em; font-size : 110%; font-style : normal; font-weight : bold;}}
.highlight-yellow {{ background-color: yellow; }}
.highlight-green {{ background-color: lightgreen; }}
.highlight-blue {{ background-color: lightblue; }}
.highlight-orange {{ background-color: orange; }}
</style>
</head>
<body>
""")
        f.write('\n'.join(html_content))
        f.write("\n</body>\n</html>")

if __name__ == "__main__":
    input_file = "pog.txt"
    output_html_file = os.path.splitext(input_file)[0] + '_yo.html'

    try:
        replace_expressions(
            input_file,
            r"C:\Users\energ\Dropbox\Fix and Yo\Словари\green.dic",
            r"C:\Users\energ\Dropbox\Fix and Yo\Словари\blue.dic",
            output_html_file,
            r"C:\Users\energ\Dropbox\Fix and Yo\Словари\yellow.dic",
            r"C:\Users\energ\Dropbox\Fix and Yo\Словари\orange.dic"
        )
        print(f"{Fore.GREEN}Текст успешно обработан. Результат сохранён в: {output_html_file}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Ошибка: {str(e)}{Style.RESET_ALL}")
