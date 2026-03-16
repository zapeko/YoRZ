import sys
import os
from colorama import init, Fore, Style

# Инициализация colorama для корректного отображения цветов в терминале Windows
init(autoreset=True)

# Импорт модулей
try:
    from modules import typographer
    from modules import extraction
    from modules import sorting
    from modules import twin
    from modules import yellow_dic_forming
    from modules import yorz
except ImportError as e:
    print(f"{Fore.RED}Ошибка импорта модулей: {e}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Убедитесь, что вы запускаете main.py из директории modular_yorz.{Style.RESET_ALL}")
    sys.exit(1)

def print_menu():
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW} Скрипт-ёфикатор YoRZ (Модульная версия) {Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print("Выберите шаг для выполнения:")
    print(f"  {Fore.GREEN}1.{Style.RESET_ALL} Типографика (typographer) - подготовка текста")
    print(f"  {Fore.GREEN}2.{Style.RESET_ALL} Извлечение слов (extraction) - {Fore.RED}Требует ручной проверки{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}3.{Style.RESET_ALL} Сортировка базы (sorting)")
    print(f"  {Fore.GREEN}4.{Style.RESET_ALL} Поиск двойников (twin) - {Fore.RED}Требует ручной проверки{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}5.{Style.RESET_ALL} Формирование словаря (yellow_dic_forming)")
    print(f"  {Fore.GREEN}6.{Style.RESET_ALL} Ёфикация текста (YoRZ)")
    print(f"  {Fore.GREEN}0.{Style.RESET_ALL} Выход")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")

def main():
    while True:
        print_menu()
        choice = input(f"{Fore.GREEN}Ваш выбор: {Style.RESET_ALL}").strip()

        if choice == '1':
            print(f"\n{Fore.CYAN}--- Запуск типографики ---{Style.RESET_ALL}")
            filename = input("Введите имя файла (по умолчанию book.txt): ").strip()
            if not filename: filename = "book.txt"
            typographer.run(input_file=filename)
            print(f"{Fore.YELLOW}Совет: проверьте результат в {os.path.splitext(filename)[0]}_fixed.txt и переименуйте в book.txt для дальнейшей работы.{Style.RESET_ALL}")

        elif choice == '2':
            print(f"\n{Fore.CYAN}--- Запуск извлечения слов ---{Style.RESET_ALL}")
            filename = input("Введите имя файла (по умолчанию book.txt): ").strip()
            if not filename: filename = "book.txt"
            extraction.run(input_filename=filename)
            print(f"{Fore.YELLOW}ВНИМАНИЕ: Проверьте {os.path.splitext(filename)[0]}_extraction.txt, расставьте 'ё' где необходимо и добавьте в yellow_base.txt.{Style.RESET_ALL}")

        elif choice == '3':
            print(f"\n{Fore.CYAN}--- Запуск сортировки базы ---{Style.RESET_ALL}")
            filename = input("Введите имя файла базы (по умолчанию yellow_base.txt): ").strip()
            if not filename: filename = "yellow_base.txt"
            sorting.run(input_filename=filename)
            print(f"{Fore.YELLOW}ВНИМАНИЕ: Сохраните результат {os.path.splitext(filename)[0]}_sorting.txt как yellow_base.txt (перезаписав старый).{Style.RESET_ALL}")

        elif choice == '4':
            print(f"\n{Fore.CYAN}--- Поиск двойников (омографов) ---{Style.RESET_ALL}")
            twin.run()
            print(f"{Fore.YELLOW}ВНИМАНИЕ: Проверьте twin.txt и добавьте нужные пары в orange.dic.{Style.RESET_ALL}")

        elif choice == '5':
            print(f"\n{Fore.CYAN}--- Формирование словаря yellow.dic ---{Style.RESET_ALL}")
            yellow_dic_forming.run()

        elif choice == '6':
            print(f"\n{Fore.CYAN}--- Запуск Ёфикации ---{Style.RESET_ALL}")
            filename = input("Введите имя файла (по умолчанию book.txt): ").strip()
            if not filename: filename = "book.txt"
            yorz.run(input_file=filename)
            print(f"{Fore.YELLOW}Результат сохранён в {os.path.splitext(filename)[0]}_yo.html{Style.RESET_ALL}")

        elif choice == '0':
            print(f"{Fore.CYAN}Выход из программы.{Style.RESET_ALL}")
            break
        else:
            print(f"{Fore.RED}Неверный выбор. Пожалуйста, введите число от 0 до 6.{Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Программа прервана пользователем.{Style.RESET_ALL}")
        sys.exit(0)
