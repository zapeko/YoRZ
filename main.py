import sys
import os
import json
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
    from modules import paths
    
    # Инициализация путей в %APPDATA%
    paths.ensure_user_data_exists()
except ImportError as e:
    print(f"{Fore.RED}Ошибка импорта модулей: {e}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Убедитесь, что вы запускаете main.py из директории modular_yorz.{Style.RESET_ALL}")
    sys.exit(1)

def load_settings():
    default_settings = {
        "typo_zwnbsp": True,
        "typo_html_nbsp": True,
        "typo_nbsp": True,
        "typo_shy": True,
        "typo_spaces": False,
        "typo_letter_digit_spaces": False,
        "typo_punctuation": True,
        "typo_dashes": True,
        "typo_merge_lines": False,
        "typo_keep_leading_dashes": False,
        "typo_remove_all_empty": False,
        "typo_deyo": True,
        "sync_on_extraction": True,
        "combine_processes": False
    }
    settings_file = os.path.join(paths.USER_DATA_DIR, "yorz_settings.json")
    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                default_settings.update(loaded)
        except Exception:
            pass
    else:
        # Если файла нет, создаем его с настройками по умолчанию,
        # чтобы пользователь консольной версии мог его редактировать вручную.
        try:
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(default_settings, f, indent=4)
        except Exception as e:
            print(f"{Fore.RED}Ошибка при создании файла настроек: {e}{Style.RESET_ALL}")
            
    return default_settings

def print_menu():
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW} Скрипт-ёфикатор YoRZ (Модульная версия) {Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print("Выберите шаг для выполнения:")
    print(f"  {Fore.GREEN}1.{Style.RESET_ALL} Типографика (typographer) - подготовка текста")
    print(f"  {Fore.GREEN}2.{Style.RESET_ALL} Извлечение слов (extraction) - {Fore.RED}Требует ручной проверки{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}3.{Style.RESET_ALL} Сортировка базы (sorting)")
    print(f"  {Fore.GREEN}4.{Style.RESET_ALL} Поиск двойников (twin) - пополняет orange.dic")
    print(f"  {Fore.GREEN}5.{Style.RESET_ALL} Формирование словаря (yellow_dic_forming)")
    print(f"  {Fore.GREEN}6.{Style.RESET_ALL} Ёфикация текста (YoRZ)")
    print(f"  {Fore.GREEN}7.{Style.RESET_ALL} Синхронизировать словари (обновить базу)")
    print(f"  {Fore.GREEN}8.{Style.RESET_ALL} Открыть папку со словарями пользователя")
    print(f"  {Fore.GREEN}0.{Style.RESET_ALL} Выход")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")

def main():
    while True:
        print_menu()
        choice = input(f"{Fore.GREEN}Ваш выбор: {Style.RESET_ALL}").strip()
        
        settings = load_settings()

        if choice == '1':
            print(f"\n{Fore.CYAN}--- Запуск типографики ---{Style.RESET_ALL}")
            filename = input("Введите имя файла (по умолчанию book.txt): ").strip()
            if not filename: filename = "book.txt"
            
            options = {
                'zwnbsp': settings.get('typo_zwnbsp', True),
                'html_nbsp': settings.get('typo_html_nbsp', True),
                'nbsp': settings.get('typo_nbsp', True),
                'shy': settings.get('typo_shy', True),
                'spaces': settings.get('typo_spaces', True),
                'letter_digit_spaces': settings.get('typo_letter_digit_spaces', True),
                'punctuation': settings.get('typo_punctuation', True),
                'dashes': settings.get('typo_dashes', True),
                'merge_lines': settings.get('typo_merge_lines', True),
                'keep_leading_dashes': settings.get('typo_keep_leading_dashes', False),
                'remove_all_empty': settings.get('typo_remove_all_empty', False),
                'deyo': settings.get('typo_deyo', False)
            }
            
            typographer.run(input_file=filename, options=options)
            print(f"{Fore.YELLOW}Совет: проверьте результат в {os.path.splitext(filename)[0]}_fixed.txt и переименуйте в book.txt для дальнейшей работы.{Style.RESET_ALL}")

        elif choice == '2':
            print(f"\n{Fore.CYAN}--- Запуск извлечения слов ---{Style.RESET_ALL}")
            filename = input("Введите имя файла (по умолчанию book.txt): ").strip()
            if not filename: filename = "book.txt"
            
            if settings.get("sync_on_extraction", True):
                print(f"{Fore.YELLOW}Фоновая синхронизация словарей перед извлечением...{Style.RESET_ALL}")
                def cli_sync_progress(msg):
                    print(f"  [SYNC] {msg}")
                try:
                    paths.initialize_user_data(verbose=False)
                    paths.sync_dictionaries_from_github(progress_callback=cli_sync_progress)
                except Exception as sync_e:
                    print(f"{Fore.RED}[SYNC ERROR] Не удалось выполнить фоновую синхронизацию: {sync_e}{Style.RESET_ALL}")
                print(f"{Fore.GREEN}Синхронизация завершена. Начинаю извлечение слов...{Style.RESET_ALL}\n")
                
            extraction.run(input_filename=filename)
            print(f"{Fore.YELLOW}ВНИМАНИЕ: Проверьте {os.path.splitext(filename)[0]}_extraction.txt, расставьте 'ё' где необходимо и добавьте в yellow_base.txt.{Style.RESET_ALL}")

        elif choice == '3':
            print(f"\n{Fore.CYAN}--- Запуск сортировки базы ---{Style.RESET_ALL}")
            default_base = paths.get_path("dictionaries/yellow_base.txt")
            filename = input(f"Введите путь к файлу базы (по умолчанию {default_base}):\n> ").strip()
            if not filename: filename = default_base
            sorting.run(input_filename=filename)
            print(f"{Fore.YELLOW}Готово. Файл базы был перезаписан отсортированными данными.{Style.RESET_ALL}")

        elif choice == '4':
            print(f"\n{Fore.CYAN}--- Поиск двойников (омографов) ---{Style.RESET_ALL}")
            twin.run()
            print(f"{Fore.YELLOW}Готово. Новые пары омографов добавлены в orange.dic.{Style.RESET_ALL}")

        elif choice == '5':
            print(f"\n{Fore.CYAN}--- Формирование словаря yellow.dic ---{Style.RESET_ALL}")
            yellow_dic_forming.run()

        elif choice == '6':
            print(f"\n{Fore.CYAN}--- Запуск Ёфикации ---{Style.RESET_ALL}")
            filename = input("Введите имя файла (по умолчанию book.txt): ").strip()
            if not filename: filename = "book.txt"
            yorz.run(input_file=filename)
            print(f"{Fore.YELLOW}Результат сохранён в {os.path.splitext(filename)[0]}_yo.html{Style.RESET_ALL}")
            
        elif choice == '7':
            print(f"\n{Fore.CYAN}--- Онлайн-синхронизация словарей с GitHub ---{Style.RESET_ALL}")
            # Сначала локальная синхронизация на всякий случай (без лишнего вывода)
            paths.initialize_user_data(verbose=False)

            def cli_progress(msg):
                color = Fore.GREEN if "завершена" in msg else Fore.YELLOW
                if "Ошибка" in msg: color = Fore.RED
                print(f"{color}{msg}{Style.RESET_ALL}")
                
            if not paths.sync_dictionaries_from_github(progress_callback=cli_progress):
                print(f"{Fore.RED}Онлайн-синхронизация завершилась с ошибкой.{Style.RESET_ALL}")

        elif choice == '8':
            print(f"\n{Fore.CYAN}--- Открытие папки со словарями ---{Style.RESET_ALL}")
            paths.open_user_data_dir()
            print(f"{Fore.YELLOW}Папка открыта.{Style.RESET_ALL}")

        elif choice == '0':
            print(f"{Fore.CYAN}Выход из программы.{Style.RESET_ALL}")
            break
        else:
            print(f"{Fore.RED}Неверный выбор. Пожалуйста, введите число от 0 до 7.{Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Программа прервана пользователем.{Style.RESET_ALL}")
        sys.exit(0)
