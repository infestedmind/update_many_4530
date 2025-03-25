![](https://qtech-russia.ru/image/cache/catalog/image/catalog/logo/qtech-logo.webp)

# Подготовка Windows

Для запуска на Windows требуется:

1. Установить Python3 c официального сайта версией не ниже, чем **3.11**:

https://www.python.org/downloads/

### Во время установки Python на первом окне поставить галочку напротив "Добавить в PATH"!

Установить Git Bash c официального сайта:

https://git-scm.com/downloads

2. Разархивировать скаченный архив с программой из этого GitHub репозитория и открыть его в Git Bash.
3. Запустить виртуальную среду
```
source /venv/bin/activate
```
4. Установить требуемые модули из файла requirements.txt
```
pip3 install -r requirements.txt
```
# Подготовка Ubuntu

1. Установить Python3
```
apt install python3-pip
```
2. Запустить виртуальную среду
```
source /venv/bin/activate
```
3. Установить требуемые модули из файла requirements.txt
```
pip3 install -r requirements.txt
```

# Конфигурирование файла config.txt:

Для запуска важно корректно заполнить поля внутри файла config.txt, айпи адреса MASTER коммутаторов записываются в самом конце, разделённые друг от друга точками (.)
Пример:
```
###TFTP###
tftp_server_ip: 10.8.8.9
filename: QSW-4530-X_8.2.3.254_nos.img
###SWITCHES###
login: admin
password: admin
.
10.45.96.1
.
10.45.30.2
.
10.45.30.8
```
C пояснениями:
```
###TFTP###
tftp_server_ip: 10.8.8.9 <-- IP-адрес локального tftp-сервера
filename: QSW-4530-X_8.2.3.254_nos.img <-- Название файла с ПО
###SWITCHES###
login: admin <-- Логин для доступа по ssh к комутатору
password: admin <-- Пароль для доступа по ssh к комутатору
.
10.45.96.1 <-- IP-адрес MASTER коммутатора
.
10.45.30.2 <-- IP-адрес MASTER коммутатора
.
10.45.30.8 <-- IP-адрес MASTER коммутатора
```
# Запуск

Запуск программы осуществляется с помощью Python3
```
python3 main.py
```
