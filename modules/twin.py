import re
import os
from colorama import Fore, Style

def parse_ignore_patterns(ignore_file):
    ignore_patterns = []
    if not os.path.exists(ignore_file):
        return ignore_patterns
    with open(ignore_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            exclusion_list = []
            if '(' in line:
                pattern_part, exclusion_part = line.split('(', 1)
                pattern_part = pattern_part.strip()
                exclusion_part = exclusion_part.rstrip(')').strip()
                if exclusion_part:
                    exclusion_list = [excl.strip() for excl in exclusion_part.split(':') if excl.strip()]
            else:
                pattern_part = line.strip()
            if '|' not in pattern_part: continue
            left_pattern, right_pattern = pattern_part.split('|', 1)
            left_pattern, right_pattern = left_pattern.strip(), right_pattern.strip()
            try:
                left_re = re.compile("^" + left_pattern + "$", re.UNICODE)
                right_re = re.compile("^" + right_pattern + "$", re.UNICODE)
            except re.error as e:
                print(f"Ошибка компиляции regex для шаблона: {pattern_part} — {e}")
                continue
            ignore_patterns.append((left_re, right_re, exclusion_list))
    return ignore_patterns

def find_word_pairs(input_file='yellow_base.txt', output_file='twin.txt', ignore_file='orange.dic'):
    if not os.path.exists(input_file):
        print(f"{Fore.RED}Файл {input_file} не найден!{Style.RESET_ALL}")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.read()

    words = re.findall(r'\b[а-яА-ЯёЁ]+\b', text)
    word_set = set(words)
    pairs = set()

    for word in word_set:
        if ('ё' in word) or ('Ё' in word): continue
        if ('е' not in word) and ('Е' not in word): continue
        for i, char in enumerate(word):
            if char == 'е':
                candidate = word[:i] + 'ё' + word[i+1:]
                if candidate in word_set: pairs.add((word, candidate))
            elif char == 'Е':
                candidate = word[:i] + 'Ё' + word[i+1:]
                if candidate in word_set: pairs.add((word, candidate))

    ignore_patterns = parse_ignore_patterns(ignore_file)
    final_pairs = []

    for left, right in pairs:
        twin_str = f"{left}|{right}"
        remove = False
        for left_re, right_re, exclusions in ignore_patterns:
            if left_re.match(left) and right_re.match(right):
                if exclusions:
                    if not any(excl in twin_str for excl in exclusions):
                        remove = True
                        break
                else:
                    remove = True
                    break
        if not remove:
            final_pairs.append((left, right))

    with open(output_file, 'w', encoding='utf-8') as f:
        for left, right in sorted(final_pairs):
            f.write(f"{left}|{right}\n")

    print(f"{Fore.GREEN}Поиск пар завершён. Результат сохранён в: {output_file}{Style.RESET_ALL}")

def run(input_file='yellow_base.txt', output_file='twin.txt', ignore_file='orange.dic'):
    find_word_pairs(input_file, output_file, ignore_file)

if __name__ == '__main__':
    run()