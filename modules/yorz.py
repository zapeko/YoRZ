import re
import os
import zipfile
import sys
import unicodedata
import base64
import mimetypes
from colorama import Fore, Style

def remove_diacritics(text):
    nfd_text = unicodedata.normalize("NFD", text)
    result_chars = []
    i = 0
    while i < len(nfd_text):
        ch = nfd_text[i]
        if unicodedata.category(ch) != "Mn":
            cluster = [ch]
            i += 1
            while i < len(nfd_text) and unicodedata.category(nfd_text[i]) == "Mn":
                cluster.append(nfd_text[i])
                i += 1
            if ch.lower() == "е" and "\u0308" in cluster[1:]:
                result_chars.extend(cluster)
            elif ch.lower() == "и" and "\u0306" in cluster[1:]:
                result_chars.extend(cluster)
            else:
                result_chars.append(ch)
        else:
            i += 1
    return unicodedata.normalize("NFC", "".join(result_chars))

def load_yo_dict(file_path):
    yo_dict = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        for line_num, line in enumerate(file, 1):
            line = line.strip()
            if not line or '|' not in line: continue
            main_part, *rest = line.split('(', 1)
            parts = main_part.split('|', 1)
            if len(parts) < 2: continue
            key, replace = parts[0].strip(), parts[1].strip()

            pattern_parts = []
            wildcard_groups = []
            current_group = 1
            for segment in re.split(r'(\\w[\*\+])', key):
                if segment in (r'\w*', r'\w+'):
                    quant = '*' if segment == r'\w*' else '+'
                    pattern_parts.append(f'([\\w\\u0300-\\u036F]{quant})')
                    wildcard_groups.append(current_group)
                    current_group += 1
                else:
                    pattern_parts.append(re.escape(segment))
            pattern_str = r'(?<![\w\u0300-\u036F])' + ''.join(pattern_parts) + r'(?![\w\u0300-\u036F])'

            parts_repl = re.split(r'(\\w[\*\+])', replace)
            for i in range(1, len(parts_repl), 2):
                if parts_repl[i] in (r'\w*', r'\w+'):
                    try: parts_repl[i] = f'\\{wildcard_groups.pop(0)}'
                    except IndexError: break
            replacement = ''.join(parts_repl)

            try: pattern = re.compile(pattern_str, re.I)
            except re.error: continue

            exc_patterns = []
            exc_set = set()
            if rest:
                exc_part = rest[0].split(')', 1)[0].strip()
                for exc in exc_part.split(':'):
                    exc_clean = exc.strip().lower()
                    exc_set.add(exc_clean)
                    exc_re = re.sub(r'\\(w[\*\+])', r'\\\1', exc.strip())
                    try: exc_patterns.append(re.compile(fr'\b{exc_re}\b', re.I))
                    except re.error: pass

            yo_dict[key] = {
                'replace': replacement,
                'exceptions_compiled': exc_patterns,
                'exceptions_set': exc_set,
                'pattern': pattern,
                'priority': len(key.replace(r'\w', ''))
            }
    return yo_dict

def preserve_case(match, replacement):
    original_text = match.group()
    original_words = re.findall(r'\w+|\W+', original_text)
    replacement_words = re.findall(r'\w+|\W+', replacement)
    
    if len(original_words) == len(replacement_words):
        result = []
        for orig_word, repl_word in zip(original_words, replacement_words):
            if not any(c.isalpha() for c in orig_word) or not any(c.isalpha() for c in repl_word):
                result.append(repl_word)
            elif orig_word.isupper() and any(c.isalpha() for c in orig_word):
                result.append(repl_word.upper())
            elif orig_word.istitle() and any(c.isalpha() for c in orig_word):
                result.append(repl_word.title())
            else:
                result.append(repl_word.lower())
        return ''.join(result)
    else:
        # Handling cases where number of tokens changed (e.g. "яркозеленой" -> "ярко-зелёной")
        if not any(c.isalpha() for c in original_text):
            return replacement
            
        alpha_orig = [w for w in original_words if any(c.isalpha() for c in w)]
        if not alpha_orig:
            return replacement
            
        first_word = alpha_orig[0]
        
        if original_text.isupper():
            return replacement.upper()
        
        if first_word.istitle() or first_word.isupper():
            if replacement:
                # Need to find the first letter to capitalize, preserving potential leading non-alpha
                match_alpha = re.search(r'[a-zA-Zа-яА-ЯёЁ]', replacement)
                if match_alpha:
                    idx = match_alpha.start()
                    return replacement[:idx] + replacement[idx].upper() + replacement[idx+1:].lower()
                else:
                    return replacement[0].upper() + replacement[1:].lower()
            return replacement
            
        return replacement.lower()

def replace_yo_in_text(text, sorted_yo_data):
    tag_pattern = re.compile(r'(<[^>]+>)')
    parts = tag_pattern.split(text)
    for i in range(0, len(parts), 2):
        if not parts[i].strip(): continue
        for data in sorted_yo_data:
            parts[i] = data['pattern'].sub(
                lambda m, d=data: (
                    m.group() if remove_diacritics(m.group()).lower() in d['exceptions_set']
                    else f'<yorz class="highlight-yellow">{preserve_case(m, m.expand(d["replace"]))}</yorz>'
                ), parts[i]
            )
    return ''.join(parts)

def load_yo_variants(file_path):
    yo_variants = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        for line_num, line in enumerate(file, 1):
            line = line.strip()
            if not line or '|' not in line: continue
            main_part, *rest = line.split('(', 1)
            parts = main_part.split('|', 1)
            if len(parts) < 2: continue
            original, replacement = parts[0].strip(), parts[1].strip()

            pattern_parts = []
            wildcard_groups = []
            current_group = 1
            for segment in re.split(r'(\\w[\*\+])', original):
                if segment in (r'\w*', r'\w+'):
                    quant = '*' if segment == r'\w*' else '+'
                    pattern_parts.append(f'([\\w\\u0300-\\u036F]{quant})')
                    wildcard_groups.append(current_group)
                    current_group += 1
                else:
                    pattern_parts.append(re.escape(segment))
            pattern_str = r'(?<![\w\u0300-\u036F])' + ''.join(pattern_parts) + r'(?![\w\u0300-\u036F])'

            parts_repl = re.split(r'(\\w[\*\+])', replacement)
            for i in range(1, len(parts_repl), 2):
                if parts_repl[i] in (r'\w*', r'\w+'):
                    try: parts_repl[i] = f'\\{wildcard_groups.pop(0)}'
                    except IndexError: break
            final_repl = ''.join(parts_repl)

            try: pattern = re.compile(pattern_str, re.I)
            except re.error: continue

            exc_patterns = []
            if rest:
                exc_part = rest[0].split(')', 1)[0].strip()
                for exc in exc_part.split(':'):
                    exc = re.sub(r'\\(w[\*\+])', r'\\\1', exc.strip())
                    try: exc_patterns.append(re.compile(fr'\b{exc}\b', re.I))
                    except re.error: pass

            yo_variants[pattern] = {'replacement': final_repl, 'exceptions': exc_patterns}
    return yo_variants

def process_yo_variants(text, yo_variants, replace_all_choices, global_line_offset=0):
    lines = text.split('\n')
    tag_pattern = re.compile(r'(<yorz[^>]*>.*?</yorz>|<[^>]+>)', re.IGNORECASE | re.DOTALL)

    for line_num, line in enumerate(lines):
        parts = tag_pattern.split(line)
        new_parts = parts.copy()
        for part_idx in range(0, len(parts), 2):
            part = parts[part_idx]
            if not part.strip(): continue
            words = re.split(r'([^\w\u0300-\u036F]+)', part)
            for word_idx in range(len(words)):
                word = words[word_idx]
                if not word or not re.match(r'[\w\u0300-\u036F]+', word): continue
                replaced = False
                for pattern in yo_variants:
                    if pattern in replace_all_choices:
                        match = pattern.fullmatch(word)
                        if match and not any(exc.search(remove_diacritics(word)) for exc in yo_variants[pattern]['exceptions']):
                            new_word = preserve_case(match, replace_all_choices[pattern])
                            words[word_idx] = f'<yorz class="highlight-orange">{new_word}</yorz>'
                            new_parts[part_idx] = ''.join(words)
                            replaced = True
                            break
                if replaced: continue

                for pattern, data in yo_variants.items():
                    match = pattern.fullmatch(word)
                    if not match: continue
                    if any(exc.search(remove_diacritics(word)) for exc in data['exceptions']): continue

                    base_word = match.group()
                    yo_word = match.expand(data['replacement'])
                    if base_word.lower() == yo_word.lower(): break

                    temp_words = words.copy()
                    temp_words[word_idx] = Fore.YELLOW + word + Style.RESET_ALL
                    temp_parts = parts.copy()
                    temp_parts[part_idx] = ''.join(temp_words)
                    highlighted_line = re.sub(r'<[^>]*>', '', ''.join(temp_parts))

                    import builtins
                    is_gui = hasattr(builtins, 'gui_custom_input')

                    if is_gui:
                        yellow_idx = highlighted_line.find(Fore.YELLOW)
                        if yellow_idx != -1:
                            start = max(0, yellow_idx - 150)
                            end = highlighted_line.find(Style.RESET_ALL, yellow_idx)
                            if end != -1:
                                end = min(len(highlighted_line), end + len(Style.RESET_ALL) + 150)
                            else:
                                end = min(len(highlighted_line), yellow_idx + 150)
                            
                            prefix = "... " if start > 0 else ""
                            suffix = " ..." if end < len(highlighted_line) else ""
                            highlighted_line = prefix + highlighted_line[start:end] + suffix

                    print(f"\n{Fore.CYAN}Строка {global_line_offset + line_num + 1}:{Style.RESET_ALL}")
                    print(highlighted_line)
                    
                    if not is_gui:
                        print(f"{Fore.GREEN}Варианты: 1 или 3 >>> {base_word.lower()} | {yo_word.lower()} <<< 2 или 4")

                    try:
                        if is_gui:
                            labels = [f"1 ({base_word.lower()})", f"2 ({yo_word.lower()})", f"3 ({base_word.lower()} везде)", f"4 ({yo_word.lower()} везде)", "Пропустить (Enter)"]
                            choice_input = builtins.gui_custom_input("", labels).strip()
                            if globals().get('SHOULD_STOP', False):
                                raise KeyboardInterrupt()
                        else:
                            choice_input = input("Выберите [1/2/3,4-везде/Enter-пропустить]: ").strip()
                    except KeyboardInterrupt:
                        raise KeyboardInterrupt()

                    new_word = word
                    if choice_input:
                        choice = choice_input[0]
                        if choice == '1': new_word = base_word
                        elif choice == '2': new_word = yo_word
                        elif choice == '3':
                            replace_all_choices[pattern] = base_word
                            new_word = base_word
                        elif choice == '4':
                            replace_all_choices[pattern] = yo_word
                            new_word = yo_word
                        else:
                            print(f"{Fore.RED}Неверный ввод. Пропускаем.{Style.RESET_ALL}")
                    new_word = preserve_case(match, new_word)
                    words[word_idx] = f'<yorz class="highlight-orange">{new_word}</yorz>'
                    new_parts[part_idx] = ''.join(words)
                    break
        lines[line_num] = ''.join(new_parts)
    return '\n'.join(lines)

def load_dict_with_exceptions(file_path):
    replacements_dict = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        for line_num, line in enumerate(file, 1):
            line = line.strip()
            if not line or '|' not in line: continue
            main_part, *rest = line.split('(', 1)
            parts = main_part.split('|', 1)
            if len(parts) < 2: continue
            original, replacement = parts[0].strip(), parts[1].strip()

            exc_set = set()
            if rest:
                exc_part = rest[0].split(')', 1)[0].strip()
                for exc in exc_part.split(':'):
                    exc_clean = exc.strip().lower()
                    exc_set.add(exc_clean)

            regex = None
            fixed_replacement = replacement
            if r'\w*' in original or r'\w+' in original:
                pattern_parts = []
                wildcard_groups = []
                current_group = 1
                for segment in re.split(r'(\\w[\*\+])', original):
                    if segment in (r'\w*', r'\w+'):
                        quant = '*' if segment == r'\w*' else '+'
                        pattern_parts.append(f'([\\w\\u0300-\\u036F]{quant})')
                        wildcard_groups.append(current_group)
                        current_group += 1
                    else:
                        pattern_parts.append(re.escape(segment))
                pattern_str = r'(?<![\w\u0300-\u036F])' + ''.join(pattern_parts) + r'(?![\w\u0300-\u036F])'

                repl_parts = re.split(r'(\\w[\*\+])', replacement)
                for j in range(1, len(repl_parts), 2):
                    if repl_parts[j] in (r'\w*', r'\w+'):
                        try: repl_parts[j] = f'\\{wildcard_groups.pop(0)}'
                        except IndexError: break
                fixed_replacement = ''.join(repl_parts)
                try:
                    regex = re.compile(pattern_str, re.I)
                except re.error:
                    pass
            else:
                escaped_original = re.escape(original).replace(r'\ ', r'\s+')
                pattern_str = r'(?<![\w\u0300-\u036F])' + escaped_original + r'(?![\w\u0300-\u036F])'
                try:
                    regex = re.compile(pattern_str, re.I)
                except re.error:
                    pass

            replacements_dict[original] = {'replacement': replacement, 'fixed_replacement': fixed_replacement, 'exceptions_set': exc_set, 'regex': regex}
    return replacements_dict

def apply_replacements(text, replacements_dict, span_class):
    tag_pattern = re.compile(r'(<yorz[^>]*>.*?</yorz>|<[^>]+>)', re.IGNORECASE | re.DOTALL)
    parts = tag_pattern.split(text)
    for i in range(0, len(parts), 2):
        if not parts[i].strip(): continue
        for original, data in replacements_dict.items():
            regex = data.get('regex')
            if not regex: continue
            parts[i] = regex.sub(
                lambda m, d=data: (
                    m.group() if remove_diacritics(m.group()).lower() in d['exceptions_set']
                    else f'<yorz class="{span_class}">{preserve_case(m, m.expand(d["fixed_replacement"]))}</yorz>'
                ), parts[i]
            )
    return ''.join(parts)

from . import paths
SHOULD_STOP = False

def get_html_template(title, body_content):
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{
            background-color: #f0f2f5;
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .container {{
            max-width: 900px;
            width: 100%;
        }}
        .chapter-card {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            padding: 40px;
            overflow-wrap: break-word;
        }}
        .chapter-card h1, .chapter-card h2, .chapter-card h3 {{
            color: #1a73e8;
            text-align: center;
            margin-top: 0;
            font-weight: 600;
        }}
        img {{
            max-width: 100%;
            height: auto;
            display: block;
            margin: 20px auto;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }}
        p {{
            margin: 0.8em 0;
            text-align: justify;
            font-size: 110%;
        }}
        a {{
            color: #1a73e8;
            text-decoration: none;
            border-bottom: 1px dotted #1a73e8;
        }}
        a:hover {{
            color: #0d47a1;
            border-bottom-style: solid;
        }}
        .tooltip {{
            position: relative;
            display: inline-block;
            border-bottom: 1px dotted #1a73e8;
            color: #1a73e8;
            cursor: help;
        }}
        .tooltip .tooltiptext {{
            visibility: hidden;
            width: 250px;
            background-color: #333;
            color: #fff;
            text-align: center;
            border-radius: 6px;
            padding: 10px;
            position: absolute;
            z-index: 10;
            bottom: 125%;
            left: 50%;
            margin-left: -125px;
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 0.85em;
            line-height: 1.4;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            pointer-events: none;
        }}
        .tooltip:hover .tooltiptext {{
            visibility: visible;
            opacity: 1;
        }}
        .highlight-yellow {{ background-color: #fff176; padding: 2px 0; border-radius: 3px; }}
        .highlight-green {{ background-color: #a5d6a7; padding: 2px 0; border-radius: 3px; }}
        .highlight-blue {{ background-color: #90caf9; padding: 2px 0; border-radius: 3px; }}
        .highlight-orange {{ background-color: #ffcc80; padding: 2px 0; border-radius: 3px; }}
        
        @media (max-width: 600px) {{
            body {{ padding: 10px; }}
            .chapter-card {{ padding: 20px; border-radius: 8px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        {body_content}
    </div>
</body>
</html>"""

def replace_expressions(input_file="book.txt", regular_file=None, yo_no_regular_file=None, output_file=None, yo_dict_file=None, yo_variant_file=None, app_version=None):
    if regular_file is None: regular_file = paths.get_path("dictionaries/green.dic")
    if yo_no_regular_file is None: yo_no_regular_file = paths.get_path("dictionaries/blue.dic")
    if yo_dict_file is None: yo_dict_file = paths.get_path("dictionaries/yellow.dic")
    if yo_variant_file is None: yo_variant_file = paths.get_path("dictionaries/orange.dic")

    global SHOULD_STOP
    SHOULD_STOP = False
    import builtins
    import json
    
    # Сохраняем сессию в ту же папку, где находится исходный файл
    session_file = os.path.join(os.path.dirname(os.path.abspath(input_file)), f".{os.path.basename(input_file)}.yorz_session")
    session_data = {'processed_index': 0, 'replace_all_choices': {}, 'html_contents': []}
    
    if os.path.exists(session_file):
        print(f"\n{Fore.YELLOW}Найден незаконченный процесс для этого файла.{Style.RESET_ALL}")
        if hasattr(builtins, 'gui_custom_input'):
            ans = builtins.gui_custom_input("Продолжить с места остановки? ", ["1 (Да, продолжить)", "2 (Нет, начать заново)"])
        else:
            ans = input("Продолжить с места остановки? [1 - Да / 2 - Нет]: ")
        
        if ans and str(ans)[0] == '1':
            try:
                with open(session_file, 'r', encoding='utf-8') as sf:
                    session_data = json.load(sf)
            except Exception as e:
                print(f"{Fore.RED}Не удалось загрузить сессию: {e}{Style.RESET_ALL}")
        else:
            os.remove(session_file)
            if input_file.lower().endswith('.epub'):
                base_dir = os.path.dirname(os.path.abspath(input_file))
                base_name = os.path.splitext(os.path.basename(input_file))[0]
                tmp_epub = os.path.join(base_dir, base_name + '_yo.epub.tmp')
                if os.path.exists(tmp_epub): os.remove(tmp_epub)

    yo_dict = load_yo_dict(yo_dict_file)
    sorted_yo_data = sorted(yo_dict.values(), key=lambda x: (-x['priority'], str(x['pattern'])))
    yo_variants = load_yo_variants(yo_variant_file)

    yo_no_regular_dict = load_dict_with_exceptions(yo_no_regular_file) if os.path.exists(yo_no_regular_file) else {}

    regex_dict = load_dict_with_exceptions(regular_file) if os.path.exists(regular_file) else {}

    replace_all_choices_str = session_data.get('replace_all_choices', {})
    replace_all_choices = {}
    for pat_str, rep in replace_all_choices_str.items():
        for p in yo_variants:
            if getattr(p, 'pattern', p) == pat_str or str(p) == pat_str:
                replace_all_choices[p] = rep
                break

    def save_session():
        session_data['replace_all_choices'] = {getattr(p, 'pattern', str(p)): r for p, r in replace_all_choices.items()}
        with open(session_file, 'w', encoding='utf-8') as sf:
            json.dump(session_data, sf, ensure_ascii=False, indent=2)

    def process_text_chunk(text_chunk, global_line_offset=0):
        if SHOULD_STOP: raise KeyboardInterrupt()
        text_chunk = apply_replacements(text_chunk, yo_no_regular_dict, "highlight-blue")
        if SHOULD_STOP: raise KeyboardInterrupt()
        text_chunk = apply_replacements(text_chunk, regex_dict, "highlight-green")
        if SHOULD_STOP: raise KeyboardInterrupt()
        text_chunk = process_yo_variants(text_chunk, yo_variants, replace_all_choices, global_line_offset)
        if SHOULD_STOP: raise KeyboardInterrupt()
        text_chunk = replace_yo_in_text(text_chunk, sorted_yo_data)
        return text_chunk

    is_epub = input_file.lower().endswith('.epub')
    is_fb2 = input_file.lower().endswith('.fb2')
    is_md = input_file.lower().endswith('.md')

    if is_epub:
        base_dir = os.path.dirname(os.path.abspath(input_file))
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_epub = os.path.join(base_dir, base_name + '_yo.epub')
        output_html = os.path.join(base_dir, base_name + '_yo.html')
        tmp_epub = output_epub + '.tmp'
        
        start_idx = session_data.get('processed_index', 0)
        html_contents = session_data.get('html_contents', [])
        mode = 'w' if start_idx == 0 else 'a'
        
        # Пре-сканирование для Base64 и сносок (для HTML-превью)
        images_base64 = {}
        epub_notes = {}
        try:
            with zipfile.ZipFile(input_file, 'r') as zin:
                for info in zin.infolist():
                    fname = info.filename.lower()
                    if fname.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')):
                        try:
                            img_data = zin.read(info.filename)
                            mime_type, _ = mimetypes.guess_type(info.filename)
                            if not mime_type:
                                if fname.endswith('.svg'): mime_type = 'image/svg+xml'
                                else: mime_type = 'image/jpeg'
                            b64_data = base64.b64encode(img_data).decode('utf-8')
                            images_base64[info.filename] = f"data:{mime_type};base64,{b64_data}"
                        except: pass
                    elif fname.endswith(('.html', '.xhtml', '.htm')):
                        # Предварительный сбор всех ID для сносок в EPUB
                        try:
                            content = zin.read(info.filename).decode('utf-8')
                            # Ищем все элементы с ID, которые могут быть сносками (обычно внизу страницы)
                            for match in re.finditer(r'<(?:div|p|section|aside)[^>]*?\bid=["\']([^"\']+)["\'][^>]*>(.*?)</(?:div|p|section|aside)>', content, re.IGNORECASE | re.DOTALL):
                                note_id = match.group(1)
                                note_body = re.sub(r'<[^>]+>', ' ', match.group(2))
                                note_body = re.sub(r'\s+', ' ', note_body).strip()
                                if note_body:
                                    epub_notes[note_id] = note_body
                        except: pass
        except: pass

        def fix_epub_img_paths(html_content, current_file_path, images_map):
            import posixpath
            import urllib.parse
            def replacer(match):
                src = match.group(1)
                abs_path = posixpath.normpath(posixpath.join(posixpath.dirname(current_file_path), src))
                decoded_path = urllib.parse.unquote(abs_path)
                if decoded_path in images_map: return f'src="{images_map[decoded_path]}"'
                if abs_path in images_map: return f'src="{images_map[abs_path]}"'
                return match.group(0)
            return re.sub(r'src=["\'](.*?)["\']', replacer, html_content, flags=re.IGNORECASE)

        print(f"{Fore.CYAN}Чтение и обработка EPUB архива...{Style.RESET_ALL}")
        try:
            with zipfile.ZipFile(input_file, 'r') as zin:
                with zipfile.ZipFile(tmp_epub, mode, compression=zipfile.ZIP_DEFLATED) as zout:
                    from modules.epub_utils import get_ordered_infolist
                    infolist = get_ordered_infolist(zin)
                    if hasattr(builtins, 'gui_update_progress') and len(infolist) > 0:
                        builtins.gui_update_progress(start_idx / len(infolist))
                    for i in range(start_idx, len(infolist)):
                        item = infolist[i]
                        if SHOULD_STOP: raise KeyboardInterrupt()
                        content = zin.read(item.filename)
                        if item.filename.lower().endswith(('.html', '.xhtml', '.htm')):
                            try:
                                text_content = content.decode('utf-8')
                                processed = process_text_chunk(text_content)
                                
                                # For HTML version: extract body and wrap in a card
                                body_match = re.search(r'<body[^>]*>(.*?)</body>', processed, re.IGNORECASE | re.DOTALL)
                                if body_match:
                                    chapter_body = body_match.group(1)
                                else:
                                    chapter_body = processed
                                
                                # Fix images for HTML preview
                                chapter_body = fix_epub_img_paths(chapter_body, item.filename, images_base64)
                                
                                # Make EPUB footnotes as tooltips if possible, otherwise jumpable
                                def epub_link_replacer(match):
                                    href_attr = match.group(1)
                                    text = match.group(2)
                                    if '#' in href_attr:
                                        note_id = href_attr.split('#', 1)[1]
                                        if note_id in epub_notes and len(epub_notes[note_id]) > 5:
                                            return f'<span class="tooltip">{text}<span class="tooltiptext">{epub_notes[note_id]}</span></span>'
                                        return f'<a href="#{note_id}">{text}</a>'
                                    return match.group(0)
                                chapter_body = re.sub(r'<a[^>]*?\bhref=["\']([^"\']+)["\'][^>]*>(.*?)</a>', epub_link_replacer, chapter_body, flags=re.IGNORECASE | re.DOTALL)

                                if chapter_body.strip():
                                    html_contents.append(f'<div class="chapter-card">{chapter_body}</div>')
                                
                                # For EPUB version: clean up yorz tags
                                clean_epub_text = re.sub(r'</?yorz[^>]*>', '', processed)
                                zout.writestr(item, clean_epub_text.encode('utf-8'))
                            except (KeyboardInterrupt, SystemExit):
                                raise
                            except Exception as e:
                                print(f"{Fore.RED}Ошибка обработки файла {item.filename} внутри epub: {e}{Style.RESET_ALL}")
                                zout.writestr(item, content)
                        elif item.filename.lower().endswith('.opf'):
                            try:
                                text_content = content.decode('utf-8')
                                import datetime
                                today_str = datetime.date.today().isoformat()
                                
                                # Ищем существующую метку
                                meta_pattern = re.compile(r'<meta name=".*?" content="(Текст обработан программой YoRZ 2\.0 \(.*?\))"/>')
                                match = meta_pattern.search(text_content)
                                current_meta = match.group(1) if match else ""
                                new_meta_str = paths.update_metadata(current_meta, "Ёфикатор", app_version)
                                
                                if match:
                                    text_content = text_content.replace(match.group(0), f'<meta name="{today_str}:" content="{new_meta_str}"/>')
                                else:
                                    meta_tag = f'\n    <meta name="{today_str}:" content="{new_meta_str}"/>\n'
                                    text_content = text_content.replace('</metadata>', meta_tag + '</metadata>')
                                
                                zout.writestr(item, text_content.encode('utf-8'))
                            except Exception as e:
                                print(f"{Fore.RED}Ошибка обработки файла {item.filename} внутри epub: {e}{Style.RESET_ALL}")
                                zout.writestr(item, content)
                        else:
                            zout.writestr(item, content)
                        session_data['processed_index'] = i + 1
                        if hasattr(builtins, 'gui_update_progress'):
                            builtins.gui_update_progress((i + 1) / len(infolist))
            
            # Если дошли сюда без прерываний
            if os.path.exists(output_epub):
                os.remove(output_epub)
            os.rename(tmp_epub, output_epub)

            full_html_body = "\n".join(html_contents)
            full_html_body = re.sub(r'<(/?)yorz', r'<\1span', full_html_body)
            
            with open(output_html, 'w', encoding='utf-8') as f:
                f.write(get_html_template(base_name, full_html_body))

            if os.path.exists(session_file):
                os.remove(session_file)

            print(f"{Fore.GREEN}EPUB успешно обработан. Версия со структурой: {output_epub}. HTML с подсветкой: {output_html}{Style.RESET_ALL}")
        except (KeyboardInterrupt, SystemExit):
            session_data['html_contents'] = html_contents
            save_session()
            print(f"\n{Fore.YELLOW}Сохранение прогресса...{Style.RESET_ALL}")
            raise
        except Exception as e:
            if os.path.exists(tmp_epub):
                os.remove(tmp_epub)
            print(f"{Fore.RED}Ошибка при работе с EPUB архивом: {e}{Style.RESET_ALL}")
        return

    # Если это обычный текст, fb2 или md
    base_dir = os.path.dirname(os.path.abspath(input_file))
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    output_html = os.path.join(base_dir, base_name + '_yo.html')
    output_clean = os.path.join(base_dir, base_name + ('_yo.fb2' if is_fb2 else ('_yo.md' if is_md else '_yo.txt')))

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            text_content = f.read()
    except Exception as e:
        print(f"{Fore.RED}Не удалось прочитать {input_file}: {e}{Style.RESET_ALL}")
        return

    start_idx = session_data.get('processed_index', 0)
    html_contents = session_data.get('html_contents', [])

    if is_fb2:
        print(f"{Fore.CYAN}Извлечение текста из FB2 и обработка...{Style.RESET_ALL}")
        # Разделяем на части, захватывая нужные теги целиком. Указываем точные закрывающие теги для каждого, 
        # чтобы <title> не обрывался на первом встретившемся </p> внутри него. И используем (?=[\s>/]) вместо \b
        parts = re.split(r'(<p(?=[\s>/])[^>]*>.*?</p>|<v(?=[\s>/])[^>]*>.*?</v>|<text-author(?=[\s>/])[^>]*>.*?</text-author>|<subtitle(?=[\s>/])[^>]*>.*?</subtitle>|<title(?=[\s>/])[^>]*>.*?</title>|<empty-line(?=[\s>/])[^>]*>.*?</empty-line>|<empty-line(?=[\s>/])[^>]*/>)', text_content, flags=re.IGNORECASE | re.DOTALL)
        
        try:
            if hasattr(builtins, 'gui_update_progress') and len(parts) > 0:
                builtins.gui_update_progress(start_idx / len(parts))
            for i in range(start_idx, len(parts)):
                if SHOULD_STOP: raise KeyboardInterrupt()
                part = parts[i]
                # Ищем теги, контент которых нужно обработать (включая вложенные <p> внутри <title>)
                match = re.match(r'<(p|v|text-author|subtitle|title)(?=[\s>/])([^>]*)>(.*?)</\1>', part, re.IGNORECASE | re.DOTALL)
                if match:
                    tag_name, tag_attrs, content = match.groups()
                    if not content.strip():
                        html_contents.append(part)
                    else:
                        # Обрабатываем содержимое. Если внутри есть еще теги (как <p> в <title>), 
                        # process_text_chunk их проигнорирует благодаря tag_pattern
                        processed_content = process_text_chunk(content, global_line_offset=i)
                        html_contents.append(f"<{tag_name}{tag_attrs}>{processed_content}</{tag_name}>")
                else:
                    html_contents.append(part)
                
                session_data['processed_index'] = i + 1
                if hasattr(builtins, 'gui_update_progress'):
                    builtins.gui_update_progress((i + 1) / len(parts))
        except (KeyboardInterrupt, SystemExit):
            session_data['html_contents'] = html_contents
            save_session()
            print(f"\n{Fore.YELLOW}Сохранение прогресса...{Style.RESET_ALL}")
            raise

    else:
        print(f"{Fore.CYAN}Чтение и обработка текста...{Style.RESET_ALL}")
        paragraphs = text_content.split('\n')
        try:
            if hasattr(builtins, 'gui_update_progress') and len(paragraphs) > 0:
                builtins.gui_update_progress(start_idx / len(paragraphs))
            for i in range(start_idx, len(paragraphs)):
                if SHOULD_STOP: raise KeyboardInterrupt()
                p_text = paragraphs[i]
                if not p_text.strip():
                    html_contents.append("")
                else:
                    processed_p = process_text_chunk(p_text, global_line_offset=i)
                    html_contents.append(processed_p)
                session_data['processed_index'] = i + 1
                if hasattr(builtins, 'gui_update_progress'):
                    builtins.gui_update_progress((i + 1) / len(paragraphs))
        except (KeyboardInterrupt, SystemExit):
            session_data['html_contents'] = html_contents
            save_session()
            print(f"\n{Fore.YELLOW}Сохранение прогресса...{Style.RESET_ALL}")
            raise

    full_processed_text = ('' if is_fb2 else '\n').join(html_contents)
    import datetime

    # Сохраняем чистую версию (убираем временные теги yorz)
    clean_text = re.sub(r'</?yorz[^>]*>', '', full_processed_text)
    
    today_str = datetime.date.today().isoformat()
    if is_fb2:
        # Ищем существующую метку в истории (быстрый поиск без тяжелых регулярок)
        meta_match = re.search(r'<p>[^<]*(Текст обработан программой YoRZ 2\.0 \([^)]*\))</p>', clean_text[:15000]) or re.search(r'<p>[^<]*(Текст обработан программой YoRZ 2\.0 \([^)]*\))</p>', clean_text)
        current_meta = meta_match.group(1) if meta_match else ""
        new_meta_str = paths.update_metadata(current_meta, "Ёфикатор", app_version)
        
        history_entry = f'<p>{today_str}: {new_meta_str}</p>'
        if meta_match:
            clean_text = clean_text.replace(meta_match.group(0), history_entry)
        elif '</history>' in clean_text[:15000] or '</history>' in clean_text:
            clean_text = clean_text.replace('</history>', f'\n{history_entry}\n</history>', 1)
        elif '</document-info>' in clean_text[:15000] or '</document-info>' in clean_text:
            meta_tag = f'\n<history>\n{history_entry}\n</history>\n'
            clean_text = clean_text.replace('</document-info>', meta_tag + '</document-info>', 1)
        elif '</description>' in clean_text[:15000] or '</description>' in clean_text:
            meta_tag = f'\n<document-info>\n<history>\n{history_entry}\n</history>\n</document-info>\n'
            clean_text = clean_text.replace('</description>', meta_tag + '</description>', 1)
    else:
        # Ищем существующую метку в MD или TXT
        if is_md:
            meta_pattern = re.compile(r'<!-- .*?(Текст обработан программой YoRZ 2\.0 \(.*?\)) -->')
        else:
            meta_pattern = re.compile(r'.*?(Текст обработан программой YoRZ 2\.0 \(.*?\))')
            
        match = meta_pattern.search(clean_text)
        current_meta = match.group(1) if match else ""
        new_meta_str = paths.update_metadata(current_meta, "Ёфикатор", app_version)
        
        if is_md:
            new_entry = f'\n\n<!-- {today_str}: {new_meta_str} -->\n'
        else:
            new_entry = f'\n\n{today_str}: {new_meta_str}\n'
            
        if match:
            clean_text = clean_text.replace(match.group(0), new_entry.strip())
        else:
            clean_text = clean_text.rstrip() + new_entry

    with open(output_clean, 'w', encoding='utf-8') as f:
        f.write(clean_text)

    # Сохраняем HTML версию с подсветкой
    if is_fb2:
        # Extract images from FB2 for HTML preview
        fb2_images = {}
        for img_match in re.finditer(r'<binary[^>]*?\bid=["\']([^"\']+)["\'][^>]*>([^<]+)</binary>', text_content, re.IGNORECASE):
            img_id = img_match.group(1)
            img_data_b64 = re.sub(r'\s+', '', img_match.group(2))
            mime_type = "image/jpeg"
            if img_id.lower().endswith('.png'): mime_type = "image/png"
            elif img_id.lower().endswith('.gif'): mime_type = "image/gif"
            fb2_images[img_id] = f"data:{mime_type};base64,{img_data_b64}"

        # Extract footnotes for tooltips
        fb2_notes = {}
        for note_match in re.finditer(r'<section[^>]*?\bid=["\']([^"\']+)["\'][^>]*>(.*?)</section>', text_content, re.IGNORECASE | re.DOTALL):
            note_id = note_match.group(1)
            note_content = re.sub(r'<title[^>]*>.*?</title>', '', note_match.group(2), flags=re.IGNORECASE | re.DOTALL)
            note_content = re.sub(r'<[^>]+>', ' ', note_content)
            note_content = re.sub(r'\s+', ' ', note_content).strip()
            fb2_notes[note_id] = note_content

        # Extract cover image from description before removing it
        cover_img_html = ""
        cover_match = re.search(r'<coverpage[^>]*>.*?<image[^>]*?\b(?:l:|xlink:)?href=["\']#([^"\']+)["\'][^>]*>', text_content, re.IGNORECASE | re.DOTALL)
        if cover_match:
            cover_id = cover_match.group(1)
            if cover_id in fb2_images:
                cover_img_html = f'<img src="{fb2_images[cover_id]}" style="width:100%; max-width:100%; height:auto; margin: 0 auto 30px auto;" />'

        joined_html = "".join(html_contents)
        
        # Убираем техническую информацию (метаданные) и секции с бинарниками из итогового HTML
        joined_html = re.sub(r'<description[^>]*>.*?</description>', '', joined_html, flags=re.IGNORECASE | re.DOTALL)
        joined_html = re.sub(r'<binary[^>]*>[^<]*</binary>', '', joined_html, flags=re.IGNORECASE)
        
        # Вставляем обложку в самое начало
        if cover_img_html:
            joined_html = cover_img_html + joined_html
        
        # Apply yo highlights
        joined_html = re.sub(r'<(/?)yorz', r'<\1span', joined_html)
        
        # Simple tag replacement for FB2
        joined_html = re.sub(r'<title(?=[\s>/])[^>]*>(.*?)</title>', r'<h3>\1</h3>', joined_html, flags=re.IGNORECASE | re.DOTALL)
        joined_html = re.sub(r'<subtitle(?=[\s>/])[^>]*>(.*?)</subtitle>', r'<h4>\1</h4>', joined_html, flags=re.IGNORECASE | re.DOTALL)
        joined_html = re.sub(r'<p(?=[\s>/])[^>]*>(.*?)</p>', r'<p>\1</p>', joined_html, flags=re.IGNORECASE | re.DOTALL)
        joined_html = re.sub(r'<v(?=[\s>/])[^>]*>(.*?)</v>', r'<p style="font-style:italic; text-align:center;">\1</p>', joined_html, flags=re.IGNORECASE | re.DOTALL)
        joined_html = re.sub(r'<empty-line(?=[\s>/])[^>]*/>', r'<br/><br/>', joined_html, flags=re.IGNORECASE)
        
        # Fix images in FB2
        def fb2_img_replacer(match):
            href = match.group(1)
            if href.startswith('#'):
                img_id = href[1:]
                if img_id in fb2_images:
                    return f'<img src="{fb2_images[img_id]}" />'
            return match.group(0)
        joined_html = re.sub(r'<image[^>]*?\b(?:l:|xlink:)?href=["\']([^"\']+)["\'][^>]*>(?:\s*</image>)?', fb2_img_replacer, joined_html, flags=re.IGNORECASE)

        # Footnotes tooltips
        def fb2_note_replacer(match):
            href = match.group(1)
            text = match.group(2)
            if href.startswith('#'):
                note_id = href[1:]
                if note_id in fb2_notes and fb2_notes[note_id]:
                    return f'<span class="tooltip">{text}<span class="tooltiptext">{fb2_notes[note_id]}</span></span>'
            return match.group(0)
        joined_html = re.sub(r'<a[^>]*?\b(?:l:|xlink:)?href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', fb2_note_replacer, joined_html, flags=re.IGNORECASE | re.DOTALL)

        # Split into cards
        cards = re.split(r'(<h3>)', joined_html)
        final_preview_parts = []
        
        if cards[0].strip():
            final_preview_parts.append(f'<div class="chapter-card">{cards[0]}</div>')
            
        for i in range(1, len(cards), 2):
            card_content = cards[i] + (cards[i+1] if i+1 < len(cards) else "")
            if card_content.strip():
                final_preview_parts.append(f'<div class="chapter-card">{card_content}</div>')
                
        preview_html = '\n'.join(final_preview_parts) if final_preview_parts else "Ошибка генерации предпросмотра."
    else:
        highlighted_text = re.sub(r'<(/?)yorz', r'<\1span', full_processed_text)
        html_body = []
        for line in highlighted_text.split('\n'):
            if line.strip(): html_body.append(f"<p>{line}</p>")
            else: html_body.append("<p>&nbsp;</p>")
        preview_html = f'<div class="chapter-card">{"".join(html_body)}</div>'

    base_name = os.path.splitext(os.path.basename(input_file))[0]

    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(get_html_template(base_name, preview_html))
        
    if os.path.exists(session_file):
        os.remove(session_file)
        
    print(f"{Fore.GREEN}Обработка завершена.{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Чистая версия: {output_clean}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}HTML с подсветкой: {output_html}{Style.RESET_ALL}")

def run(input_file="book.txt", app_version=None):
    try:
        replace_expressions(input_file=input_file, app_version=app_version)
    except Exception as e:
        print(f"{Fore.RED}Ошибка при ёфикации: {str(e)}{Style.RESET_ALL}")

if __name__ == "__main__":
    run()
