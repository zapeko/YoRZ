import re
import os
import zipfile
import sys
import unicodedata
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
            if rest:
                exc_part = rest[0].split(')', 1)[0].strip()
                for exc in exc_part.split(':'):
                    exc = re.sub(r'\\(w[\*\+])', r'\\\1', exc.strip())
                    try: exc_patterns.append(re.compile(fr'\b{exc}\b', re.I))
                    except re.error: pass

            yo_dict[key] = {
                'replace': replacement,
                'exceptions_compiled': exc_patterns,
                'pattern': pattern,
                'priority': len(key.replace(r'\w', ''))
            }
    return yo_dict

def preserve_case(match, replacement):
    original_text = match.group()
    original_words = re.findall(r'\w+|\W+', original_text)
    replacement_words = re.findall(r'\w+|\W+', replacement)
    result = []
    for orig_word, repl_word in zip(original_words, replacement_words):
        if orig_word.isupper(): result.append(repl_word.upper())
        elif orig_word.istitle(): result.append(repl_word.title())
        else: result.append(repl_word.lower())
    return ''.join(result)

def replace_yo_in_text(text, yo_dict):
    tag_pattern = re.compile(r'(<[^>]+>)')
    sorted_data = sorted(yo_dict.values(), key=lambda x: (-x['priority'], str(x['pattern'])))
    for data in sorted_data:
        parts = tag_pattern.split(text)
        for i in range(0, len(parts), 2):
            if not parts[i].strip(): continue
            parts[i] = data['pattern'].sub(
                lambda m: (
                    m.group() if any(exc.search(remove_diacritics(m.group())) for exc in data['exceptions_compiled'])
                    else f'<yorz class="highlight-yellow">{preserve_case(m, m.expand(data["replace"]))}</yorz>'
                ), parts[i]
            )
        text = ''.join(parts)
    return text

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
                        else:
                            choice_input = input("Выберите [1/2/3,4-везде/Enter-пропустить]: ").strip()
                    except KeyboardInterrupt:
                        print(f"\n{Fore.RED}Программа прервана пользователем.{Style.RESET_ALL}")
                        sys.exit(0)

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

            exc_patterns = []
            if rest:
                exc_part = rest[0].split(')', 1)[0].strip()
                for exc in exc_part.split(':'):
                    exc = re.sub(r'\\(w[\*\+])', r'\\\1', exc.strip())
                    try: exc_patterns.append(re.compile(fr'\b{exc}\b', re.I))
                    except re.error: pass
            replacements_dict[original] = {'replacement': replacement, 'exceptions': exc_patterns}
    return replacements_dict

def apply_replacements(text, replacements_dict, span_class):
    tag_pattern = re.compile(r'(<yorz[^>]*>.*?</yorz>|<[^>]+>)', re.IGNORECASE | re.DOTALL)
    for original, data in replacements_dict.items():
        replacement = data['replacement']
        exceptions = data['exceptions']
        
        regex = None
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
            except re.error as e:
                continue
            
            parts = tag_pattern.split(text)
            for i in range(0, len(parts), 2):
                if not parts[i].strip(): continue
                parts[i] = regex.sub(
                    lambda m: (
                        m.group() if any(exc.search(remove_diacritics(m.group())) for exc in exceptions)
                        else f'<yorz class="{span_class}">{preserve_case(m, m.expand(fixed_replacement))}</yorz>'
                    ), parts[i]
                )
            text = ''.join(parts)
        else:
            escaped_original = re.escape(original).replace(r'\ ', r'\s+')
            pattern = r'(?<![\w\u0300-\u036F])' + escaped_original + r'(?![\w\u0300-\u036F])'
            try:
                regex = re.compile(pattern, re.I)
            except re.error as e:
                continue
            
            parts = tag_pattern.split(text)
            for i in range(0, len(parts), 2):
                if not parts[i].strip(): continue
                parts[i] = regex.sub(
                    lambda m: (
                        m.group() if any(exc.search(remove_diacritics(m.group())) for exc in exceptions)
                        else f'<yorz class="{span_class}">{preserve_case(m, replacement)}</yorz>'
                    ), parts[i]
                )
            text = ''.join(parts)
            
    return text

SHOULD_STOP = False

def replace_expressions(input_file="book.txt", regular_file="green.dic", yo_no_regular_file="blue.dic", output_file=None, yo_dict_file="yellow.dic", yo_variant_file="orange.dic"):
    global SHOULD_STOP
    SHOULD_STOP = False
    import builtins
    import json
    import os
    
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
        text_chunk = replace_yo_in_text(text_chunk, yo_dict)
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
        
        print(f"{Fore.CYAN}Чтение и обработка EPUB архива...{Style.RESET_ALL}")
        try:
            with zipfile.ZipFile(input_file, 'r') as zin:
                with zipfile.ZipFile(tmp_epub, mode, compression=zipfile.ZIP_DEFLATED) as zout:
                    from modules.epub_utils import get_ordered_infolist
                    infolist = get_ordered_infolist(zin)
                    for i in range(start_idx, len(infolist)):
                        item = infolist[i]
                        if SHOULD_STOP: raise KeyboardInterrupt()
                        content = zin.read(item.filename)
                        if item.filename.lower().endswith(('.html', '.xhtml', '.htm')):
                            try:
                                text_content = content.decode('utf-8')
                                processed = process_text_chunk(text_content)
                                
                                # For HTML version: extract body
                                import re
                                body_match = re.search(r'<body[^>]*>(.*?)</body>', processed, re.IGNORECASE | re.DOTALL)
                                if body_match:
                                    html_contents.append(body_match.group(1))
                                else:
                                    html_contents.append(processed)
                                
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
                                meta_tag = f'\n    <meta name="{today_str}:" content="Текст обработан программой YoRZ 2.0 (Ёфикатор)"/>\n'
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
            import re
            full_html_body = re.sub(r'<(/?)yorz', r'<\1span', full_html_body)
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            with open(output_html, 'w', encoding='utf-8') as f:
                f.write(f"""<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">\n<html xmlns="http://www.w3.org/1999/xhtml">\n<head>\n<title>{base_name}</title>\n<style>\nhtml {{color: #000000; background-color: #FFFAFA;}}\nbody {{text-align : justify }}\np {{text-indent: 2em;  margin-bottom: 0em; margin-top: 0em; font-size : 110%; font-style : normal; font-weight : bold;}}\n.highlight-yellow {{ background-color: yellow; }}\n.highlight-green {{ background-color: lightgreen; }}\n.highlight-blue {{ background-color: lightblue; }}\n.highlight-orange {{ background-color: orange; }}\n</style>\n</head>\n<body>\n""")
                f.write(full_html_body)
                f.write("\n</body>\n</html>")

            if os.path.exists(session_file):
                os.remove(session_file)

            print(f"{Fore.GREEN}EPUB успешно обработан. Версия со структурой: {output_epub}. HTML с подсветкой: {output_html}{Style.RESET_ALL}")
        except (KeyboardInterrupt, SystemExit):
            session_data['html_contents'] = html_contents
            save_session()
            print(f"\n{Fore.RED}Программа прервана.{Style.RESET_ALL}")
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
        import re
        # Разделяем на части, захватывая нужные теги целиком. Указываем точные закрывающие теги для каждого, 
        # чтобы <title> не обрывался на первом встретившемся </p> внутри него. И используем (?=[\s>/]) вместо \b
        parts = re.split(r'(<p(?=[\s>/])[^>]*>.*?</p>|<v(?=[\s>/])[^>]*>.*?</v>|<text-author(?=[\s>/])[^>]*>.*?</text-author>|<subtitle(?=[\s>/])[^>]*>.*?</subtitle>|<title(?=[\s>/])[^>]*>.*?</title>|<empty-line(?=[\s>/])[^>]*>.*?</empty-line>|<empty-line(?=[\s>/])[^>]*/>)', text_content, flags=re.IGNORECASE | re.DOTALL)
        
        try:
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
            print(f"\n{Fore.RED}Программа прервана.{Style.RESET_ALL}")
            raise

    else:
        print(f"{Fore.CYAN}Чтение и обработка текста...{Style.RESET_ALL}")
        paragraphs = text_content.split('\n')
        try:
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
            print(f"\n{Fore.RED}Программа прервана.{Style.RESET_ALL}")
            raise

    full_processed_text = ('' if is_fb2 else '\n').join(html_contents)
    import re
    import datetime

    # Сохраняем чистую версию (убираем временные теги yorz)
    clean_text = re.sub(r'</?yorz[^>]*>', '', full_processed_text)
    
    today_str = datetime.date.today().isoformat()
    if is_fb2:
        history_entry = f'<p>{today_str}: Текст обработан программой YoRZ 2.0 (Ёфикатор)</p>'
        if '</history>' in clean_text:
            clean_text = clean_text.replace('</history>', f'\n{history_entry}\n</history>')
        elif '</document-info>' in clean_text:
            meta_tag = f'\n<history>\n{history_entry}\n</history>\n'
            clean_text = clean_text.replace('</document-info>', meta_tag + '</document-info>')
        elif '</description>' in clean_text:
            meta_tag = f'\n<document-info>\n<history>\n{history_entry}\n</history>\n</document-info>\n'
            clean_text = clean_text.replace('</description>', meta_tag + '</description>')
    else:
        if is_md:
            clean_text = clean_text.rstrip() + f'\n\n<!-- {today_str}: Текст обработан программой YoRZ 2.0 (Ёфикатор) -->\n'
        else:
            clean_text = clean_text.rstrip() + f'\n\n{today_str}: Текст обработан программой YoRZ 2.0 (Ёфикатор)\n'

    with open(output_clean, 'w', encoding='utf-8') as f:
        f.write(clean_text)

    # Сохраняем HTML версию с подсветкой
    highlighted_text = re.sub(r'<(/?)yorz', r'<\1span', full_processed_text)
    
    if is_fb2:
        # Для предпросмотра FB2 делаем простую замену тегов на HTML аналоги
        preview_html = highlighted_text
        # Заголовки глав
        preview_html = re.sub(r'<title(?=[\s>/])[^>]*>(.*?)</title>', r'<h3 style="text-align:center; color:#8b0000; margin-top:2em; border-bottom:1px solid #ccc;">\1</h3>', preview_html, flags=re.IGNORECASE | re.DOTALL)
        # Подзаголовки
        preview_html = re.sub(r'<subtitle(?=[\s>/])[^>]*>(.*?)</subtitle>', r'<h4 style="text-align:center; color:#555;">\1</h4>', preview_html, flags=re.IGNORECASE | re.DOTALL)
        # Абзацы
        preview_html = re.sub(r'<p(?=[\s>/])[^>]*>(.*?)</p>', r'<p style="text-indent:2em; margin:0.5em 0;">\1</p>', preview_html, flags=re.IGNORECASE | re.DOTALL)
        # Стихи/цитаты
        preview_html = re.sub(r'<v(?=[\s>/])[^>]*>(.*?)</v>', r'<p style="font-style:italic; text-align:center; margin:0.2em 0;">\1</p>', preview_html, flags=re.IGNORECASE | re.DOTALL)
        # Пустые строки
        preview_html = re.sub(r'<empty-line(?=[\s>/])[^>]*/>', r'<br/><br/>', preview_html, flags=re.IGNORECASE)
        
        # Пересоберем body только из нужных нам элементов, чтобы не было мусора от метаданных и бинарных данных
        # Извлекаем все наши h3, h4, p и br
        final_parts = []
        for m in re.finditer(r'<(p|h3|h4)(?=[\s>/])[^>]*>.*?</\1>|<br\s*/?>', preview_html, flags=re.IGNORECASE | re.DOTALL):
            final_parts.append(m.group(0))
            
        preview_html = '\n'.join(final_parts) if final_parts else "Ошибка генерации предпросмотра."
    else:
        html_body = []
        for line in highlighted_text.split('\n'):
            if line.strip(): html_body.append(f"<p>{line}</p>")
            else: html_body.append("<p>&nbsp;</p>")
        preview_html = '\n'.join(html_body)

    base_name = os.path.splitext(os.path.basename(input_file))[0]

    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(f"""<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">\n<html xmlns="http://www.w3.org/1999/xhtml">\n<head>\n<title>{base_name}</title>\n<style>\nhtml {{color: #000000; background-color: #FFFAFA;}}\nbody {{text-align : justify }}\np {{text-indent: 2em;  margin-bottom: 0em; margin-top: 0em; font-size : 110%; font-style : normal; font-weight : bold;}}\n.highlight-yellow {{ background-color: yellow; }}\n.highlight-green {{ background-color: lightgreen; }}\n.highlight-blue {{ background-color: lightblue; }}\n.highlight-orange {{ background-color: orange; }}\n</style>\n</head>\n<body>\n""")
        f.write(preview_html)
        f.write("\n</body>\n</html>")
        
    if os.path.exists(session_file):
        os.remove(session_file)
        
    print(f"{Fore.GREEN}Обработка завершена.{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Чистая версия: {output_clean}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}HTML с подсветкой: {output_html}{Style.RESET_ALL}")

def run(input_file="book.txt"):
    try:
        replace_expressions(input_file=input_file)
    except Exception as e:
        print(f"{Fore.RED}Ошибка при ёфикации: {str(e)}{Style.RESET_ALL}")

if __name__ == "__main__":
    run()
