import re
import os
import argparse
from dataclasses import dataclass, field, fields
from colorama import init, Fore, Style

# -- Структура данных для статистики --
@dataclass
class ProcessStats:
    nbsp_replaced: int = 0
    zwnbsp_replaced: int = 0
    spaces_removed: int = 0
    spaces_added_around_dash: int = 0
    spaces_added_after_punct: int = 0
    dashes_replaced: int = 0
    number_word_spaces_added: int = 0
    hyphens_added_after_numbers: int = 0
    punctuation_errors_fixed: int = 0
    empty_lines_removed: int = 0

    def __add__(self, other):
        if not isinstance(other, ProcessStats):
            return NotImplemented

        new_stats = ProcessStats()
        for f in fields(self):
            setattr(new_stats, f.name, getattr(self, f.name) + getattr(other, f.name))
        return new_stats

    @property
    def total(self):
        return sum(getattr(self, f.name) for f in fields(self))

# -- Предварительно скомпилированные регулярные выражения для производительности --

# Неразрывные пробелы
RE_ZWNBSP = re.compile(r'\ufeff')
RE_NBSP = re.compile(r'\u00a0')

# Тире и дефисы
RE_DASH_START_1 = re.compile(r'^-\s+')
RE_DASH_START_2 = re.compile(r'^-(?=\S)')
RE_MDASH_START_1 = re.compile(r'^–\s+')
RE_MDASH_START_2 = re.compile(r'^–(?=\S)')
RE_DOUBLE_DASH = re.compile(r'[-–]{2,}')
RE_SPACED_DASH = re.compile(r'(?<=\s)[–-](?=\S)|(?<=\S)[–-](?=\s)|(?<=\s)[–-](?=\s)|(?<!^)[–-](?=\s|$)')

# Правила для чисел и слов
ENDINGS = ['го','е','ей','ех','ёх','и','й','м','мь','му','ое','ой','ом','ть','ти','ух','ую','х','ых','ый','ю','я']
ENDINGS_PATTERN = r'(?:{})'.format('|'.join(ENDINGS))
RE_NUM_DASH_WORD_NO_ENDING = re.compile(rf'(\d)([-—])(?!{ENDINGS_PATTERN})([A-Za-zА-Яа-я])', flags=re.IGNORECASE)
RE_NUM_SPACE_DASH_WORD = re.compile(r'(\d\s+)([-—])([A-Za-zА-Яа-я])', flags=re.IGNORECASE)
RE_NUM_SPACE_DASH_SPACE_WORD = re.compile(r'(\d\s+)([-—])(\s+[A-Za-zА-Яа-я])', flags=re.IGNORECASE)
RE_WORD_DASH_NUM = re.compile(r'([A-Za-zА-Яа-я])([-—])(\d)', flags=re.IGNORECASE)
RE_WORD_DASH_SPACE_NUM = re.compile(r'([A-Za-zА-Яа-я])([-—])(\s+\d)', flags=re.IGNORECASE)
RE_WORD_SPACE_DASH_NUM = re.compile(r'([A-Za-zА-Яа-я]\s+)([-—])(\d)', flags=re.IGNORECASE)
RE_WORD_SPACE_DASH_SPACE_NUM = re.compile(r'([A-Za-zА-Яа-я]\s+)([-—])(\s+\d)', flags=re.IGNORECASE)
RE_ADD_HYPHEN_AFTER_NUM = re.compile(rf'(\d)(?<![—-])({ENDINGS_PATTERN})(?=\b|$)', flags=re.IGNORECASE)

# Диапазоны чисел
RE_NUM_DASH_NUM = re.compile(r'(?<=[\d])([-—])(?=[\d])')
RE_NUM_SPACE_DASH_SPACE_NUM = re.compile(r'(?<=[\d])\s+([-—])\s+(?=[\d])')
RE_NUM_SPACE_DASH_NUM = re.compile(r'(?<=[\d])\s+([-—])(?=[\d])')
RE_NUM_DASH_SPACE_NUM = re.compile(r'(?<=[\d])([-—])\s+(?=[\d])')

# Тире после чисел с точкой (1. — )
RE_NUM_DOT_DASH = re.compile(r'(?<=\d\.)([-—])(?=\S)')
RE_NUM_DOT_SPACE_DASH = re.compile(r'(\d\.\s+)([-—])(?=\S)')
RE_NUM_DOT_SPACE_DASH_SPACE = re.compile(r'(\d\.\s+)([-—])\s+')

# Пробелы между числами и буквами
RE_NUM_DASH_NUM_WORD = re.compile(r'(\d)([-—])(\d)([A-Za-zА-Яа-я])', flags=re.IGNORECASE)
RE_WORD_NUM = re.compile(r'([A-Za-zА-Яа-я])(\d)', flags=re.IGNORECASE)
RE_NUM_WORD = re.compile(r'(\d)([A-Za-zА-Яа-я])', flags=re.IGNORECASE)

# Шаблоны цифра.цифра (для защиты от изменений пробелов)
RE_DIGIT_DOT_DIGIT = re.compile(r'\d[.,:]\d')

# Пунктуация
RE_MULTIPLE_DOTS = re.compile(r'\.{3,}')
RE_MULTIPLE_ELLIPSIS = re.compile(r'…{2,}')
RE_ELLIPSIS_DOTS = re.compile(r'…\.+')
RE_EXTRA_END_DOTS = re.compile(r'(?<![?!])\.{2,}(?![.…])')
RE_REPEATED_PUNCT = re.compile(r'([.,;:!?])\1+')
RE_INVERTED_PUNCT = re.compile(r'\!\?+(?![.])')
RE_INVERTED_PUNCT_2 = re.compile(r'\?\!+(?![.])')
RE_PUNCT_DOTS = re.compile(r'([?!])([.…](?![.…])|[.…]{3,})')
RE_PUNCT_ELLIPSIS_1 = re.compile(r'([?!])(?<!\.\.)\.{3,}')
RE_PUNCT_ELLIPSIS_2 = re.compile(r'([?!])…(?<!…\.\.)')

# Пробелы вокруг знаков препинания
RE_DASH_NO_SPACE_BEFORE = re.compile(r'(?<!^)(?<!\s)(—)')
RE_DASH_NO_SPACE_AFTER = re.compile(r'(—)(?=\S)')
RE_PUNCT_NO_SPACE_AFTER = re.compile(r'([,:;])(?=\S)(?![)\]}>»”*])')
RE_END_PUNCT_NO_SPACE_AFTER = re.compile(r'(?<=[.…?!])(?<!\?\.\.|!\.\.)(?=\w)(?![)\]}>»”*])')
RE_QE_NO_SPACE_AFTER = re.compile(r'([!?])(?!\s|$|[.!?…]|[)\]}>»”*])')
RE_PUNCT_SPACE_PUNCT = re.compile(r'([?!])\s+([?!.…])')

# Общие пробелы
RE_MULTIPLE_SPACES = re.compile(r' {2,}')
RE_STARTING_ELLIPSIS_SPACE = re.compile(r'^…\s+')
RE_SPACED_ELLIPSIS = re.compile(r'(\s)…\s+(?=\S)')

# -- Вспомогательные функции --

def handle_nbsp(line: str, stats: ProcessStats) -> str:
    """Заменяет неразрывные пробелы на обычные."""
    count_zwnbsp = len(RE_ZWNBSP.findall(line))
    if count_zwnbsp > 0:
        line = RE_ZWNBSP.sub(' ', line)
        stats.zwnbsp_replaced += count_zwnbsp

    count_nbsp = len(RE_NBSP.findall(line))
    if count_nbsp > 0:
        line = RE_NBSP.sub(' ', line)
        stats.nbsp_replaced += count_nbsp

    return line

def handle_dashes_and_hyphens(line: str, stats: ProcessStats, keep_leading_dashes: bool) -> str:
    """Преобразует дефисы в длинные тире и стандартизирует их."""
    if not keep_leading_dashes:
        line, count = RE_DASH_START_1.subn('— ', line); stats.dashes_replaced += count
        line, count = RE_DASH_START_2.subn('— ', line); stats.dashes_replaced += count
        line, count = RE_MDASH_START_1.subn('— ', line); stats.dashes_replaced += count
        line, count = RE_MDASH_START_2.subn('— ', line); stats.dashes_replaced += count

    line, count = RE_DOUBLE_DASH.subn('—', line); stats.dashes_replaced += count
    line, count = RE_SPACED_DASH.subn('—', line); stats.dashes_replaced += count

    line, count = RE_NUM_DASH_WORD_NO_ENDING.subn(r'\1 – \3', line); stats.dashes_replaced += count; stats.spaces_added_around_dash += count * 2
    line, count = RE_NUM_SPACE_DASH_WORD.subn(r'\1– \3', line); stats.dashes_replaced += count; stats.spaces_added_around_dash += count
    line, count = RE_NUM_SPACE_DASH_SPACE_WORD.subn(r'\1–\3', line); stats.dashes_replaced += count
    line, count = RE_WORD_DASH_NUM.subn(r'\1 – \3', line); stats.dashes_replaced += count; stats.spaces_added_around_dash += count * 2
    line, count = RE_WORD_DASH_SPACE_NUM.subn(r'\1 –\3', line); stats.dashes_replaced += count; stats.spaces_added_around_dash += count
    line, count = RE_WORD_SPACE_DASH_NUM.subn(r'\1– \3', line); stats.spaces_added_around_dash += count
    line, count = RE_WORD_SPACE_DASH_SPACE_NUM.subn(r'\1–\3', line); stats.dashes_replaced += count

    line, count = RE_ADD_HYPHEN_AFTER_NUM.subn(r'\1-\2', line); stats.hyphens_added_after_numbers += count

    line, count = RE_NUM_DASH_NUM.subn('–', line); stats.dashes_replaced += count
    line, count = RE_NUM_SPACE_DASH_SPACE_NUM.subn('–', line); stats.dashes_replaced += count; stats.spaces_removed += count * 2
    line, count = RE_NUM_SPACE_DASH_NUM.subn('–', line); stats.dashes_replaced += count; stats.spaces_removed += count
    line, count = RE_NUM_DASH_SPACE_NUM.subn('–', line); stats.dashes_replaced += count; stats.spaces_removed += count

    line, count = RE_NUM_DOT_DASH.subn(' – ', line); stats.dashes_replaced += count; stats.spaces_added_around_dash += count * 2
    line, count = RE_NUM_DOT_SPACE_DASH.subn(r'\1– ', line); stats.dashes_replaced += count; stats.spaces_added_around_dash += count
    line, count = RE_NUM_DOT_SPACE_DASH_SPACE.subn(r'\1– ', line); stats.dashes_replaced += count

    return line

def handle_spacing(line: str, stats: ProcessStats) -> str:
    """Устраняет различные проблемы с пробелами."""
    protected = {}
    def protect(match):
        seq = match.group(0)
        key = f"__DIGIT_DOT_DIGIT_{len(protected)}__"
        protected[key] = seq
        return key
    line = RE_DIGIT_DOT_DIGIT.sub(protect, line)

    line, count = RE_NUM_DASH_NUM_WORD.subn(r'\1\2\3 \4', line); stats.number_word_spaces_added += count
    line, count = RE_WORD_NUM.subn(r'\1 \2', line); stats.number_word_spaces_added += count
    line, count = RE_NUM_WORD.subn(r'\1 \2', line); stats.number_word_spaces_added += count

    original_len = len(line)
    line = line.strip()
    stats.spaces_removed += original_len - len(line)

    original_len = len(line)
    line = RE_MULTIPLE_SPACES.sub(' ', line)
    stats.spaces_removed += original_len - len(line)

    line, count = RE_DASH_NO_SPACE_BEFORE.subn(r' \1', line); stats.spaces_added_around_dash += count
    line, count = RE_DASH_NO_SPACE_AFTER.subn(r'\1 ', line); stats.spaces_added_around_dash += count

    line, count = RE_PUNCT_NO_SPACE_AFTER.subn(r'\1 ', line); stats.spaces_added_after_punct += count
    line, count = RE_END_PUNCT_NO_SPACE_AFTER.subn(' ', line); stats.spaces_added_after_punct += count
    line, count = RE_QE_NO_SPACE_AFTER.subn(r'\1 ', line); stats.spaces_added_after_punct += count

    line = RE_PUNCT_SPACE_PUNCT.sub(r'\1\2', line)

    line = RE_STARTING_ELLIPSIS_SPACE.sub('…', line)
    line = RE_SPACED_ELLIPSIS.sub(r'\1…', line)

    for key, value in protected.items():
        line = line.replace(key, value)

    return line

def handle_punctuation(line: str, stats: ProcessStats) -> str:
    """Исправляет распространенные ошибки пунктуации."""
    protected = {}
    def protect(match):
        seq = match.group(0)
        key = f"__PROTECT{len(protected)}__"
        protected[key] = seq
        return key
    line = re.sub(r'^[?!]\.\.(?=\s|$)', protect, line)
    line = re.sub(r'(?<=\S)[?!]\.\.(?=\s|$)', protect, line)

    line, count = RE_MULTIPLE_DOTS.subn('…', line); stats.punctuation_errors_fixed += sum(len(m.group()) - 1 for m in re.finditer(r'\.{3,}', line))
    line, count = RE_MULTIPLE_ELLIPSIS.subn('…', line); stats.punctuation_errors_fixed += sum(len(m.group()) - 1 for m in re.finditer(r'…{2,}', line))
    line, count = RE_ELLIPSIS_DOTS.subn('…', line); stats.punctuation_errors_fixed += sum(len(m.group()) - 1 for m in re.finditer(r'…\.+', line))
    line, count = RE_EXTRA_END_DOTS.subn('.', line); stats.punctuation_errors_fixed += sum(len(m.group()) - 1 for m in re.finditer(r'(?<![?!])\.{2,}(?![.…])', line))

    line, count = RE_REPEATED_PUNCT.subn(r'\1', line); stats.punctuation_errors_fixed += sum(len(m.group()) - 1 for m in re.finditer(r'([.,;:!?])\1+', line))
    line = RE_INVERTED_PUNCT.sub('?!', line)
    line = RE_INVERTED_PUNCT_2.sub('?!', line)

    line, count = RE_PUNCT_DOTS.subn(r'\1..', line); stats.punctuation_errors_fixed += count
    line = RE_PUNCT_ELLIPSIS_1.sub(r'\1..', line)
    line = RE_PUNCT_ELLIPSIS_2.sub(r'\1..', line)

    for key, value in protected.items():
        line = line.replace(key, value)

    return line

def process_line(line: str, keep_leading_dashes: bool) -> tuple[str, ProcessStats]:
    """
    Обрабатывает одну строку текста, применяя типографские правила.
    Возвращает обработанную строку и статистику изменений.
    """
    stats = ProcessStats()

    processed_line = handle_nbsp(line, stats)
    processed_line = handle_dashes_and_hyphens(processed_line, stats, keep_leading_dashes)
    processed_line = handle_punctuation(processed_line, stats)
    processed_line = handle_spacing(processed_line, stats)

    return processed_line, stats

def remove_empty_lines(lines: list[str], remove_all: bool = False) -> tuple[list[str], int]:
    """Удаляет все или лишние пустые строки из списка строк."""
    if remove_all:
        new_lines = [line for line in lines if line.strip() != '']
        removed_count = len(lines) - len(new_lines)
        return new_lines, removed_count

    new_lines = []
    in_block = False
    for line in lines:
        if line.strip() != '':
            new_lines.append(line)
            in_block = True
        elif in_block:
            new_lines.append('')
            in_block = False

    while new_lines and new_lines[-1].strip() == '':
        new_lines.pop()

    return new_lines, len(lines) - len(new_lines)

def main():
    """Основная функция для запуска скрипта."""
    init(autoreset=True)

    parser = argparse.ArgumentParser(
        description="Типографская обработка текстового файла.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("input_file", help="Путь к исходному файлу.")
    parser.add_argument("-o", "--output", help="Путь к файлу для сохранения результата (по умолчанию: <input>_fixed.txt).")
    parser.add_argument(
        "--remove-all-empty",
        action="store_true",
        help="Удалить все пустые строки, а не только лишние."
    )
    parser.add_argument(
        "--keep-leading-dashes",
        action="store_true",
        help="Не заменять дефисы в начале строки на тире (для прямой речи)."
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Тихий режим. Не выводить подробную статистику в консоль."
    )
    args = parser.parse_args()

    input_file = args.input_file
    output_file = args.output if args.output else f"{os.path.splitext(input_file)[0]}_fixed.txt"

    try:
        with open(input_file, 'rb') as f:
            raw_data = f.read()
    except FileNotFoundError:
        print(f"{Fore.RED}Ошибка: Файл не найден по пути: {input_file}{Style.RESET_ALL}")
        return
    except IOError as e:
        print(f"{Fore.RED}Ошибка чтения файла: {e}{Style.RESET_ALL}")
        return

    content = ""
    if len(raw_data) >= 2 and raw_data[:2] in (b'\xFF\xFE', b'\xFE\xFF'):
        print(f"{Fore.RED}Ошибка: файл в кодировке UTF-16, которая не поддерживается. Используйте UTF-8 или CP1251.{Style.RESET_ALL}")
        return
    try:
        content = raw_data.decode('utf-8')
    except UnicodeDecodeError:
        try:
            content = raw_data.decode('cp1251')
        except UnicodeDecodeError:
            print(f"{Fore.RED}Ошибка: не удалось декодировать файл. Поддерживаемые кодировки: UTF-8, CP1251.{Style.RESET_ALL}")
            return

    lines = content.splitlines()
    total_stats = ProcessStats()
    processed_lines = []

    for line in lines:
        processed_line, line_stats = process_line(line, args.keep_leading_dashes)
        processed_lines.append(processed_line)
        total_stats += line_stats

    processed_lines, empty_removed = remove_empty_lines(processed_lines, args.remove_all_empty)
    total_stats.empty_lines_removed = empty_removed

    try:
        with open(output_file, 'w', encoding='utf-8') as f_out:
            f_out.write('\n'.join(processed_lines))
    except IOError as e:
        print(f"{Fore.RED}Ошибка записи в файл {output_file}: {e}{Style.RESET_ALL}")
        return

    print(f"\n{Fore.GREEN}{'#'*78}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Обработка завершена. Исправлено ошибок: {total_stats.total}. Результат в: {output_file}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'#'*78}{Style.RESET_ALL}")

    if not args.quiet:
        print(f"{Fore.YELLOW}Проставлено дефисов после чисел: {total_stats.hyphens_added_after_numbers}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Проставлено пробелов между числами и словами: {total_stats.number_word_spaces_added}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Проставлено пробелов после знаков пунктуации: {total_stats.spaces_added_after_punct}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Проставлено пробелов вокруг тире: {total_stats.spaces_added_around_dash}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Заменено дефисов на тире: {total_stats.dashes_replaced}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Заменено неразрывных пробелов (NBSP): {total_stats.nbsp_replaced}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Заменено неразрывных пробелов (ZWNBSP): {total_stats.zwnbsp_replaced}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Удалено лишних пробелов: {total_stats.spaces_removed}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Исправлено ошибок пунктуации: {total_stats.punctuation_errors_fixed}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Удалено пустых строк: {total_stats.empty_lines_removed}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'#'*78}{Style.RESET_ALL}\n")


if __name__ == '__main__':
    main()
