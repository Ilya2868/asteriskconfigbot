1.клонируем репозиторий в папку /opt/ansiblebot

2.файл сервиса бота telegram_ansible.service переносим в /etc/systemd/system и выполняем systemctl daemon-reload

3.устанавливаем окружение venv для бота. например в папку /opt/ansiblebot

sudo apt update

sudo apt install -y python3 python3-venv python3-pip git

cd /opt/ansiblebot


папку venv можно удалить

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install python-telegram-bot ansible python-dotenv
touch .env
echo 'BOT_TOKEN=ваш_телеграм_токен' > .env
chmod 600 .env

можно запустить вручную чтобы проверить все ли установилось
./venv/bin/python telegram_ansible_bot.py



4.файл скрипта rt_many переносим в папку /root

5.systemctl enable telegram_ansible.service && systemctl start telegram_ansible.service

6.если используются другие директории, их можно изменить в файле самого бота и в файле сервиса