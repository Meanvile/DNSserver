import pickle
import socket
import sys
# from difflib import ndiff
from dnslib import DNSHeader, DNSRecord
from datetime import timedelta, datetime

FORWARD_SERVER = '212.193.163.6'


def get_forward_server():
    new_forward_server = input("Введите ip перенаправляющего сервера: ")
    if new_forward_server:
        return new_forward_server
    return FORWARD_SERVER


forward_server = FORWARD_SERVER
if sys.argv[-1] == "ip":
    forward_server = get_forward_server()


def save_cache(data):
    try:
        old_cache = load_cache()
        with open('dns_cache.pickle', 'wb') as file:
            pickle.dump(data, file)
        for k, v in data.items():
            if k not in old_cache or data[k] != v:
                for i in str(v[0])[1:-1].split(", "):
                    print(f"Новая запись:\n {str(v[1])}  {str(k)}  {str(i)}")
    except Exception as e:
        pass


def load_cache():
    try:
        with open('dns_cache.pickle', 'rb') as file:
            new_cache = pickle.load(file)
        return new_cache
    except Exception as e:
        return {}


def clean_cache(cache):
    num = 0
    new_cache = {}
    last_length = len(cache)

    for key, value in cache.items():
        if not datetime.now() - value[1] > timedelta(seconds=300):
            new_cache[key] = value
    num += last_length - len(new_cache)

    if num > 0:
        print(f"Удалено {str(num)} старых ресурсных записей\n")
    return new_cache


cache = load_cache()
server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind(('127.0.0.1', 53))
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

try:
    print(f'Перенаправляющий сервер: {forward_server}')
    print("Сервер работает...")
    while True:
        data, ip = server.recvfrom(2048)
        x = DNSRecord.parse(data)
        if cache:
            cache = clean_cache(cache)
            save_cache(cache)

        if cache.get((x.questions[0].qname, x.questions[0].qtype)):
            header = DNSHeader(x.header.id, q=1, a=len(
                cache.get((x.questions[0].qname, x.questions[0].qtype))[0]))
            response = DNSRecord(header, x.questions, cache.get(
                (x.questions[0].qname, x.questions[0].qtype))[0])
            server.sendto(response.pack(), ip)
            print(f"Получен ответ от кэша")
        else:
            try:
                client.sendto(data, (forward_server, 53))
                response_from_dns, _ = client.recvfrom(2048)
                y = DNSRecord.parse(response_from_dns)
                date_time = datetime.now()
                cache[
                    (y.questions[0].qname, y.questions[0].qtype)] = y.rr, date_time
                if y.auth:
                    cache[
                        (y.auth[0].rname, y.auth[0].rtype)] = y.auth, date_time
                for pack in y.ar:
                    cache[(pack.rname, pack.rtype)] = [pack], date_time
                save_cache(cache)
                header = DNSHeader(x.header.id, q=1,
                                   a=len(
                                       cache.get((x.questions[0].qname,
                                                  x.questions[
                                                      0].qtype))[
                                           0]))
                response = DNSRecord(header, x.questions, cache.get(
                    (x.questions[0].qname, x.questions[0].qtype))[0])
                server.sendto(response.pack(), ip)
            except Exception as e:
                print(f"На сервере произошла ошибка: \n{e}")
except KeyboardInterrupt:
    exit(0)
finally:
    if cache:
        save_cache(cache)
        print('Кэш был успешно сохранён\n')
    print('Произошло отключение сервера')
