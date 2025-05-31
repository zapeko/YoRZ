import re
import os
from colorama import init, Fore, Style

def process_line(line):
    nbsp = '\u00A0'  # Неразрывный пробел
    zwnbsp = '\ufeff'  # Zero Width No-Break Space (ZWNBSP)

    # Замена ZWNBSP на пробел
    count_zwnbsp = line.count(zwnbsp)
    line = line.replace(zwnbsp, ' ')

    # Замена NBSP на пробел
    count_nbsp = line.count(nbsp)
    processed_line = line.replace(nbsp, ' ')

    # Общее количество заменённых неразрывных пробелов (NBSP + ZWNBSP)
    total_nbsp_replaced = count_nbsp + count_zwnbsp

    dash_replacement_count = 0
    dash_spaces = 0
    spaces_removed = 0
    number_word_spaces = 0
    hyphen_after_numbers = 0

    # Обработка дефисов и тире
    processed_line, count = re.subn(r'^-\s+', '— ', processed_line)
    dash_replacement_count += count
    processed_line, count = re.subn(r'^-(?=\S)', '— ', processed_line)
    dash_replacement_count += count
    processed_line, count = re.subn(r'^–\s+', '— ', processed_line)
    dash_replacement_count += count
    processed_line, count = re.subn(r'^–(?=\S)', '— ', processed_line)
    dash_replacement_count += count

    processed_line, count = re.subn(r'[-–]{2,}', '—', processed_line)
    dash_replacement_count += count

    processed_line, count = re.subn(r'(?<=\s)[–-](?=\S)|(?<=\S)[–-](?=\s)|(?<=\s)[–-](?=\s)|[–-](?=\s|$)', '—', processed_line)
    dash_replacement_count += count

    # Правила 8-14 (модифицированное Правило 8)
    endings = ['го','е','ей','ех','ёх','и','й','м','мь','му','ое','ой','ом','ть','ти','ух','ую','х','ых','ый','ю','я']
    endings_pattern = r'(?:{})'.format('|'.join(endings))

    # Правило 8: Исключаем окончания из замены
    processed_line, count = re.subn(
        rf'(\d)([-—])(?!{endings_pattern})([A-Za-zА-Яа-я])',
        r'\1 – \3',
        processed_line,
        flags=re.IGNORECASE
    )
    dash_replacement_count += count
    dash_spaces += count * 2

    # Правило 9-14
    processed_line, count = re.subn(r'(\d\s+)([-—])([A-Za-zА-Яа-я])', r'\1– \3', processed_line, flags=re.IGNORECASE)
    dash_replacement_count += count
    dash_spaces += count

    processed_line, count = re.subn(r'(\d\s+)([-—])(\s+[A-Za-zА-Яа-я])', r'\1–\3', processed_line, flags=re.IGNORECASE)
    dash_replacement_count += count

    processed_line, count = re.subn(r'([A-Za-zА-Яа-я])([-—])(\d)', r'\1 – \3', processed_line, flags=re.IGNORECASE)
    dash_replacement_count += count
    dash_spaces += count * 2

    processed_line, count = re.subn(r'([A-Za-zА-Яа-я])([-—])(\s+\d)', r'\1 –\3', processed_line, flags=re.IGNORECASE)
    dash_replacement_count += count
    dash_spaces += count

    processed_line, count = re.subn(r'([A-Za-zА-Яа-я]\s+)([-—])(\d)', r'\1– \3', processed_line, flags=re.IGNORECASE)
    dash_spaces += count

    processed_line, count = re.subn(r'([A-Za-zА-Яа-я]\s+)([-—])(\s+\d)', r'\1–\3', processed_line, flags=re.IGNORECASE)
    dash_replacement_count += count

    # Добавление дефиса после чисел (если его нет)
    pattern = rf'(\d)(?<![—-])({endings_pattern})(?=\b|$)'
    processed_line, count = re.subn(pattern, r'\1-\2', processed_line, flags=re.IGNORECASE)
    hyphen_after_numbers += count

    # Обработка цифровых диапазонов
    processed_line, count = re.subn(r'(?<=[\d])([-—])(?=[\d])', '–', processed_line)
    dash_replacement_count += count

    processed_line, count = re.subn(r'(?<=[\d])\s+([-—])\s+(?=[\d])', '–', processed_line)
    dash_replacement_count += count
    spaces_removed += count * 2

    processed_line, count = re.subn(r'(?<=[\d])\s+([-—])(?=[\d])', '–', processed_line)
    dash_replacement_count += count
    spaces_removed += count

    processed_line, count = re.subn(r'(?<=[\d])([-—])\s+(?=[\d])', '–', processed_line)
    dash_replacement_count += count
    spaces_removed += count

    processed_line, count5 = re.subn(r'(?<=\d\.)([-—])(?=\S)', ' – ', processed_line)
    dash_replacement_count += count5
    dash_spaces += count5 * 2

    processed_line, count6 = re.subn(r'(\d\.\s+)([-—])(?=\S)', r'\1– ', processed_line)
    dash_replacement_count += count6
    dash_spaces += count6

    processed_line, count7 = re.subn(r'(\d\.\s+)([-—])\s+', r'\1– ', processed_line)
    dash_replacement_count += count7

    # Пробелы между цифрами и буквами
    processed_line, count = re.subn(r'(\d)([-—])(\d)([A-Za-zА-Яа-я])', r'\1\2\3 \4', processed_line, flags=re.IGNORECASE)
    number_word_spaces += count

    processed_line, count = re.subn(r'([A-Za-zА-Яа-я])(\d)', r'\1 \2', processed_line, flags=re.IGNORECASE)
    number_word_spaces += count

    processed_line, count = re.subn(r'(\d)([A-Za-zА-Яа-я])', r'\1 \2', processed_line, flags=re.IGNORECASE)
    number_word_spaces += count

    # Защита последовательностей ?.. и !..
    protected = {}
    def protect(match):
        seq = match.group(0)
        key = f"__PROTECT{len(protected)}__"
        protected[key] = seq
        return key

    processed_line = re.sub(r'^[?!]\.\.(?=\s|$)', protect, processed_line)
    processed_line = re.sub(r'(?<=\S)[?!]\.\.(?=\s|$)', protect, processed_line)

    leading_nbsp = len(re.match(fr'^{nbsp}*', line).group(0))
    trailing_nbsp = len(re.search(fr'{nbsp}*$', line).group(0))
    total_start_end_nbsp = leading_nbsp + trailing_nbsp

    stripped_line = processed_line.strip()
    spaces_removed_start_end = len(processed_line) - len(stripped_line)
    processed_line = stripped_line
    spaces_removed_start_end = max(0, spaces_removed_start_end - total_start_end_nbsp)

    count1 = sum(len(m.group()) - 1 for m in re.finditer(r'\.{3,}', processed_line))
    processed_line = re.sub(r'\.{3,}', '…', processed_line)

    count2 = sum(len(m.group()) - 1 for m in re.finditer(r'…{2,}', processed_line))
    processed_line = re.sub(r'…{2,}', '…', processed_line)

    count_extra_ellipsis = sum(len(m.group()) - 1 for m in re.finditer(r'…\.+', processed_line))
    processed_line = re.sub(r'…\.+', '…', processed_line)

    count_extra_end = sum(len(m.group()) - 1 for m in re.finditer(r'(?<![\?!])\.{2,}(?![.…])', processed_line))
    processed_line = re.sub(r'(?<![\?!])\.{2,}(?![.…])', '.', processed_line)

    count_repeated_punct = sum(len(m.group()) - 1 for m in re.finditer(r'([.,;:!?])\1+', processed_line))
    processed_line = re.sub(r'([.,;:!?])\1+', r'\1', processed_line)

    original_fixes = count1 + count2 + count_extra_ellipsis + count_extra_end + count_repeated_punct

    processed_line = re.sub(r'!\?+(?![.])', '?!', processed_line)
    processed_line = re.sub(r'\?\!+(?![.])', '?!', processed_line)

    processed_line, colon_count = re.subn(
        r'([?!])([.…](?![.…])|[.…]{3,})',
        r'\1..',
        processed_line
    )

    processed_line, count4 = re.subn(r'(?<!^)(?<!\s)(—)', r' \1', processed_line)
    processed_line, count5 = re.subn(r'(—)(?=\S)', r'\1 ', processed_line)
    dash_spaces += count4 + count5

    processed_line, punct_count = re.subn(
        r'([,:;])(?=\S)(?![\]\)}>»”*])',
        r'\1 ',
        processed_line
    )
    processed_line, count3 = re.subn(r'(?<=[.…?!])(?<!\?\.\.|!\.\.)(?=\w)(?![\]\)}>»”*])', ' ', processed_line)
    punct_count += count3

    processed_line, count_qe = re.subn(
        r'([!?])(?!\s|$|[.!?…]|[\])}»”*])',
        r'\1 ',
        processed_line
    )
    punct_count += count_qe

    processed_line = re.sub(r'([?!])\s+([?!.…])', r'\1\2', processed_line)

    processed_line = re.sub(r'([?!])(?<!\.\.)\.{3,}', r'\1..', processed_line)
    processed_line = re.sub(r'([?!])…(?<!…\.\.)', r'\1..', processed_line)

    before_inline = len(processed_line)
    processed_line = re.sub(r' {2,}', ' ', processed_line)
    after_inline = len(processed_line)
    inline_spaces_removed = before_inline - after_inline

    spaces_removed += spaces_removed_start_end + inline_spaces_removed

    processed_line = re.sub(r'^…\s+', '…', processed_line)
    processed_line = re.sub(r'(\s)…\s+(?=\S)', r'\1…', processed_line)

    for key, value in protected.items():
        processed_line = processed_line.replace(key, value)

    return (processed_line, original_fixes, total_nbsp_replaced,
            spaces_removed, dash_spaces, colon_count, punct_count,
            dash_replacement_count, number_word_spaces, hyphen_after_numbers)

def remove_excessive_empty_lines(lines):
    non_empty_indices = [i for i, line in enumerate(lines) if line.strip() != '']
    if not non_empty_indices:
        return [], 0

    groups = []
    current_group = None
    for i, line in enumerate(lines):
        if line == '':
            if current_group is None:
                current_group = {'start': i, 'end': i}
            else:
                current_group['end'] = i
        else:
            if current_group is not None:
                groups.append(current_group)
                current_group = None
    if current_group is not None:
        groups.append(current_group)

    new_lines = []
    total_removed = 0
    last_pos = 0

    for group in groups:
        start = group['start']
        end = group['end']
        new_lines.extend(lines[last_pos:start])
        prev_ne = [i for i in non_empty_indices if i < start]
        next_ne = [i for i in non_empty_indices if i > end]
        if prev_ne and next_ne:
            count = end - start + 1
            if count > 1:
                new_count = count - 1
                total_removed += count - new_count
            else:
                new_count = count
            new_lines.extend([''] * new_count)
        else:
            new_lines.extend(lines[start:end + 1])
        last_pos = end + 1

    new_lines.extend(lines[last_pos:])
    return new_lines, total_removed

def remove_all_empty_lines(lines):
    new_lines = [line for line in lines if line.strip() != '']
    total_removed = len(lines) - len(new_lines)
    return new_lines, total_removed

def main():
    input_file = "book.txt"
    base, ext = os.path.splitext(input_file)
    output_file = f"{base}_fixed{ext}"

    with open(input_file, 'rb') as f:
        raw_data = f.read()

    if len(raw_data) >= 2:
        bom = raw_data[:2]
        if bom in (b'\xFF\xFE', b'\xFE\xFF'):
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

    total_original = total_nbsp = total_spaces = 0
    total_dash = total_colon = total_punct = total_empty = 0
    total_dash_replaced = 0
    total_number_word_spaces = 0
    total_hyphen_after_numbers = 0

    processed_lines = []

    for line in lines:
        (processed_line, orig, nbsp,
         spaces, dash, colon, punct, dash_replaced,
         number_word, hyphen_num) = process_line(line)
        processed_lines.append(processed_line)
        total_original += orig
        total_nbsp += nbsp
        total_spaces += spaces
        total_dash += dash
        total_colon += colon
        total_punct += punct
        total_dash_replaced += dash_replaced
        total_number_word_spaces += number_word
        total_hyphen_after_numbers += hyphen_num

    # Удаление лишних пустых строк в середине (по умолчанию)
    processed_lines, total_empty = remove_excessive_empty_lines(processed_lines)

    # Для удаления всех пустых строк раскомментируйте следующую строку:
    # processed_lines, total_empty = remove_all_empty_lines(processed_lines)

    while processed_lines and processed_lines[-1] == '':
        processed_lines.pop()

    with open(output_file, 'w', encoding='utf-8') as f_out:
        if processed_lines:
            f_out.write('\n'.join(processed_lines))

    total = sum([total_original, total_nbsp, total_spaces, total_dash,
                total_colon, total_punct, total_empty, total_dash_replaced,
                total_number_word_spaces, total_hyphen_after_numbers])

    print(f"\n{Fore.GREEN}##############################################################################{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Обработка завершена. Исправлено ошибок: {total}. Результат в: {output_file}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}##############################################################################{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Проставлено дефисов после чисел: {total_hyphen_after_numbers}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Проставлено пробелов между числами и словами: {total_number_word_spaces}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Проставлено пробелов после знаков пунктуации: {total_punct}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Проставлено пробелов вокруг тире: {total_dash}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Проставлено пар точек после ? и !: {total_colon}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Заменено (на) тире: {total_dash_replaced}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Заменено неразрывных пробелов: {total_nbsp}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Удалено лишних пробелов: {total_spaces}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Удалено лишних знаков пунктуации: {total_original}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Удалено пустых строк: {total_empty}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}##############################################################################{Style.RESET_ALL}\n\n")

if __name__ == '__main__':
    main()
