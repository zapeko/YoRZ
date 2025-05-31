import re
from colorama import init, Fore, Style

def parse_ignore_patterns(ignore_file):
    """
    Считывает файл orange.dic, игнорируя пустые строки и строки, начинающиеся с "#".
    Из каждой строки извлекает часть с шаблоном (левая и правая части, разделённые символом "|")
    и, если указаны, список слов-исключений внутри круглых скобок (разделённые двоеточием).
    Результат – список кортежей: (left_regex, right_regex, [exclusion_words]).
    """
    ignore_patterns = []
    with open(ignore_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            exclusion_list = []
            # Если указаны слова-исключения, они находятся в круглых скобках
            if '(' in line:
                # Разбиваем на часть с шаблоном и часть с исключениями.
                pattern_part, exclusion_part = line.split('(', 1)
                pattern_part = pattern_part.strip()
                # Убираем завершающую скобку и лишние пробелы
                exclusion_part = exclusion_part.rstrip(')').strip()
                if exclusion_part:
                    # Если несколько исключений, они разделяются символом ":"
                    exclusion_list = [excl.strip() for excl in exclusion_part.split(':') if excl.strip()]
            else:
                pattern_part = line.strip()

            # Шаблон представляет собой две части, разделённые символом "|"
            if '|' not in pattern_part:
                continue  # пропускаем некорректные записи
            left_pattern, right_pattern = pattern_part.split('|', 1)
            left_pattern = left_pattern.strip()
            right_pattern = right_pattern.strip()

            # Компилируем обе части как регекс с якорями (^...$)
            try:
                left_re = re.compile("^" + left_pattern + "$", re.UNICODE)
                right_re = re.compile("^" + right_pattern + "$", re.UNICODE)
            except re.error as e:
                print(f"Ошибка компиляции regex для шаблона: {pattern_part} — {e}")
                continue

            ignore_patterns.append((left_re, right_re, exclusion_list))
    return ignore_patterns

def find_word_pairs(input_file, output_file, ignore_file):
    """
    1. Считывает файл yellow_base.txt, извлекает все слова (учитывая буквы ё/Ё) и формирует из них набор.
    2. Для каждого слова, содержащего букву "е" (но не содержащее букву "ё"),
       перебирает все позиции, заменяя одну букву "е" на "ё". Если полученный вариант есть в наборе,
       добавляет пару (вариант с "е", вариант с "ё") в результирующее множество.
    3. Считывает список шаблонов из orange.dic (см. функцию parse_ignore_patterns).
    4. Для каждой полученной пары вида "слово_с_е|слово_с_ё" проверяет – если левая и правая части удовлетворяют
       шаблонам из какой-либо записи orange.dic и при этом строка не содержит ни одного из исключений (если они заданы),
       то такую пару исключает из итогового результата.
    5. Оставшиеся пары записываются в файл twin.txt, каждая пара – на отдельной строке.
    """
    # Читаем содержимое файла yellow_base.txt
    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.read()

    # Извлекаем слова, состоящие только из русских букв (учитываются буквы ё/Ё)
    words = re.findall(r'\b[а-яА-ЯёЁ]+\b', text)
    word_set = set(words)

    pairs = set()
    # Перебираем все уникальные слова
    for word in word_set:
        # Отбираем те слова, где есть буква "е"/"Е", но нет буквы "ё"/"Ё"
        if ('ё' in word) or ('Ё' in word):
            continue
        if ('е' not in word) and ('Е' not in word):
            continue
        # Для каждого символа "е"/"Е" пытаемся создать вариант с "ё"/"Ё"
        for i, char in enumerate(word):
            if char == 'е':
                candidate = word[:i] + 'ё' + word[i+1:]
                if candidate in word_set:
                    pairs.add((word, candidate))
            elif char == 'Е':
                candidate = word[:i] + 'Ё' + word[i+1:]
                if candidate in word_set:
                    pairs.add((word, candidate))

    # Считываем шаблоны-исключения из файла orange.dic
    ignore_patterns = parse_ignore_patterns(ignore_file)

    # Фильтр по orange.dic:
    # Если пара (left, right) удовлетворяет шаблону (то есть left и right совпадают с соответствующими regex)
    # и при этом итоговая строка, сформированная как "left|right", не содержит ни одного слова-исключения (если они заданы)
    # – такую пару будем исключать (то есть не запишем в twin.txt)
    final_pairs = []
    for left, right in pairs:
        twin_str = f"{left}|{right}"
        remove = False
        for left_re, right_re, exclusions in ignore_patterns:
            if left_re.match(left) and right_re.match(right):
                # Если заданы исключения – проверяем, встречается ли любое из них в строке.
                # Если ни одно не найдено, пара подлежит удалению.
                if exclusions:
                    if not any(excl in twin_str for excl in exclusions):
                        remove = True
                        break
                else:
                    remove = True
                    break
        if not remove:
            final_pairs.append((left, right))

    # Записываем итоговые пары в файл twin.txt, каждая пара в виде "слово_с_е|слово_с_ё"
    with open(output_file, 'w', encoding='utf-8') as f:
        for left, right in sorted(final_pairs):
            f.write(f"{left}|{right}\n")

    # По завершении обработки выводим сообщение в терминал.
    print(f"{Fore.GREEN}Поиск пар завершён. Результат сохранён в: twin.txt{Style.RESET_ALL}")

if __name__ == '__main__':
    find_word_pairs('yellow_base.txt', 'twin.txt', 'orange.dic')
