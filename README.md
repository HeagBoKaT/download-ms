# StoreDownloader

Приложение для скачивания и установки приложений из Microsoft Store миную сам Store.

Ссылки можно брать с офф. сайта.

## 📦 Установка

1. Установите Python 3.10+ с [официального сайта](https://www.python.org/)
2. Клонируйте репозиторий:
```bash
git clone https://github.com/download-ms.git
```
3. Установите зависимости:
```bash
pip install -r requirements.txt
```

## 🛠 Сборка exe
```bash
pyinstaller build.spec
```

## 🚀 Использование
1. Запустите main.py или собранный exe-файл
2. Вставьте ссылку на приложение из Microsoft Store
3. Дождитесь завершения скачивания и установки

## ⚙️ Особенности
- Автоматическое определение архитектуры системы
- Прогресс бар скачивания и установки
- Автоочистка временных файлов
- Проверка зависимостей после установки

## 📌 Системные требования
- Windows 10/11 x64
- .NET Framework 4.8+
- PowerShell 5.1+
