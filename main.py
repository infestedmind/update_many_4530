import paramiko
import time
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
        client.connect(hostname=host, username=username, password=password, timeout=10)
        return client
    except Exception as e:
        print(f"Ошибка подключения к {host}: {e}")
        return None

def wait_for_prompt(shell, prompt="#", timeout=60):
    buffer = ""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if shell.recv_ready():
            buffer += shell.recv(65535).decode()
            if prompt in buffer:
                return buffer
        time.sleep(0.5)
    print("Ошибка: не дождались CLI приглашения.")
    return buffer

def execute_command(ssh_client, command, wait_time=1):
    shell = ssh_client.invoke_shell()
    shell.send(command + "\n")
    time.sleep(wait_time)
    output = shell.recv(65535).decode()
    return output

def update_switch(ssh_client, tftp_ip, filename):
    cmd = f"copy tftp://{tftp_ip}/{filename} nos.img"
    output = execute_command(ssh_client, cmd, 2)
    if "Confirm to overwrite" in output:
        execute_command(ssh_client, "Y", 2)
    while True:
        output = execute_command(ssh_client, "", 2)
        print(output)
        if "Write ok." in output:
            print("Обновление завершено")
            break
        time.sleep(CHECK_INTERVAL)

def get_stack_units(ssh_client):
    output = execute_command(ssh_client, "show unit", 2)
    unit_numbers = re.findall(r"-------------------- Unit (\d+) --------------------", output)
    return [int(num) for num in unit_numbers]

def update_stack_units(ssh_client, units):
    for unit in units:
        if unit == 1:
            continue
        cmd = f"copy nos.img member-{unit}#nos.img"
        execute_command(ssh_client, cmd, 2)
        while True:
            output = execute_command(ssh_client, "", 2)
            print(output)
            if "Write ok." in output:
                print(f"Обновление юнита {unit} завершено")
                break
            time.sleep(CHECK_INTERVAL)

def main():
    config = read_config(CONFIG_FILE)
    if config is None:
        return
    
    for switch in config["switches"]:
        print(f"Проверка доступности {switch}...")
        if not ping_host(switch):
            print(f"{switch} недоступен, пропуск")
            continue
        print(f"Подключение к {switch}...")
        ssh_client = ssh_connect(switch, config["login"], config["password"])
        if ssh_client:
            print(f"Подключено к {switch} прошло успешно!")
            shell = ssh_client.invoke_shell()
            print("Ожидание загрузки CLI...")
            wait_for_prompt(shell)
            shell.send("\n")  # Отправляем Enter
            update_switch(ssh_client, config["tftp_server_ip"], config["filename"])
            units = get_stack_units(ssh_client)
            update_stack_units(ssh_client, units)
            ssh_client.close()

if __name__ == "__main__":
    main()
