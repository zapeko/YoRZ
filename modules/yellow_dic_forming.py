import re
import os
from colorama import Fore, Style
from . import paths

def russian_sort_key(s):
    special = {"", "w", "*"}
    i = 0
    while i < len(s) and s[i] in special: i += 1
    trimmed = s[i:].lower()
    russian_alphabet = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
    order_map = {char: idx for idx, char in enumerate(russian_alphabet)}
    key = []
    for ch in trimmed:
        if ch in order_map: key.append(order_map[ch])
        else: key.append(len(russian_alphabet) + ord(ch))
    return tuple(key)

def generate_analog_variants(word):
    indices = [i for i, ch in enumerate(word) if ch == "ё"]
    if not indices or "е" not in word: return []
    variants = []
    n = len(indices)
    for mask in range(1, 2**n):
        chars = list(word)
        for j in range(n):
            if mask & (1 << j):
                pos = indices[j]
                chars[pos] = "е"
        variant = "".join(chars)
        if variant != word: variants.append(variant)
    return variants

def expand_parentheses(match):
    content = match.group(1)
    tokens = content.split(":")
    new_tokens = []
    for token in tokens:
        token = token.strip()
        if "ё" in token and "е" in token:
            analogs = generate_analog_variants(token)
            token_expanded = token + (":" + ":".join(analogs) if analogs else "")
            new_tokens.append(token_expanded)
        else:
            new_tokens.append(token)
    return "(" + ":".join(new_tokens) + ")"

def load_orange_regexes():
    orange_file = paths.get_path("dictionaries/orange.dic")
    regexes = []
    if os.path.exists(orange_file):
        with open(orange_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                parts = line.split("|")
                if len(parts) >= 1:
                    e_pattern = parts[0].strip()
                    if e_pattern.startswith("#") or e_pattern.startswith("####"): continue
                    try:
                        pattern = e_pattern.replace(r"\w*", ".*").replace(r"\w+", ".+")
                        regexes.append(re.compile(f"^{pattern}$", re.I))
                    except re.error:
                        continue
    return regexes

def load_all_roots():
    root_file = paths.get_path("dictionaries/yellow_root.txt")
    roots = []
    if os.path.exists(root_file):
        with open(root_file, "r", encoding="utf-8") as f:
            for line in f:
                r = line.strip()
                if r:
                    roots.append((r, r.replace("ё", "е")))
    return roots

def run():
    files = {
        "root": paths.get_path("dictionaries/yellow_root.txt"),
        "base": paths.get_path("dictionaries/yellow_base.txt"),
        "add": paths.get_path("dictionaries/yellow_add.txt"),
        "dic": paths.get_path("dictionaries/yellow.dic")
    }
    
    missing_files = []
    for f in [files["root"], files["base"], files["add"]]:
        if not os.path.exists(f): missing_files.append(f)
    if missing_files:
        print(f"{Fore.RED}Отсутствуют файлы: {', '.join(missing_files)}{Style.RESET_ALL}")
        return

    with open(files["root"], "r", encoding="utf-8") as f:
        yellow_root = [line.strip() for line in f if line.strip()]
    with open(files["base"], "r", encoding="utf-8") as f:
        yellow_base = [line.strip() for line in f if line.strip()]
    with open(files["add"], "r", encoding="utf-8") as f:
        yellow_add = [line.strip() for line in f if line.strip()]

    orange_regexes = load_orange_regexes()
    all_roots = load_all_roots()

    results = []
    for word in yellow_root:
        if "ё" not in word: continue
        replaced = word.replace("ё", "е")
        if word.startswith("ё"):
            combined_regex = replaced + r'\w*' + "|" + word + r'\w*'
            matching = [w for w in yellow_base if w.startswith(replaced)]
        elif word.endswith("ё"):
            combined_regex = r'\w*' + replaced + "|" + r'\w*' + word
            matching = [w for w in yellow_base if w.endswith(replaced)]
        elif "ё" in word[1:-1]:
            combined_regex = r'\w*' + replaced + r'\w*' + "|" + r'\w*' + word + r'\w*'
            matching = [w for w in yellow_base if replaced in w]
        else: continue

        # Оптимизация: фильтрация списка исключений
        filtered_matching = []
        for w in matching:
            keep = True
            if "ё" in w:
                w_e = w.replace("ё", "е")
                is_orange = any(regex.fullmatch(w_e) for regex in orange_regexes)
                
                if not is_orange:
                    # Подсчет уникальных позиций целевых гласных (е/ё) для найденных корней
                    vowel_indices = set()
                    for r_yo, r_e in all_roots:
                        yo_pos = r_yo.find("ё")
                        if yo_pos == -1: continue
                        
                        start = 0
                        while True:
                            idx = w.find(r_yo, start)
                            if idx == -1: break
                            vowel_indices.add(idx + yo_pos)
                            start = idx + 1
                            
                        start = 0
                        while True:
                            idx = w.find(r_e, start)
                            if idx == -1: break
                            vowel_indices.add(idx + yo_pos)
                            start = idx + 1
                    
                    # Если найдена только одна уникальная позиция для е/ё, 
                    # значит, все совпадения корней перекрёстные и относятся к одной и той же букве.
                    if len(vowel_indices) == 1:
                        keep = False
            
            if keep:
                filtered_matching.append(w)
        
        matching = filtered_matching

        if matching: line_out = f"{combined_regex} ({':'.join(matching)})"
        else: line_out = combined_regex
        results.append(line_out)

    results.extend(yellow_add)
    unique_results = set(filter(None, results))
    sorted_results = sorted(unique_results, key=russian_sort_key)

    pattern = re.compile(r'\((.*?)\)')
    final_results = []
    for line in sorted_results:
        final_results.append(pattern.sub(expand_parentheses, line))

    with open(files["dic"], "w", encoding="utf-8") as f:
        for line in final_results:
            f.write(line + "\n")

    print(f"{Fore.GREEN}Словарь {files['dic']} для ёфикатора YoRZ сформирован (с оптимизацией).{Style.RESET_ALL}")

if __name__ == "__main__":
    run()
