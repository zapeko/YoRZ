import os
from colorama import Fore, Style
from modules.extraction import remove_diacritics, load_lines, extract_words, matches_condition
from . import paths

def run(input_filename=None):
    if not input_filename:
        input_filename = paths.get_path("dictionaries/yellow_base.txt")
    
    if not os.path.exists(input_filename):
        print(f"{Fore.RED}Файл {input_filename} не найден!{Style.RESET_ALL}")
        return

    # Читаем весь текст файла
    try:
        with open(input_filename, "r", encoding="utf-8") as f:
            content = f.read().lower()
    except Exception as e:
        print(f"{Fore.RED}Ошибка при чтении файла {input_filename}: {e}{Style.RESET_ALL}")
        return

    # Удаляем диакритические знаки (кроме нужных нам)
    content = remove_diacritics(content)

    # Загружаем корни для фильтрации
    try:
        raw_roots = load_lines(paths.get_path("dictionaries/yellow_root.txt"))
    except FileNotFoundError:
        print(f"{Fore.RED}Файл yellow_root.txt не найден! Пропускаю фильтрацию по корням.{Style.RESET_ALL}")
        raw_roots = []

    roots_tuples = []
    for r in raw_roots:
        if not r: continue
        r_variant = r.replace("ё", "е")
        roots_tuples.append((r, r_variant))

    # Извлекаем только слова (это автоматически удаляет комментарии и заголовки)
    words = extract_words(content)

    # Фильтруем слова: оставляем только те, что содержат корни (если корни загружены)
    extracted_set = set()
    if roots_tuples:
        for word in words:
            for r, r_variant in roots_tuples:
                if matches_condition(word, r, r_variant):
                    extracted_set.add(word)
                    break
    else:
        # Если корней нет, просто берем все уникальные слова
        extracted_set = set(words)

    # Правильная сортировка (ё идет после е)
    ru_alphabet = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
    alphabet_order = {char: idx for idx, char in enumerate(ru_alphabet)}
    
    def sort_key(word):
        return [alphabet_order.get(ch, 1000) for ch in word]
    
    sorted_words = sorted(list(extracted_set), key=sort_key)

    # Перезаписываем исходный файл
    try:
        with open(input_filename, "w", encoding="utf-8") as f:
            for word in sorted_words:
                f.write(word + "\n")
        print(f"{Fore.GREEN}Сортировка и фильтрация завершены. Файл {os.path.basename(input_filename)} успешно перезаписан.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Ошибка при записи файла {input_filename}: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    run()
