import socket
import random


def parse_address(address):
    host, port = address.split(':')

    if host == '':
        host = 'localhost'

    return host, int(port)


def parse_ip(ip_address):
    add = ip_address.split('.')
    return (int(item) for item in add)


def flags_splitter_from_int(flags: int):
    flg = []
    for _ in range(6):
        flg.append((flags % 2) == 1)
        flags //= 2
    flg.reverse()
    return flg


def flags_maker_from_int(end=False, syn=False, rst=False, ack=False):
    flags = 0
    flags += 2 ** 0 if end else 0
    flags += 2 ** 1 if syn else 0
    flags += 2 ** 2 if rst else 0
    flags += 2 ** 4 if ack else 0
    return flags


def headers_maker_from_int(source_port=0, destination_port=0, sequence_number=0, ack=0,
                           data_offset=0, flags=0, window_size=0, checksum=0, urgent=0):
    return {'source_port': source_port,
            'destination_port': destination_port,
            'sequence_number': sequence_number,
            'ack': ack,
            'data_offset': data_offset,
            'flags': flags,
            'window_size': window_size,
            'checksum': checksum,
            'urgent': urgent}


def split_package_to_int(pack: bytes):
    of = 20
    dic = {'source_port': int.from_bytes(pack[0+of:2+of], byteorder='little', signed=True),
           'destination_port': int.from_bytes(pack[2+of:4+of], byteorder='little', signed=True),
           'sequence_number': int.from_bytes(pack[4+of:8+of], byteorder='little', signed=True),
           'ack': int.from_bytes(pack[8+of:12+of], byteorder='little', signed=True),
           'data_offset': int.from_bytes([pack[12+of]], byteorder='little', signed=True),
           'flags': int.from_bytes([pack[13+of]], byteorder='little', signed=True),
           'window_size': int.from_bytes(pack[14+of:16+of], byteorder='little', signed=True),
           'checksum': check_checksum(pack[20+of:], pack[16+of:18+of]),
           'urgent': int.from_bytes(pack[18+of:20+of], byteorder='little', signed=True)}
    return dic, pack[20+of:]


def make_package_from_int(data: bytes, **dic) -> bytes:
    header = int.to_bytes(dic['source_port'], 2, byteorder='little', signed=True)
    header += int.to_bytes(dic['destination_port'], 2, byteorder='little', signed=True)
    header += int.to_bytes(dic['sequence_number'], 4, byteorder='little', signed=True)
    header += int.to_bytes(dic['ack'], 4, byteorder='little', signed=True)
    header += int.to_bytes(dic['data_offset'], 1, byteorder='little', signed=True)
    header += int.to_bytes(dic['flags'], 1, byteorder='little', signed=True)
    header += int.to_bytes(dic['window_size'], 2, byteorder='little', signed=True)
    header += make_checksum(data)
    header += int.to_bytes(dic['urgent'], 2, byteorder='little', signed=True)
    return header + data


def send_pack(pack, addr, s: socket.socket):
    # prob = random.randint(0, 100)
    s.sendto(pack, (addr, 0))


def receive_pack(host, s: socket.socket):
    pack, addr_info = s.recvfrom(65565)
    return pack, addr_info


def empty_dic():
    return {'source_port': 0,
            'destination_port': 0,
            'sequence_number': 0,
            'ack': 0,
            'data_offset': 0,
            'flags': 0,
            'window_size': 0,
            'checksum': 0,
            'urgent': 0}


def empty_header():
    return {'source_port': b'\x00\x00',
            'destination_port': b'\x00\x00',
            'sequence_number': b'\x00\x00\x00\x00',
            'ack': b'\x00\x00\x00\x00',
            'data_offset': b'\x00',
            'flags': b'\x00',
            'window_size': b'\x00\x00',
            'checksum': b'\x00\x00',
            'urgent': b'\x00\x00'}


def make_checksum(data: bytes) -> bytes:
    sum = 0
    for i in range(0, len(data), 2):
        sum += int.from_bytes(data[i:i + 1], byteorder='little', signed=True)
    return int.to_bytes(sum, 2, byteorder='little', signed=True)


def check_checksum(data: bytes, checksum: bytes) -> bool:
    checksum = int.from_bytes(checksum, byteorder='little', signed=True)
    sum = 0
    for i in range(0, len(data), 2):
        sum += int.from_bytes(data[i:i+1], byteorder='little', signed=True)
    return checksum == sum
