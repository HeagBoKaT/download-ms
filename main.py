import eel
import requests
from bs4 import BeautifulSoup
import subprocess
import os
import logging
from urllib.parse import unquote
import re
import platform
import time
import sys

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

if getattr(sys, 'frozen', False):
    eel.init(os.path.join(sys._MEIPASS, 'web'))
else:
    eel.init('web')

@eel.expose
def process_store_link(store_url):
    try:
        logging.info(f"Начало обработки ссылки: {store_url}")
        
        system_arch = platform.machine().lower()
        if 'amd64' in system_arch or 'x86_64' in system_arch:
            target_arch = 'x64'
        else:
            return "Ошибка: Неподдерживаемая архитектура системы"
        
        logging.info(f"Архитектура системы: {system_arch}, целевая архитектура: {target_arch}")
        
        # Получаем HTML страницы с ссылками для скачивания
        post_url = "https://store.rg-adguard.net/api/GetFiles"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'type': 'url',
            'url': store_url,
            'ring': 'Retail',
            'lang': 'ru-RU'
        }
        
        response = requests.post(post_url, headers=headers, data=data)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # В разделе поиска файлов
        allowed_extensions = ('.appx', '.msixbundle', '.exe')
        exclude_keywords = ['framework', 'vclibs', 'runtime', 'dependency', 'ui.xaml', 'xaml.ui', 'microsoft.ui', 'webinstaller']

        appx_link = None
        current_max_size = 0
        for tr in soup.select('tr'):
            row_text = tr.text.lower()
            if any(ext in row_text for ext in allowed_extensions):
                # Для нейтральных пакетов пропускаем проверку архитектуры
                is_neutral = '_neutral_' in row_text
                arch_check = target_arch in row_text or is_neutral
                
                if not arch_check:
                    logging.debug(f"Пропуск пакета: несовпадение архитектуры. Текст: {row_text}")
                    continue
                
                # Проверка исключений
                if any(keyword in row_text for keyword in exclude_keywords):
                    logging.debug(f"Пропуск пакета: содержит исключенное ключевое слово. Текст: {row_text}")
                    continue
                
                # Получаем размер в мегабайтах
                size_str = tr.select('td')[1].text.lower()
                multiplier = 1
                if 'gb' in size_str:
                    multiplier = 1024
                size = float(''.join(c for c in size_str if c.isdigit() or c == '.')) * multiplier
                
                # Выбираем самый большой подходящий пакет
                if size > current_max_size:
                    appx_link = tr.select_one('a')['href']
                    current_max_size = size
                    logging.debug(f"Текущий кандидат: {appx_link} | Размер: {size} MB")
                
        if not appx_link:
            return f"Ошибка: Основной APPX/MSIXBUNDLE для {target_arch} не найден"
            
        logging.info(f"Найден APPX-файл: {appx_link}")
        
        # Обрабатываем URL и имя файла
        file_part = unquote(appx_link.split('?')[0])
        file_name = re.sub(r'[^\w\d._~-]', '', file_part.split('/')[-1])  # Разрешаем тильду
        file_name = file_name.replace('__', '_').replace('_.', '.')  # Чистим дубли подчеркиваний
        
        # Удаляем лишние части в нейтральных пакетах
        if '_neutral_' in file_name:
            file_name = file_name.split('_neutral_')[0] + '.msixbundle'
        
        logging.info(f"Скачивание файла как: {file_name}")
        
        # Скачиваем файл
        with requests.get(appx_link, stream=True) as r:
            r.raise_for_status()
            
            total_size = int(r.headers.get('content-length', 0))
            downloaded = 0
            start_time = time.time()
            last_update = 0
            
            with open(file_name, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Обновляем прогресс не чаще 5 раз в секунду
                    now = time.time()
                    if now - last_update > 0.2 or downloaded == total_size:
                        speed = downloaded / (now - start_time) if (now - start_time) > 0 else 0
                        progress = (downloaded / total_size) * 100 if total_size > 0 else 0
                        remaining = (total_size - downloaded) / speed if speed > 0 and total_size > 0 else 0
                        
                        # Принудительно устанавливаем 100% при завершении
                        if downloaded == total_size and total_size > 0:
                            progress = 100
                            remaining = 0
                        
                        eel.update_download_progress(progress, speed, total_size, remaining) 
                        last_update = now
            
            # Гарантированно отправляем 100% после завершения
            eel.update_download_progress(100, 0, total_size, 0)
        
        logging.info(f"Файл {file_name} успешно скачан")
        
        # Определяем команду установки в зависимости от типа файла
        if file_name.lower().endswith('.exe'):
            ps_command = f'Start-Process -FilePath "{os.path.abspath(file_name)}" -ArgumentList "/S" -Wait -WindowStyle Hidden'
            install_command = [
                'powershell',
                '-WindowStyle', 'Hidden',
                '-Command',
                f'Start-Process powershell -WindowStyle Hidden -ArgumentList \'-NoProfile -WindowStyle Hidden -Command "{ps_command}"\' -Verb RunAs'
            ]
        else:
            ps_command = (
                f'Add-AppxPackage -Path "{os.path.abspath(file_name)}" '
                '-ErrorAction Stop -ForceApplicationShutdown'
            )
            install_command = [
                'powershell',
                '-WindowStyle', 'Hidden',
                '-Command',
                f'$process = Start-Process powershell -WindowStyle Hidden -ArgumentList \'-NoProfile -WindowStyle Hidden -Command {ps_command}\' -Verb RunAs -PassThru -Wait; exit $process.ExitCode'
            ]
        
        logging.info("Запуск установки через PowerShell: " + ps_command)
        eel.start_installation()
        
        # Показываем прогресс для всех типов установки
        for i in range(1, 101):
            time.sleep(0.1)
            eel.update_install_progress(i)
        
        result = subprocess.run(
            install_command,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        if result.returncode != 0:
            logging.error(f"Ошибка установки: {result.stderr}")
            # Удаляем файл при ошибке
            cleanup_file(file_name)
            return f"Ошибка установки: {result.stderr}"
        else:
            logging.info("Установка завершена успешно")
            
            # Проверяем зависимости
            deps_command = f'Get-AppxPackage -Path "{os.path.abspath(file_name)}" | ForEach-Object {{ $_.Dependencies }}'
            deps_result = subprocess.run(
                ['powershell', '-WindowStyle', 'Hidden', '-Command', deps_command],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Удаляем файл после успешной установки
            cleanup_file(file_name)
            
            if 'Microsoft.UI.Xaml' in deps_result.stdout:
                return "Ошибка: Требуется установить Microsoft.UI.Xaml.2.8 отдельно"
            
            return "Приложение успешно установлено!"
        
    except Exception as e:
        logging.error(f"Критическая ошибка: {str(e)}", exc_info=True)
        # Удаляем файл при исключении
        cleanup_file(file_name)
        return f"Произошла ошибка: {str(e)}"

def cleanup_file(filename):
    try:
        if os.path.exists(filename):
            os.remove(filename)
            logging.info(f"Временный файл {filename} удален")
    except Exception as e:
        logging.warning(f"Не удалось удалить файл {filename}: {str(e)}")

eel.start(
    'index.html',
    mode='edge',
    size=(800, 600),
    port=0,
    cmdline_args=[
        '--disable-context-menu',
        '--window-size=800,600',
        '--disable-window-resize',
        '--no-first-run',
        '--single-process'
    ]
) 