import warnings
from cryptography.utils import CryptographyDeprecationWarning
with warnings.catch_warnings(action="ignore", category=CryptographyDeprecationWarning):
    import paramiko
import time
from tqdm import tqdm
import re
import ping3
import os

CONFIG_FILE = "config.txt"
CHECK_INTERVAL = 60  # Интервал проверки обновления в секундах

def read_config(filename):
    if not os.path.exists(filename):
        print(f"Ошибка: файл {filename} не найден.")
        return None
    
    with open(filename, "r") as f:
        lines = f.readlines()
    
    config = {}
    switches = []
    
    for line in lines:
        line = line.strip()
        if line.startswith("tftp_server_ip"):
            config["tftp_server_ip"] = line.split(": ")[1]
        elif line.startswith("filename"):
            config["filename"] = line.split(": ")[1]
        elif line.startswith("login"):
            config["login"] = line.split(": ")[1]
        elif line.startswith("password"):
            config["password"] = line.split(": ")[1]
        elif re.match(r"\d+\.\d+\.\d+\.\d+", line):
            switches.append(line)
    
    config["switches"] = switches
    return config

def ping_host(host):
    return ping3.ping(host) is not None

def ssh_connect(host, username, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname=host, username=username, password=password, timeout=60)
        print(f"OK.")
        return client
    except Exception as e:
        print(f"Ошибка подключения к {host}: {e}")
        return None

def wait_for_prompt(shell, prompt="#", timeout=120):
    buffer = ""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if shell.recv_ready():
            buffer += shell.recv(65535).decode()
            if prompt in buffer:
                print(f"OK.")
                return buffer
        time.sleep(0.5)
    print("Ошибка: не дождались CLI приглашения.")
    return buffer

def wait_for_write_ok(shell):
    buffer = ""
    while True:
        buffer += shell.recv(65535).decode()
        if "Get Img file size success" in buffer:
            buffer = ""
            break
        for i in tqdm(range(4000)):
            buffer += shell.recv(65535).decode()
            i = len(buffer)
            if "File transfer complete." in buffer:
                i = 4000
                buffer = ""
                print(f"Загрузка завершена")
                print(f"Запись файла локально...")
        while not "Write ok." in buffer:
            buffer += shell.recv(65535).decode()
        print(f"Запись файла завершена.")
        break
    time.sleep(CHECK_INTERVAL)

def wait_for_write_ok_lite(shell):
    buffer = ""
    while True:
        print(f"Запись файла локально...")
        buffer += shell.recv(65535).decode()
        while not "Write ok." in buffer:
            buffer += shell.recv(65535).decode()
            print(buffer)
        print(f"Запись файла завершена.")
        break
    time.sleep(CHECK_INTERVAL)

def execute_command(ssh_client, command, wait_time):
    print(command)
    shell = ssh_client.invoke_shell()
    shell.send(command + "\n")
    time.sleep(wait_time)
    output = shell.recv(65535).decode()
    return output

def execute_command_Y(ssh_client, command, wait_time):
    shell = ssh_client.invoke_shell()
    shell.send(command + "\n")
    shell.send('Y' + "\n")
    wait_for_write_ok(shell)
    time.sleep(wait_time)
    
def execute_command_Y_lite(ssh_client, command, wait_time):
    shell = ssh_client.invoke_shell()
    shell.send(command + "\n")
    shell.send('Y' + "\n")
    wait_for_write_ok_lite(shell)
    time.sleep(wait_time)

def update_switch(ssh_client, tftp_ip, filename):
    cmd = f"copy tftp://{tftp_ip}/{filename} nos.img"
    execute_command_Y(ssh_client, cmd, 1)

def get_stack_info(ssh_client):
    print(f"Получение списка юнитов...")
    units = {}
    master_unit = None
    output = execute_command(ssh_client, "show unit", 2)
    matches = re.findall(r"-------------------- Unit (\d+) --------------------.*?Work mode\s+:\s+([A-Z]+\s*[A-Z]*)", output, re.DOTALL)
    for unit, mode in matches:
        units[unit] = mode
        if mode == "ACTIVE MASTER":
            master_unit = unit
    return master_unit, units

def update_slave_units(ssh_client, master_unit, units):
    for unit, mode in units.items():
        if unit == master_unit:
            continue
        print(f"Обновляем SLAVE-коммутатор Unit {unit}")
        cmd = f"copy nos.img member-{unit}#nos.img"
        execute_command_Y_lite(ssh_client, cmd, 2)
        print(f"Обновление юнита {unit} завершено.")

def main():
    config = read_config(CONFIG_FILE)
    if config is None:
        return
    
    for switch in config["switches"]:
        print(f"Проверка доступности {switch}...")
        if not ping_host(switch):
            print(f"{switch} недоступен, пропуск")
            continue
        else:
            print(f"OK.")
            print(f"Подключение к {switch}...")
            ssh_client = ssh_connect(switch, config["login"], config["password"])
            if ssh_client:
                shell = ssh_client.invoke_shell()
                print("Ожидание загрузки CLI...")
                wait_for_prompt(shell)
                updated = update_switch(ssh_client, config["tftp_server_ip"], config["filename"])
                if updated:
                    master, units = get_stack_info(ssh_client)
                    update_slave_units(ssh_client, master, units)
                    print(f"Обновление стека завершено")
                    ssh_client.close()

if __name__ == "__main__":
    main()
