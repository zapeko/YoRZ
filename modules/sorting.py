import os
from colorama import Fore, Style
from modules.extraction import remove_diacritics, load_lines, extract_words, matches_condition, generate_alternatives

def run(input_filename="yellow_base.txt"):
    if not os.path.exists(input_filename):
        print(f"{Fore.RED}Файл {input_filename} не найден!{Style.RESET_ALL}")
        return

    with open(input_filename, encoding="utf-8") as f:
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

    if os.path.exists("zero.txt"):
        exclude_words = set(load_lines("zero.txt"))
    else:
        exclude_words = set()

    final_words = extracted_set - exclude_words

    ru_alphabet = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
    alphabet_order = {char: idx for idx, char in enumerate(ru_alphabet)}
    def sort_key(word):
        return [alphabet_order.get(ch, 1000) for ch in word]
    sorted_words = sorted(final_words, key=sort_key)

    base_dir = os.path.dirname(os.path.abspath(input_filename))
    base_name, _ = os.path.splitext(os.path.basename(input_filename))
    output_filename = os.path.join(base_dir, f"{base_name}_sorting.txt")

    with open(output_filename, "w", encoding="utf-8") as f:
        for word in sorted_words:
            alts = generate_alternatives(word)
            if any(alt in exclude_words for alt in alts):
                f.write(f"{word} (!)\n")
            else:
                f.write(word + "\n")

    print(f"{Fore.GREEN}Сортировка слов завершена. Результат сохранён в: {output_filename}{Style.RESET_ALL}")

if __name__ == "__main__":
    run()