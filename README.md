# Asterisk Config Bot

Telegram-бот и локальные Bash-скрипты для управления dialplan и PJSIP-конфигурацией Asterisk без Ansible.

Старые файлы `telegram_ansible_bot.py` и `telegram_ansible.service` оставлены в репозитории как legacy-пример. Для локального режима используются:

- `telegram_asterisk_bot.py` — Telegram-бот;
- `rt_many` — входящие и исходящие маршруты dialplan;
- `pjsip_trunk_upsert` — добавление и обновление PJSIP-транков;
- `asteriskconfigbot.service` — systemd unit нового бота.

## Требования

- Linux с systemd;
- Asterisk 20 с `chan_pjsip` и `res_pjsip`;
- Python 3.10 или новее;
- локальный доступ к `/etc/asterisk` и Asterisk CLI.

В `pjsip.conf` должен существовать UDP-транспорт с именем `transport-udp`.

## Установка

```bash
git clone https://github.com/Ilya2868/asteriskconfigbot.git /opt/asteriskconfigbot
cd /opt/asteriskconfigbot

python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

cp .env.example .env
chmod 600 .env
```

Заполните `.env`:

```dotenv
BOT_TOKEN=replace-with-telegram-bot-token
ALLOWED_USER_IDS=123456789
```

`ALLOWED_USER_IDS` — числовые Telegram user ID через запятую, не username. Пустое значение разрешает доступ всем пользователям и не рекомендуется.

Установите службу:

```bash
install -o root -g root -m 0750 rt_many /opt/asteriskconfigbot/rt_many
install -o root -g root -m 0750 pjsip_trunk_upsert /opt/asteriskconfigbot/pjsip_trunk_upsert
install -o root -g root -m 0750 telegram_asterisk_bot.py /opt/asteriskconfigbot/telegram_asterisk_bot.py
install -o root -g root -m 0644 asteriskconfigbot.service /etc/systemd/system/asteriskconfigbot.service

systemctl daemon-reload
systemctl enable --now asteriskconfigbot
```

Пути можно изменить в systemd unit и константах бота.

## PJSIP-транки

Транк с регистрацией принимает пять аргументов:

```bash
./pjsip_trunk_upsert provider1 203.0.113.10 sip-login 'sip-password' from-provider1
```

IP-транк без регистрации принимает три аргумента:

```bash
./pjsip_trunk_upsert provider-ip 203.0.113.20 from-provider-ip
```

Для транка без регистрации создаются `endpoint`, `aor` и `identify`. Секции `auth` и `registration` не создаются.

Скрипт:

- проверяет аргументы;
- блокирует параллельное редактирование;
- обновляет ранее созданный управляемый блок;
- сохраняет резервную копию `pjsip.conf`;
- выполняет `pjsip reload`;
- восстанавливает предыдущий файл, если endpoint не появился.

## Входящие маршруты

Специальные направления MTT и MTS работают как прежде:

```bash
./rt_many 74953151234,7495 mtt
./rt_many 74953151234 mts
```

Если второй аргумент не равен `mtt`, `mts`, `out`, `transit` или `remove`, он считается именем контекста. Маршрут добавляется непосредственно в `extensions.conf`:

```bash
./rt_many 74953151234 from-provider
```

Созданный маршрут выполняет `NoOp`, `DumpChan` и `Hangup`. Его можно дополнить собственной логикой обработки вызова.

Исходящий маршрут:

```bash
./rt_many 74953151234 out provider1
```

Удаление:

```bash
./rt_many 74953151234 remove
```

## Безопасность

- Не добавляйте `.env`, Telegram-токены, SIP-пароли и приватные SSH-ключи в Git.
- Ограничивайте доступ через `ALLOWED_USER_IDS`.
- Бот запускает административные скрипты, поэтому используйте его только в доверенной среде.
- Перед публикацией SIP-конфигурации удаляйте реальные адреса, логины и пароли.
