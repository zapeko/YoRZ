import re
import os
from colorama import Fore, Style

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

from . import paths

def run():
    missing_files = []
    files = {
        "root": paths.get_path("dictionaries/yellow_root.txt"),
        "base": paths.get_path("dictionaries/yellow_base.txt"),
        "add": paths.get_path("dictionaries/yellow_add.txt"),
        "dic": paths.get_path("dictionaries/yellow.dic")
    }
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

    print(f"{Fore.GREEN}Словарь {files['dic']} для ёфикатора YoRZ сформирован.{Style.RESET_ALL}")

if __name__ == "__main__":
    run()
