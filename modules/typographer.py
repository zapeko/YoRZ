import re
import os
import datetime
from dataclasses import dataclass, field, fields
from colorama import Fore, Style
from . import paths

@dataclass
class ProcessStats:
    nbsp_replaced: int = 0
    zwnbsp_replaced: int = 0
    shy_removed: int = 0
    spaces_removed: int = 0
    spaces_added_around_dash: int = 0
    spaces_added_after_punct: int = 0
    dashes_replaced: int = 0
    number_word_spaces_added: int = 0
    hyphens_added_after_numbers: int = 0
    punctuation_errors_fixed: int = 0
    empty_lines_removed: int = 0
    lines_merged: int = 0

    def __add__(self, other):
        if not isinstance(other, ProcessStats): return NotImplemented
        new_stats = ProcessStats()
        for f in fields(self): setattr(new_stats, f.name, getattr(self, f.name) + getattr(other, f.name))
        return new_stats

    def __iadd__(self, other):
        if not isinstance(other, ProcessStats): return NotImplemented
        for f in fields(self): setattr(self, f.name, getattr(self, f.name) + getattr(other, f.name))
        return self

    @property
    def total(self): return sum(getattr(self, f.name) for f in fields(self))

RE_ZWNBSP = re.compile(r'\ufeff')
RE_NBSP = re.compile(r'\u00a0')
RE_IDSP = re.compile(r'\u3000')
RE_SHY = re.compile(r'\xad')
RE_DASH_START_1 = re.compile(r'^-\s+')
RE_DASH_START_2 = re.compile(r'^-(?=\S)')
RE_MDASH_START_1 = re.compile(r'^–\s+')
RE_MDASH_START_2 = re.compile(r'^–(?=\S)')
RE_DOUBLE_DASH = re.compile(r'[-–]{2,}')
RE_SPACED_DASH = re.compile(r'(?<=\s)[–-](?=\S)|(?<=\S)[–-](?=\s)|(?<=\s)[–-](?=\s)|(?<!^)[–-](?=\s|$)')
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
RE_NUM_DASH_NUM = re.compile(r'(?<=[\d])([-—])(?=[\d])')
RE_NUM_SPACE_DASH_SPACE_NUM = re.compile(r'(?<=[\d])\s+([-—])\s+(?=[\d])')
RE_NUM_SPACE_DASH_NUM = re.compile(r'(?<=[\d])\s+([-—])(?=[\d])')
RE_NUM_DASH_SPACE_NUM = re.compile(r'(?<=[\d])([-—])\s+(?=[\d])')
RE_NUM_DOT_DASH = re.compile(r'(?<=\d\.)([-—])(?=\S)')
RE_NUM_DOT_SPACE_DASH = re.compile(r'(\d\.\s+)([-—])(?=\S)')
RE_NUM_DOT_SPACE_DASH_SPACE = re.compile(r'(\d\.\s+)([-—])\s+')
RE_NUM_DASH_NUM_WORD = re.compile(r'(\d)([-—])(\d)([A-Za-zА-Яа-я])', flags=re.IGNORECASE)
RE_WORD_NUM = re.compile(r'([A-Za-zА-Яа-я])(\d)', flags=re.IGNORECASE)
RE_NUM_WORD = re.compile(r'(\d)([A-Za-zА-Яа-я])', flags=re.IGNORECASE)
RE_DIGIT_PUNCT_DIGIT = re.compile(r'\d[.,:]\d')
RE_LETTER_DOT_LETTER = re.compile(r'([A-ZА-Я]\.[A-ZА-Я]|[а-я]\.[а-я])')
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
RE_DASH_NO_SPACE_BEFORE = re.compile(r'(?<!^)(?<!\s)(—)')
RE_DASH_NO_SPACE_AFTER = re.compile(r'(—)(?=\S)')
RE_PUNCT_NO_SPACE_AFTER = re.compile(r'([,:;])(?=\S)(?![)\]}>»”*])')
RE_END_PUNCT_NO_SPACE_AFTER = re.compile(r'(?<=[.…?!])(?<!\?\.\.|!\.\.)(?=\w)(?![)\]}>»”*])')
RE_QE_NO_SPACE_AFTER = re.compile(r'([!?])(?!\s|$|[.!?…]|[)\]}>»”*])')
RE_PUNCT_SPACE_PUNCT = re.compile(r'([?!])\s+([?!.…])')
RE_MULTIPLE_SPACES = re.compile(r' {2,}')
RE_STARTING_ELLIPSIS_SPACE = re.compile(r'^…\s+')
RE_SPACED_ELLIPSIS = re.compile(r'(\s)…\s+(?=\S)')

def handle_nbsp(line, stats, options):
    if options.get('zwnbsp'):
        count_zwnbsp = len(RE_ZWNBSP.findall(line))
        if count_zwnbsp > 0:
            line = RE_ZWNBSP.sub(' ', line)
            stats.zwnbsp_replaced += count_zwnbsp
        
    if options.get('html_nbsp'):
        line, count_html_nbsp = re.subn(r'&nbsp;|&#160;', ' ', line, flags=re.IGNORECASE)
        if count_html_nbsp > 0:
            stats.nbsp_replaced += count_html_nbsp
            
    if options.get('nbsp'):
        count_nbsp = len(RE_NBSP.findall(line))
        if count_nbsp > 0:
            line = RE_NBSP.sub(' ', line)
            stats.nbsp_replaced += count_nbsp
            
        count_idsp = len(RE_IDSP.findall(line))
        if count_idsp > 0:
            line = RE_IDSP.sub(' ', line)
            stats.nbsp_replaced += count_idsp
            
    if options.get('shy'):
        count_shy = len(RE_SHY.findall(line))
        if count_shy > 0:
            line = RE_SHY.sub('', line)
            stats.shy_removed += count_shy
            
    return line

def handle_dashes_and_hyphens(line, stats, options):
    if not options.get('dashes'):
        return line
        
    keep_leading_dashes = options.get('keep_leading_dashes', False)
    protected = {}
    def protect(match, key_prefix):
        seq = match.group(0)
        key = f"__{key_prefix}_{len(protected)}__"
        protected[key] = seq
        return key

    # Protect hanging hyphens
    line = re.sub(r'(?<=[A-Za-zА-Яа-яЁё\d])-(?=\s+(?:и|или|да|либо)\b)', lambda m: protect(m, "HANG"), line, flags=re.IGNORECASE)

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
    
    for key, value in protected.items():
        line = line.replace(key, value)
        
    return line

def handle_spacing(line, stats, options, is_md=False):
    protected = {}
    def protect(match, key_prefix):
        seq = match.group(0)
        key = f"__{key_prefix}_{len(protected)}__"
        protected[key] = seq
        return key
    
    # Сначала защищаем то, что не должно меняться пробелами
    line = RE_LETTER_DOT_LETTER.sub(lambda m: protect(m, "LDL"), line)
    line = RE_DIGIT_PUNCT_DIGIT.sub(lambda m: protect(m, "DPD"), line)

    # Опция разделения букв и цифр (FB2 -> FB 2)
    if options.get('letter_digit_spaces'):
        line, count = RE_NUM_DASH_NUM_WORD.subn(r'\1\2\3 \4', line); stats.number_word_spaces_added += count
        line, count = RE_WORD_NUM.subn(r'\1 \2', line); stats.number_word_spaces_added += count
        line, count = RE_NUM_WORD.subn(r'\1 \2', line); stats.number_word_spaces_added += count

    # Основная опция очистки лишних пробелов
    if options.get('spaces'):
        original_len = len(line)
        if is_md:
            leading_spaces_match = re.match(r'^\s+', line)
            leading_spaces = leading_spaces_match.group(0) if leading_spaces_match else ""
            # Markdown soft break: two spaces at end of line. Keep them if present.
            trailing_spaces_match = re.search(r'  +$', line)
            trailing_spaces = "  " if trailing_spaces_match else ""
            
            line = line.strip()
            line = leading_spaces + line + trailing_spaces
        else:
            line = line.strip()
        stats.spaces_removed += original_len - len(line)
        
        original_len = len(line)
        if not is_md:
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

def handle_punctuation(line, stats, options):
    if not options.get('punctuation'):
        return line
        
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

def process_line(line, options, is_md=False):
    stats = ProcessStats()
    line = handle_nbsp(line, stats, options)
    
    # In Markdown, prevent changing --- to em dash
    if is_md:
        md_hr_match = re.match(r'^([-*_.])\1{2,}\s*$', line)
        if md_hr_match:
            return line, stats

    line = handle_dashes_and_hyphens(line, stats, options)
    line = handle_punctuation(line, stats, options)
    line = handle_spacing(line, stats, options, is_md)
    return line, stats

def remove_empty_lines(lines, remove_all=False):
    if remove_all:
        new_lines = [line for line in lines if line.strip() != '']
        return new_lines, len(lines) - len(new_lines)
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

def merge_lines(lines):
    if not lines: return [], 0
    merged_lines = [lines[0]]
    merge_count = 0
    i = 1
    while i < len(lines):
        prev_line_for_check = merged_lines[-1].rstrip()
        current_line_for_check = lines[i].lstrip()
        if prev_line_for_check and current_line_for_check and prev_line_for_check[-1] not in ".?!…":
            first_char = current_line_for_check[0]
            if first_char.islower() and first_char.isalpha() and not current_line_for_check.startswith(('-', '–', '—')):
                merged_lines[-1] = merged_lines[-1].rstrip() + ' ' + lines[i].lstrip()
                merge_count += 1
            else:
                merged_lines.append(lines[i])
        else:
            merged_lines.append(lines[i])
        i += 1
    return merged_lines, merge_count

def process_text_block(text_block, options, total_stats, is_md=False):
    protected_elements = {}
    
    def prot(m, prefix):
        key = f"__PROT_{prefix}_{len(protected_elements)}__"
        protected_elements[key] = m.group(0)
        return key

    if is_md:
        # Защита фрагментов кода (многострочных)
        text_block = re.sub(r'(?s)```.*?```|~~~.*?~~~', lambda m: prot(m, 'CBLK'), text_block)
        # Защита инлайн-кода
        text_block = re.sub(r'`[^`]+`', lambda m: prot(m, 'ILC'), text_block)
        
    # Защита URL-адресов
    text_block = re.sub(r'https?://[^\s>\])]+', lambda m: prot(m, 'URL'), text_block)
    # Защита email-адресов
    text_block = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', lambda m: prot(m, 'EML'), text_block)
    # Защита имен файлов, расширений и доменов (gui.py)
    text_block = re.sub(r'(?i)\b[a-z0-9_-]+\.[a-z0-9_-]+\b', lambda m: prot(m, 'FDOM'), text_block)
    # Защита HTML кодов цветов (#FF0000)
    text_block = re.sub(r'#[0-9a-fA-F]{3,8}\b', lambda m: prot(m, 'COL'), text_block)

    lines = text_block.splitlines()
    lines, empty_removed = remove_empty_lines(lines, options.get('remove_all_empty', False))
    total_stats.empty_lines_removed += empty_removed
    
    if not is_md and options.get('merge_lines'):
        lines, merged_count = merge_lines(lines)
        total_stats.lines_merged += merged_count
        
    processed_lines = []
    for line in lines:
        processed_line, line_stats = process_line(line, options, is_md)
        processed_lines.append(processed_line)
        total_stats += line_stats
        
    result = '\n'.join(processed_lines)
    
    for key, val in protected_elements.items():
        result = result.replace(key, val)
            
    return result

def process_content_with_tags(content, options, total_stats, is_md=False):
    tag_pattern = re.compile(r'(<[^>]+>)')
    parts = tag_pattern.split(content)
    for i in range(0, len(parts), 2):
        if not parts[i].strip():
            continue
            
        # Check if the text chunk consists ONLY of whitespace and HTML non-breaking spaces
        # If so, skip processing to preserve layout formatting (e.g. empty lines in EPUB)
        if re.fullmatch(r'(?i)(?:[ \t\n\r\f\v]|&nbsp;|&#160;)+', parts[i]):
            continue
            
        leading_space_match = re.match(r'(?s)^[ \t\n\r\f\v]*', parts[i])
        trailing_space_match = re.search(r'(?s)[ \t\n\r\f\v]*$', parts[i])
        leading_space = leading_space_match.group(0) if leading_space_match else ""
        trailing_space = trailing_space_match.group(0) if trailing_space_match else ""
        
        processed = process_text_block(parts[i], options, total_stats, is_md)
        
        if processed.strip():
            parts[i] = leading_space + processed.strip() + trailing_space
        else:
            parts[i] = leading_space if len(leading_space) >= len(trailing_space) else trailing_space
            
    return ''.join(parts)

def run(input_file="book.txt", output_file=None, remove_all_empty=False, keep_leading_dashes=False, quiet=False, options=None, app_version=None):
    default_options = {
        'zwnbsp': True, 'html_nbsp': True, 'nbsp': True, 'shy': True,
        'spaces': True, 'letter_digit_spaces': True, 'punctuation': True, 'dashes': True, 'merge_lines': True,
        'keep_leading_dashes': keep_leading_dashes,
        'remove_all_empty': remove_all_empty
    }

    
    if options is None:
        options = default_options
    else:
        for k, v in default_options.items():
            options.setdefault(k, v)

    is_epub = input_file.lower().endswith('.epub')
    is_fb2 = input_file.lower().endswith('.fb2')
    is_md = input_file.lower().endswith('.md')
    
    if is_md:
        options['keep_leading_dashes'] = True

    if not output_file:
        base_dir = os.path.dirname(os.path.abspath(input_file))
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        if is_epub:
            output_file = os.path.join(base_dir, base_name + '_fixed.epub')
        elif is_fb2:
            output_file = os.path.join(base_dir, base_name + '_fixed.fb2')
        elif is_md:
            output_file = os.path.join(base_dir, base_name + '_fixed.md')
        else:
            output_file = os.path.join(base_dir, base_name + '_fixed.txt')

    total_stats = ProcessStats()

    if is_epub:
        import zipfile
        from modules.epub_utils import get_ordered_infolist
        try:
            with zipfile.ZipFile(input_file, 'r') as zin:
                with zipfile.ZipFile(output_file, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
                    for item in get_ordered_infolist(zin):
                        content = zin.read(item.filename)
                        if item.filename.lower().endswith(('.html', '.xhtml', '.htm')):
                            try:
                                text = content.decode('utf-8').replace('\r\n', '\n').replace('\r', '\n')
                                processed = process_content_with_tags(text, options, total_stats)
                                zout.writestr(item, processed.encode('utf-8'))
                            except Exception as e:
                                zout.writestr(item, content)
                        elif item.filename.lower().endswith('.opf'):
                            try:
                                text_content = content.decode('utf-8')
                                today_str = datetime.date.today().isoformat()
                                
                                # Ищем существующую метку
                                meta_pattern = re.compile(r'<meta name=".*?" content="(Текст обработан программой YoRZ 2\.0 \(.*?\))"/>')
                                match = meta_pattern.search(text_content)
                                current_meta = match.group(1) if match else ""
                                new_meta_str = paths.update_metadata(current_meta, "Типограф", app_version)
                                
                                if match:
                                    text_content = text_content.replace(match.group(0), f'<meta name="{today_str}:" content="{new_meta_str}"/>')
                                else:
                                    meta_tag = f'\n    <meta name="{today_str}:" content="{new_meta_str}"/>\n'
                                    text_content = text_content.replace('</metadata>', meta_tag + '</metadata>')
                                
                                zout.writestr(item, text_content.encode('utf-8'))
                            except Exception as e:
                                zout.writestr(item, content)
                        else:
                            zout.writestr(item, content)
        except Exception as e:
            print(f"{Fore.RED}Ошибка при работе с EPUB архивом: {e}{Style.RESET_ALL}")
            return
    else:
        try:
            with open(input_file, 'rb') as f:
                raw_data = f.read()
        except Exception as e:
            print(f"{Fore.RED}Ошибка чтения {input_file}: {e}{Style.RESET_ALL}")
            return

        try: content = raw_data.decode('utf-8').replace('\r\n', '\n').replace('\r', '\n')
        except UnicodeDecodeError:
            try: content = raw_data.decode('cp1251').replace('\r\n', '\n').replace('\r', '\n')
            except UnicodeDecodeError:
                print(f"{Fore.RED}Не удалось декодировать файл. Нужен UTF-8 или CP1251.{Style.RESET_ALL}")
                return

        if is_fb2:
            processed = process_content_with_tags(content, options, total_stats, is_md)
        else:
            processed = process_text_block(content, options, total_stats, is_md)

        # Добавляем метаданные
        today_str = datetime.date.today().isoformat()
        if is_fb2:
            # Ищем существующую метку в истории
            meta_pattern = re.compile(r'<p>.*?(Текст обработан программой YoRZ 2\.0 \(.*?\))</p>')
            match = meta_pattern.search(processed)
            current_meta = match.group(1) if match else ""
            new_meta_str = paths.update_metadata(current_meta, "Типограф")
            
            history_entry = f'<p>{today_str}: {new_meta_str}</p>'
            if match:
                processed = processed.replace(match.group(0), history_entry)
            elif '</history>' in processed:
                processed = processed.replace('</history>', f'\n{history_entry}\n</history>')
            elif '</document-info>' in processed:
                meta_tag = f'\n<history>\n{history_entry}\n</history>\n'
                processed = processed.replace('</document-info>', meta_tag + '</document-info>')
            elif '</description>' in processed:
                meta_tag = f'\n<document-info>\n<history>\n{history_entry}\n</history>\n</document-info>\n'
                processed = processed.replace('</description>', meta_tag + '</description>')
        else:
            # Ищем существующую метку в MD или TXT
            if is_md:
                meta_pattern = re.compile(r'<!-- .*?(Текст обработан программой YoRZ 2\.0 \(.*?\)) -->')
            else:
                meta_pattern = re.compile(r'.*?(Текст обработан программой YoRZ 2\.0 \(.*?\))')
                
            match = meta_pattern.search(processed)
            current_meta = match.group(1) if match else ""
            new_meta_str = paths.update_metadata(current_meta, "Типограф", app_version)
            
            if is_md:
                new_entry = f'\n\n<!-- {today_str}: {new_meta_str} -->\n'
            else:
                new_entry = f'\n\n{today_str}: {new_meta_str}\n'
                
            if match:
                processed = processed.replace(match.group(0), new_entry.strip())
            else:
                processed = processed.rstrip() + new_entry

        try:
            with open(output_file, 'w', encoding='utf-8') as f_out:
                f_out.write(processed)
        except Exception as e:
            print(f"{Fore.RED}Ошибка записи: {e}{Style.RESET_ALL}")
            return

    print(f"\n{Fore.GREEN}{'#'*78}{Style.RESET_ALL}")
    if quiet:
        print(f"{Fore.GREEN}Обработка завершена.\nРезультат в: {output_file}{Style.RESET_ALL}")
    else:
        print(f"{Fore.GREEN}Обработка завершена. Всего исправлено ошибок/недочетов: {total_stats.total}.\nРезультат в: {output_file}{Style.RESET_ALL}")
        if total_stats.total > 0:
            print(f"{Fore.GREEN}{'#'*78}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Детальная статистика:{Style.RESET_ALL}")
            if total_stats.zwnbsp_replaced > 0: print(f"  - Удалено невидимых символов ZWNBSP: {total_stats.zwnbsp_replaced}")
            if total_stats.nbsp_replaced > 0: print(f"  - Заменено неразрывных/HTML пробелов: {total_stats.nbsp_replaced}")
            if total_stats.shy_removed > 0: print(f"  - Удалено мягких переносов: {total_stats.shy_removed}")
            if total_stats.spaces_removed > 0: print(f"  - Удалено лишних пробелов: {total_stats.spaces_removed}")
            if total_stats.spaces_added_around_dash > 0: print(f"  - Проставлено пробелов вокруг тире: {total_stats.spaces_added_around_dash}")
            if total_stats.spaces_added_after_punct > 0: print(f"  - Проставлено пробелов после знаков препинания: {total_stats.spaces_added_after_punct}")
            if total_stats.dashes_replaced > 0: print(f"  - Нормализовано тире: {total_stats.dashes_replaced}")
            if total_stats.number_word_spaces_added > 0: print(f"  - Разделено букв и цифр пробелом: {total_stats.number_word_spaces_added}")
            if total_stats.hyphens_added_after_numbers > 0: print(f"  - Добавлено дефисов после цифр: {total_stats.hyphens_added_after_numbers}")
            if total_stats.punctuation_errors_fixed > 0: print(f"  - Исправлено ошибок пунктуации: {total_stats.punctuation_errors_fixed}")
            if total_stats.empty_lines_removed > 0: print(f"  - Удалено лишних пустых строк: {total_stats.empty_lines_removed}")
            if total_stats.lines_merged > 0: print(f"  - Склеено разорванных строк: {total_stats.lines_merged}")

    print(f"{Fore.GREEN}{'#'*78}{Style.RESET_ALL}\n")

if __name__ == '__main__':
    run()