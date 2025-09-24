1.клонируем репозиторий в папку /opt/ansiblebot

2.файл сервиса бота telegram_ansible.service переносим в /etc/systemd/system

3.устанавливаем окружение venv для бота. например в папку /opt/ansiblebot




4.файл скрипта rt_many переносим в папку /root

5.systemctl enable telegram_ansible.service && systemctl start telegram_ansible.service

6.если нужны другие директории, их можно изменить в файле самого бота и в файле сервиса