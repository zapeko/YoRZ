import os
import re
import unicodedata
from colorama import Fore, Style
from . import paths

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

def load_lines(filename):
    if not os.path.exists(filename): return []
    with open(filename, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]

def extract_words(text):
    return re.findall(r"[а-яё]+", text)

def matches_condition(word, root, root_variant):
    if root[0] == "ё":
        if word.startswith(root) or word.startswith(root_variant):
            return True
    if root[-1] == "ё":
        if word.endswith(root) or word.endswith(root_variant):
            return True
    if len(root) > 2 and root[1] == "ё":
        if root in word or root_variant in word:
            return True
    return False

def generate_alternatives(word):
    alternatives = set()
    def rec(current, index):
        if index == len(word):
            variant = "".join(current)
            if variant != word:
                alternatives.add(variant)
            return
        ch = word[index]
        if ch in {"е", "ё"}:
            rec(current + [ch], index + 1)
            alt = "ё" if ch == "е" else "е"
            rec(current + [alt], index + 1)
        else:
            rec(current + [ch], index + 1)
    rec([], 0)
    return alternatives

def run(input_filename="book.txt"):
    if not os.path.exists(input_filename):
        print(f"{Fore.RED}Файл {input_filename} не найден!{Style.RESET_ALL}")
        return

    ext = input_filename.lower().split('.')[-1]
    text = ""
    if ext == 'epub':
        import zipfile
        from modules.epub_utils import get_ordered_infolist
        text_blocks = []
        try:
            with zipfile.ZipFile(input_filename, 'r') as zin:
                for item in get_ordered_infolist(zin):
                    if item.filename.lower().endswith(('.html', '.xhtml', '.htm')):
                        content = zin.read(item.filename).decode('utf-8', errors='ignore')
                        text_blocks.append(re.sub(r'<[^>]+>', ' ', content))
            text = ' '.join(text_blocks).lower()
        except Exception as e:
            print(f"{Fore.RED}Ошибка при работе с EPUB архивом: {e}{Style.RESET_ALL}")
            return
    if ext == 'fb2':
        with open(input_filename, 'r', encoding="utf-8", errors='ignore') as f:
            content = f.read()
        text = re.sub(r'<[^>]+>', ' ', content).lower()
    else:
        with open(input_filename, encoding="utf-8", errors='ignore') as f:
            text = f.read().lower()

    try:
        raw_roots = load_lines(paths.get_path("dictionaries/yellow_root.txt"))
    except FileNotFoundError:
        print(f"{Fore.RED}Файл dictionaries/yellow_root.txt не найден!{Style.RESET_ALL}")
        return

    roots_tuples = []
    for r in raw_roots:
        if not r: continue
        r_variant = r.replace("ё", "е")
        roots_tuples.append((r, r_variant))

    import time
    # Добавляем обновление прогресс-бара
    def update_prog(percent):
        import builtins
        if hasattr(builtins, 'gui_update_progress'):
            builtins.gui_update_progress(percent)
            # Даем GUI крошечную паузу, чтобы он успел отрисовать изменения
            time.sleep(0.001)
            
    update_prog(0.01) # Сразу показываем начало работы

    print(f"{Fore.CYAN}Извлечение уникальных слов из текста...{Style.RESET_ALL}")
    all_words = extract_words(text)
    unique_words = list(set(all_words))
    total_unique = len(unique_words)
    
    extracted_set = set()
    
    print(f"{Fore.CYAN}Анализ слов по корням ({total_unique} уникальных слов)...{Style.RESET_ALL}")
    
    # Объединяем очистку диакритики и проверку корней в один цикл для точного прогресса
    for i, word in enumerate(unique_words):
        # Обновляем прогресс каждые 200 слов (чаще, чем было)
        if i % 200 == 0:
            update_prog(i / total_unique)
            
        # Сначала очищаем от диакритики
        clean_word = remove_diacritics(word)
        
        # Затем проверяем по корням
        for r, r_variant in roots_tuples:
            if matches_condition(clean_word, r, r_variant):
                extracted_set.add(clean_word)
                break
                
    update_prog(1.0)

    try:
        exclude_words = set(load_lines(paths.get_path("dictionaries/yellow_base.txt")))
    except FileNotFoundError:
        print(f"{Fore.RED}Файл dictionaries/yellow_base.txt не найден!{Style.RESET_ALL}")
        exclude_words = set()

    # Extract words from green.dic and blue.dic to also exclude them
    for dic_name in ["dictionaries/green.dic", "dictionaries/blue.dic"]:
        dic_path = paths.get_path(dic_name)
        if os.path.exists(dic_path):
            try:
                with open(dic_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'): continue
                        if '(' in line:
                            line = line.split('(')[0]
                        parts = line.split('|')
                        for p in parts:
                            p_clean = re.sub(r'\\w[\*\+]', ' ', p)
                            for w in extract_words(p_clean):
                                exclude_words.add(remove_diacritics(w.lower()))
            except Exception as e:
                print(f"{Fore.RED}Ошибка чтения {dic_name}: {e}{Style.RESET_ALL}")

    final_words = extracted_set - exclude_words

    try:
        ignore_words = set(load_lines(paths.get_path("dictionaries/.ignore")))
        excluded_count = len(final_words.intersection(ignore_words))
        final_words -= ignore_words
        if excluded_count > 0:
            print(f"{Fore.YELLOW}Применена фильтрация по dictionaries/.ignore. Исключено слов: {excluded_count}{Style.RESET_ALL}")
    except FileNotFoundError:
        pass

    ru_alphabet = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
    alphabet_order = {char: idx for idx, char in enumerate(ru_alphabet)}
    def sort_key(word):
        return [alphabet_order.get(ch, 1000) for ch in word]
    sorted_words = sorted(final_words, key=sort_key)

    base_dir = os.path.dirname(os.path.abspath(input_filename))
    base_name, _ = os.path.splitext(os.path.basename(input_filename))
    output_filename = os.path.join(base_dir, f"{base_name}_extraction.txt")

    for_ignore = []
    with open(output_filename, "w", encoding="utf-8") as f:
        for word in sorted_words:
            alts = generate_alternatives(word)
            if any(alt in exclude_words for alt in alts):
                f.write(f"{word} (!)\n")
                for_ignore.append(word)
            else:
                f.write(word + "\n")

    for_ignore_filename = os.path.join(base_dir, "for_ignore.txt")
    if for_ignore:
        with open(for_ignore_filename, "w", encoding="utf-8") as f:
            for word in for_ignore:
                f.write(word + "\n")
        print(f"{Fore.CYAN}Слова для .ignore сохранены в: {for_ignore_filename} ({len(for_ignore)} слов){Style.RESET_ALL}")

    print(f"{Fore.GREEN}Извлечение слов завершено. Извлечено новых слов: {len(sorted_words)}.{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Результат сохранён в: {output_filename}{Style.RESET_ALL}")

if __name__ == "__main__":
    run()