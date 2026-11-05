# Расшифровка русского аудио

Очередь ASR на GigaAM v3 E2E CTC (int8 ONNX), модель с пунктуацией, лицензия MIT.
Считает GitHub Actions на бесплатном раннере, интерфейс на бесплатном статическом пространстве Hugging Face, очередь и тексты в Supabase.
Ничего не крутится на домашнем компьютере.

100 часов в месяц это 3,3 часа в сутки, при скорости в 4 раза быстрее реального времени около 50 минут счёта в день. Лимит одного запуска 5 часов, куски по 10 минут, очередь последовательная.

## 1. Supabase

1. Проект на supabase.com, карта не нужна.
2. SQL Editor, вставить `supabase/schema.sql`, выполнить.
3. Settings, API: взять Project URL, anon key и service_role key.

## 2. Hugging Face

1. Аккаунт, токен Write.
2. `python3 -m venv .venv && . .venv/bin/activate && pip install huggingface_hub`
3. `export HF_USER=логин HF_TOKEN=токен && python deploy.py`
4. Получишь адрес интерфейса.

## 3. GitHub

1. Аккаунт, пустой публичный репозиторий `rus-asr`.
2. Settings, Secrets and variables, Actions: `SUPABASE_URL`, `SUPABASE_KEY` (service_role), `HF_TOKEN`.
3. Залить этот каталог в ветку `main`.
4. Actions, workflow `asr`, Run workflow для проверки.

Публичный репозиторий даёт неограниченные минуты, приватный 2000 в месяц.

## 4. Проверка

Открыть интерфейс, вписать URL и anon key, записать 30 секунд, дождаться текста.
Очередь видно в таблице `jobs`, логи в Actions.

## Ограничения

- 50 МБ и 4 часа на файл, куски по 10 минут.
- Один воркер, параллельных задач нет.
- Секреты только в GitHub Secrets, anon key публичный.
- Аудио удаляется после расшифровки, тексты в Supabase.
- Cron на GitHub может запаздывать на 5–20 минут, это нормально.

## Стоимость

Ноль. Расход: минуты Actions и квота Supabase.
