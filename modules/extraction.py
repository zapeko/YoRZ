import os
import re
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

def load_lines(filename):
    with open(filename, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

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
    elif ext == 'fb2':
        with open(input_filename, 'r', encoding="utf-8", errors='ignore') as f:
            content = f.read()
        text = re.sub(r'<[^>]+>', ' ', content).lower()
    else:
        with open(input_filename, encoding="utf-8", errors='ignore') as f:
            text = f.read().lower()

    text = remove_diacritics(text)

    try:
        raw_roots = load_lines("yellow_root.txt")
    except FileNotFoundError:
        print(f"{Fore.RED}Файл yellow_root.txt не найден!{Style.RESET_ALL}")
        return

    roots_tuples = []
    for r in raw_roots:
        if not r: continue
        r_variant = r.replace("ё", "е")
        roots_tuples.append((r, r_variant))

    words = extract_words(text)

    extracted_set = set()
    for word in words:
        for r, r_variant in roots_tuples:
            if matches_condition(word, r, r_variant):
                extracted_set.add(word)
                break

    try:
        exclude_words = set(load_lines("yellow_base.txt"))
    except FileNotFoundError:
        print(f"{Fore.RED}Файл yellow_base.txt не найден!{Style.RESET_ALL}")
        exclude_words = set()

    final_words = extracted_set - exclude_words

    try:
        blacklist_words = set(load_lines("blacklist.txt"))
        excluded_count = len(final_words.intersection(blacklist_words))
        final_words -= blacklist_words
        if excluded_count > 0:
            print(f"{Fore.YELLOW}Применена фильтрация по blacklist.txt. Исключено слов: {excluded_count}{Style.RESET_ALL}")
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

    for_blacklist = []
    with open(output_filename, "w", encoding="utf-8") as f:
        for word in sorted_words:
            alts = generate_alternatives(word)
            if any(alt in exclude_words for alt in alts):
                f.write(f"{word} (!)\n")
                for_blacklist.append(word)
            else:
                f.write(word + "\n")

    for_blacklist_filename = os.path.join(base_dir, "for_blacklist.txt")
    with open(for_blacklist_filename, "w", encoding="utf-8") as f:
        for word in for_blacklist:
            f.write(word + "\n")
    
    if for_blacklist:
        print(f"{Fore.CYAN}Слова для blacklist сохранены в: {for_blacklist_filename}{Style.RESET_ALL}")

    print(f"{Fore.GREEN}Извлечение слов завершено. Результат сохранён в: {output_filename}{Style.RESET_ALL}")

if __name__ == "__main__":
    run()