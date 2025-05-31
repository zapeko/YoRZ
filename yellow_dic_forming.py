# -*- coding: utf-8 -*-
import re
from colorama import init, Fore, Style

def russian_sort_key(s):
    """
    Формирует сортировочный ключ для строки s так, что если она начинается с символов
    "\", "w" или "*", они игнорируются при сравнении.
    Остальные символы обрабатываются по порядку русского алфавита, где буква "ё" идёт сразу после "е".
    """
    special = {"\\", "w", "*"}
    i = 0
    while i < len(s) and s[i] in special:
        i += 1
    trimmed = s[i:].lower()

    russian_alphabet = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
    order_map = {char: idx for idx, char in enumerate(russian_alphabet)}

    key = []
    for ch in trimmed:
        if ch in order_map:
            key.append(order_map[ch])
        else:
            # Символы, не входящие в русский алфавит, сдвигаем так, чтобы они шли после букв.
            key.append(len(russian_alphabet) + ord(ch))
    return tuple(key)


def generate_analog_variants(word):
    """
    Если слово содержит хотя бы одну букву "ё" И в нем встречается хотя бы одна буква "е",
    генерирует список аналогов, полученных заменой «ё» на «е» для каждого непустого набора вхождений.

    Например, для слова с одной "ё" вернёт список из одного элемента,
    для слова с двумя "ё" – список из трёх вариантов (даже если какие-то варианты совпадают),
    для слова с тремя – из (2^3 - 1)=7 вариантов.
    """
    indices = [i for i, ch in enumerate(word) if ch == "ё"]
    if not indices:
        return []
    # Если кроме "ё" в слове нет ни одной буквы "е", аналогов не надо дописывать.
    if "е" not in word:
        return []
    variants = []
    n = len(indices)
    # Перебираем все непустые подмножества вхождений (маски от 1 до 2^n - 1)
    for mask in range(1, 2**n):
        chars = list(word)
        for j in range(n):
            if mask & (1 << j):
                pos = indices[j]
                chars[pos] = "е"
        variant = "".join(chars)
        # Добавляем вариант, даже если он совпадает с другим (как в примере для двух "ё")
        if variant != word:
            variants.append(variant)
    return variants


def expand_parentheses(match):
    """
    В найденном в круглых скобках содержимом (группа символов без скобок)
    разбиваем по разделителю ":" и для каждого токена, если он содержит хотя бы одну "ё"
    И в нём встречается хотя бы одна "е", дописываем через ":" все его аналоги, полученные
    заменой "ё" на "е".

    Возвращаем обновлённую группу в круглых скобках.
    """
    content = match.group(1)
    tokens = content.split(":")
    new_tokens = []
    for token in tokens:
        token = token.strip()
        # Если слово содержит "ё" и где-то есть "е", то расширяем его аналогами.
        if "ё" in token and "е" in token:
            analogs = generate_analog_variants(token)
            # Собираем слово: оригинальное + все аналоги через ":"
            token_expanded = token + (":" + ":".join(analogs) if analogs else "")
            new_tokens.append(token_expanded)
        else:
            new_tokens.append(token)
    return "(" + ":".join(new_tokens) + ")"


# Чтение строк из файлов
with open("yellow_root.txt", "r", encoding="utf-8") as f:
    yellow_root = [line.strip() for line in f if line.strip()]

with open("yellow_base.txt", "r", encoding="utf-8") as f:
    yellow_base = [line.strip() for line in f if line.strip()]

with open("yellow_add.txt", "r", encoding="utf-8") as f:
    yellow_add = [line.strip() for line in f if line.strip()]

results = []

for word in yellow_root:
    # Обрабатываем только строки, содержащие букву "ё"
    if "ё" not in word:
        continue

    # Получаем вариант слова, где "ё" заменены на "е"
    replaced = word.replace("ё", "е")

    # Формируем регулярное выражение и ищем совпадения в yellow_base.txt
    if word.startswith("ё"):
        regex_original = word + r'\w*'
        regex_replaced = replaced + r'\w*'
        combined_regex = regex_replaced + "|" + regex_original
        # Поиск по словам, начинающимся с фрагмента replaced
        matching = [w for w in yellow_base if w.startswith(replaced)]
    elif word.endswith("ё"):
        regex_original = r'\w*' + word
        regex_replaced = r'\w*' + replaced
        combined_regex = regex_replaced + "|" + regex_original
        # Поиск по словам, оканчивающимся на фрагмент replaced
        matching = [w for w in yellow_base if w.endswith(replaced)]
    elif "ё" in word[1:-1]:
        regex_original = r'\w*' + word + r'\w*'
        regex_replaced = r'\w*' + replaced + r'\w*'
        combined_regex = regex_replaced + "|" + regex_original
        # Поиск по словам, содержащим фрагмент replaced в любом месте
        matching = [w for w in yellow_base if replaced in w]
    else:
        continue

    # Формируем итоговую строку: если найдены совпадения – добавляем их в круглых скобках через ":"
    if matching:
        line_out = f"{combined_regex} ({':'.join(matching)})"
    else:
        line_out = combined_regex

    results.append(line_out)

# Добавляем строки из файла yellow_add.txt (без поиска в yellow_base.txt)
results.extend(yellow_add)

# Удаляем дубликаты и пустые строки
unique_results = set(filter(None, results))

# Сортировка по русской азбуке с использованием функции russian_sort_key
sorted_results = sorted(unique_results, key=russian_sort_key)

# На последней стадии в каждой строке ищем содержимое в круглых скобках и обрабатываем его
pattern = re.compile(r'\((.*?)\)')
final_results = []
for line in sorted_results:
    new_line = pattern.sub(expand_parentheses, line)
    final_results.append(new_line)

# Записываем итоговые строки в файл yellow.dic
with open("yellow.dic", "w", encoding="utf-8") as f:
    for line in final_results:
        f.write(line + "\n")

print(f"{Fore.GREEN}Словарь yellow.dic для скрипта-ёфикатора YoRZ сформирован.{Style.RESET_ALL}")
