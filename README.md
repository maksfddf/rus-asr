# Расшифровка русского аудио

GigaAM v3 E2E CTC int8, пунктуация и нормализация. Лицензия MIT.
Считает GitHub Actions на бесплатном раннере, интерфейс на бесплатном статическом пространстве Hugging Face, очередь и тексты в Supabase. Домашний компьютер не нужен.

- Интерфейс: https://makarpidoras-asr-ui.static.hf.space
- Очередь: https://supabase.com/dashboard/project/poatgesiflkoyuvoqvxo
- Запуски: https://github.com/maksfddf/rus-asr/actions

## Настройка на телефоне

Открыть интерфейс, Настройки, вписать:

- URL: `https://poatgesiflkoyuvoqvxo.supabase.co`
- anon key: `sb_publishable_pwHnnP0vm7k0VRejEBsaWg_3fGbbm6Q`

Оба значения не секретные. Сохранить, дальше запись или файл.

## Как идёт работа

1. Телефон загружает аудио в приватный бакет и создаёт задачу.
2. Cron каждые 10 минут поднимает раннер, воркер берёт самую старую задачу.
3. Аудио режется по 10 минут с перехлёстом 5 секунд, идёт через модель, куски склеиваются без дублей.
4. Текст и srt пишутся в базу, файл удаляется.
5. Старые файлы чистятся через 7 суток, если задача так и не дошла.

## Ограничения

- 50 МБ и 4 часа на файл.
- Один воркер, очередь последовательная.
- Cron может опаздывать на 5–20 минут.
- Приватный бакет, тексты читаются по anon key.

## Секреты

`SUPABASE_URL`, `SUPABASE_KEY` (service_role), `HF_TOKEN` в Settings, Secrets and variables, Actions.

## Проверка

`python worker/asr.py` локально с переменными окружения. Нужны ffmpeg и `pip install -r worker/requirements.txt`.
