import requests
import json
import os
from tqdm import tqdm
import time


def download_documents():
    # Базовый URL API
    base_api_url = "http://publication.pravo.gov.ru/api/Documents"

    # Параметры запроса с PageSize
    params = {
        "DocumentTypes": "7ff5b3b5-3757-44f1-bb76-3766cabe3593",
        "SignatoryAuthorityId": "8005d8c9-4b6d-48d3-861a-2a37e69fccb3",
        "PublishDateSearchType": "0",
        "NumberSearchType": "0",
        "DocumentDateSearchType": "0",
        "DocumentDateFrom": "16.10.2025",
        "DocumentDateTo": "31.10.2025",
        "JdRegSearchType": "0",
        "SortedBy": "6",
        "SortDestination": "0",
        "PageSize": "30",  # Добавляем PageSize
        "index": "1"  # Начинаем с первой страницы
    }

    print("Параметры запроса:")
    for key, value in params.items():
        print(f"  {key}: {value}")

    # Создаем папку для сохранения документов
    download_dir = "downloaded_documents"
    os.makedirs(download_dir, exist_ok=True)

    all_items = []  # Здесь будем хранить все документы со всех страниц

    try:
        # Получаем информацию о количестве страниц
        print("\nПолучаем информацию о количестве страниц...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
        }

        # Сначала делаем запрос, чтобы узнать общее количество страниц
        first_page_response = requests.get(
            base_api_url,
            params=params,
            headers=headers,
            timeout=30
        )

        first_page_response.raise_for_status()
        first_page_data = first_page_response.json()

        # Получаем информацию о пагинации
        total_count = first_page_data.get('totalCount', 0)
        page_size = first_page_data.get('pageSize', 200)
        pages_total_count = first_page_data.get('pagesTotalCount', 1)

        print(f"Всего документов: {total_count}")
        print(f"Размер страницы: {page_size}")
        print(f"Всего страниц: {pages_total_count}")

        # Собираем данные со всех страниц
        print(f"\nСобираем данные со всех {pages_total_count} страниц...")

        for index in range(1, pages_total_count + 1):
            print(f"Обрабатываем страницу {index}/{pages_total_count}...")

            # Обновляем номер страницы в параметрах
            params["index"] = str(index)

            response = requests.get(
                base_api_url,
                params=params,
                headers=headers,
                timeout=30
            )

            response.raise_for_status()
            data = response.json()

            if 'items' in data:
                items = data['items']
                all_items.extend(items)
                print(f"Страница {index}: добавлено {len(items)} документов")
            else:
                print(f"Страница {index}: ключ 'items' не найден")

            # Небольшая пауза между запросами страниц
            time.sleep(0.5)

        print(f"\nВсего собрано документов: {len(all_items)}")

        if not all_items:
            print("Документы не найдены по заданным критериям.")
            return

        # Выводим информацию о первых нескольких документах
        print("\nПервые несколько документов:")
        for i, item in enumerate(all_items[:3], 1):
            print(f"\nДокумент {i}:")
            print(f"  eoNumber: {item.get('eoNumber', 'N/A')}")
            print(f"  Название: {item.get('title', 'N/A')}")
            print(f"  Дата: {item.get('documentDate', 'N/A')}")
            print(f"  Номер: {item.get('number', 'N/A')}")
            if 'signatoryAuthority' in item:
                print(f"  Орган: {item['signatoryAuthority'].get('name', 'N/A')}")

        # Скачиваем каждый документ
        download_base_url = "http://publication.pravo.gov.ru/file/pdf?eoNumber="

        successful_downloads = 0
        failed_downloads = 0

        print(f"\nНачинаем скачивание {len(all_items)} документов...")

        for i, item in enumerate(all_items, 1):
            eo_number = item.get('eoNumber')

            if not eo_number:
                print(f"\n[{i}/{len(all_items)}] Отсутствует eoNumber, пропускаем")
                failed_downloads += 1
                continue

            # Формируем URL для скачивания
            download_url = f"{download_base_url}{eo_number}"

            # Имя файла для сохранения
            title = item.get('title', 'document')
            number = item.get('number', 'number')
            date = item.get('documentDate', 'documentDate')
            date = date[:10]
            # Очищаем название от недопустимых символов в имени файла
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title[:50]  # Ограничиваем длину
            filename = f"{number}_{safe_title}_{date}.pdf".replace(' ', '_')
            filepath = os.path.join(download_dir, filename)

            # Проверяем, не скачан ли уже файл
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                print(f"[{i}/{len(all_items)}] ✓ Уже скачан: {filename} ({file_size} bytes)")
                successful_downloads += 1
                continue

            print(f"\n[{i}/{len(all_items)}] Скачиваю: {eo_number}")
            print(f"Название: {title}")

            try:
                # Делаем запрос для скачивания
                file_response = requests.get(download_url, stream=True, timeout=30, headers=headers)
                file_response.raise_for_status()

                # Проверяем content-type
                content_type = file_response.headers.get('content-type', '')
                if 'pdf' not in content_type.lower():
                    print(f"Внимание: файл может не быть PDF (Content-Type: {content_type})")

                # Сохраняем файл
                total_size = int(file_response.headers.get('content-length', 0))

                with open(filepath, 'wb') as f, tqdm(
                        desc=filename,
                        total=total_size,
                        unit='B',
                        unit_scale=True,
                        unit_divisor=1024,
                        disable=total_size == 0
                ) as pbar:
                    for chunk in file_response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))

                file_size = os.path.getsize(filepath)
                print(f"✓ Успешно сохранен: {filename} ({file_size} bytes)")
                successful_downloads += 1

            except requests.exceptions.RequestException as e:
                print(f"✗ Ошибка при скачивании {eo_number}: {e}")
                failed_downloads += 1

            # Пауза между запросами
            time.sleep(1)

        print(f"\n{'=' * 60}")
        print(f"ЗАВЕРШЕНО!")
        print(f"Всего документов: {len(all_items)}")
        print(f"Успешно скачано: {successful_downloads}")
        print(f"Не удалось скачать: {failed_downloads}")
        print(f"Документы сохранены в папке: '{download_dir}'")
        print(f"{'=' * 60}")

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при выполнении API запроса: {e}")
    except json.JSONDecodeError as e:
        print(f"Ошибка при парсинге JSON ответа: {e}")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")


def get_documents_info_only():
    """Функция только для получения информации о документах без скачивания"""
    params = {
        "DocumentTypes": "7ff5b3b5-3757-44f1-bb76-3766cabe3593",
        "SignatoryAuthorityId": "8005d8c9-4b6d-48d3-861a-2a37e69fccb3",
        "PublishDateSearchType": "0",
        "NumberSearchType": "0",
        "DocumentDateSearchType": "0",
        "DocumentDateFrom": "01.01.2025",
        "DocumentDateTo": "12.09.2025",
        "JdRegSearchType": "0",
        "SortedBy": "6",
        "SortDestination": "1",
        "PageSize": "200",
        "index": "1"
    }

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}

        # Сначала получаем информацию о количестве страниц
        first_response = requests.get(
            "http://publication.pravo.gov.ru/api/Documents",
            params=params,
            headers=headers,
            timeout=30
        )
        first_response.raise_for_status()
        first_data = first_response.json()

        total_count = first_data.get('totalCount', 0)
        pages_total_count = first_data.get('pagesTotalCount', 1)

        print(f"Всего документов: {total_count}")
        print(f"Всего страниц: {pages_total_count}")
        print(f"{'=' * 80}")

        all_items = []

        # Собираем данные со всех страниц
        for page in range(1, pages_total_count + 1):
            print(f"Получаем страницу {page}/{pages_total_count}...")

            params["Page"] = str(page)
            response = requests.get(
                "http://publication.pravo.gov.ru/api/Documents",
                params=params,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if 'items' in data:
                all_items.extend(data['items'])

            time.sleep(0.3)

        print(f"\nВсего собрано документов: {len(all_items)}")

        # Выводим информацию о документах
        for i, item in enumerate(all_items, 1):
            print(f"\nДокумент {i}:")
            print(f"  eoNumber: {item.get('eoNumber', 'N/A')}")
            print(f"  Название: {item.get('title', 'N/A')}")
            print(f"  Номер: {item.get('number', 'N/A')}")
            print(f"  Дата документа: {item.get('documentDate', 'N/A')}")
            print(f"  Дата публикации: {item.get('publishDate', 'N/A')}")

            if 'signatoryAuthority' in item:
                auth = item['signatoryAuthority']
                print(f"  Орган: {auth.get('name', 'N/A')}")

            print(f"  Ссылка: http://publication.pravo.gov.ru/file/pdf?eoNumber={item.get('eoNumber', '')}")

    except Exception as e:
        print(f"Ошибка: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("СКРИПТ ДЛЯ СКАЧИВАНИЯ ДОКУМЕНТОВ С PRAVO.GOV.RU")
    print("=" * 60)

    # Для скачивания всех документов:
    download_documents()

    # Для получения только информации о документах (без скачивания):
    # get_documents_info_only()