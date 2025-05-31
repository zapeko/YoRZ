import os
import re
import unicodedata
from colorama import init, Fore, Style

def remove_diacritics(text):
    """
    Нормализует текст (NFD) и удаляет все комбинированные диакритические знаки,
    за исключением знаков, необходимых для букв "ё" и "й".
    После обработки выполняется рекомпозиция (NFC).
    """
    nfd_text = unicodedata.normalize("NFD", text)
    result_chars = []
    i = 0
    while i < len(nfd_text):
        ch = nfd_text[i]
        if unicodedata.category(ch) != "Mn":  # базовый символ
            cluster = [ch]
            i += 1
            while i < len(nfd_text) and unicodedata.category(nfd_text[i]) == "Mn":
                cluster.append(nfd_text[i])
                i += 1
            if ch == "е" and "\u0308" in cluster[1:]:
                result_chars.extend(cluster)
            elif ch == "и" and "\u0306" in cluster[1:]:
                result_chars.extend(cluster)
            else:
                result_chars.append(ch)
        else:
            i += 1
    return unicodedata.normalize("NFC", "".join(result_chars))

def load_lines(filename):
    """Загружает непустые строки из файла, удаляя лишние пробельные символы."""
    with open(filename, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def extract_words(text):
    """Извлекает слова, состоящие только из кириллических символов (включая букву ё)."""
    return re.findall(r"[а-яё]+", text)

def matches_condition(word, root, root_variant):
    """
    Проверяет, содержит ли слово заданный трёхбуквенный корень (в оригинале или с заменой "ё" на "е")
    с учётом ограничений:
      — Если корень начинается с "ё", он допустим только в начале слова.
      — Если корень заканчивается на "ё", он допустим только в конце слова.
      — Если "ё" находится в центре, проверяется вхождение по всему слову.
    """
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
    """
    Генерирует все варианты слова, полученные заменой каждой буквы "е" на "ё" и наоборот.
    Исходный вариант не включается.
    """
    alternatives = set()

    def rec(current, index):
        if index == len(word):
            variant = "".join(current)
            if variant != word:
                alternatives.add(variant)
            return
        ch = word[index]
        if ch in {"е", "ё"}:
            # оставить букву без изменений
            rec(current + [ch], index + 1)
            # заменить букву на альтернативную
            alt = "ё" if ch == "е" else "е"
            rec(current + [alt], index + 1)
        else:
            rec(current + [ch], index + 1)

    rec([], 0)
    return alternatives

def main():
    # Задаём имя входного файла через переменную input_filename
    input_filename = "yellow_base.txt"

    # Шаг 1. Читаем файл, указанный в input_filename, и переводим текст в нижний регистр.
    with open(input_filename, encoding="utf-8") as f:
        text = f.read().lower()

    # Шаг 2. Удаляем диакритические знаки, оставляя их для "ё" и "й".
    text = remove_diacritics(text)

    # Шаг 3. Загружаем список корней из файла yellow-root.txt и формируем для каждого вариант с заменой "ё" на "е".
    raw_roots = load_lines("yellow_root.txt")
    roots_tuples = []
    for r in raw_roots:
        if not r:
            continue
        r_variant = r.replace("ё", "е")
        roots_tuples.append((r, r_variant))

    # Извлекаем все слова из исходного текста.
    words = extract_words(text)

    # Шаг 4. Извлекаем слова, содержащие хотя бы один из трёхбуквенных корней.
    extracted_set = set()
    for word in words:
        for r, r_variant in roots_tuples:
            if matches_condition(word, r, r_variant):
                extracted_set.add(word)
                break  # достаточно одного подходящего корня

    # Шаг 5. Пытаемся загрузить список исключаемых слов из файла yellow-base.txt.
    # Если файла нет, то пропускаем проверку, оставляя exclude_words пустым.
    if os.path.exists("zero.txt"):
        exclude_words = set(load_lines("zero.txt"))
    else:
        exclude_words = set()

    final_words = extracted_set - exclude_words

    # Шаг 6. Сортировка итоговых слов по русской азбуке,
    # где буква "ё" идёт сразу после "е".
    ru_alphabet = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
    alphabet_order = {char: idx for idx, char in enumerate(ru_alphabet)}
    def sort_key(word):
        return [alphabet_order.get(ch, 1000) for ch in word]
    sorted_words = sorted(final_words, key=sort_key)

    # Шаг 7. Формируем имя выходного файла на основе input_filename с суффиксом _extraction.txt.
    base_name, _ = os.path.splitext(input_filename)
    output_filename = f"{base_name}_sorting.txt"

    # Шаг 8. Записываем каждое слово на новой строке.
    # Если имеется хотя бы один альтернативный вариант (с заменой "ё" на "е" или наоборот)
    # из exclude_words, добавляем пометку " (!)" после слова.
    with open(output_filename, "w", encoding="utf-8") as f:
        for word in sorted_words:
            alts = generate_alternatives(word)
            if any(alt in exclude_words for alt in alts):
                f.write(f"{word} (!)\n")
            else:
                f.write(word + "\n")

    # По завершении обработки выводим сообщение в терминал.
    print(f"{Fore.GREEN}Сортировка слов завершена. Результат сохранён в: {output_filename}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
