import socket
import random

# headers in order
_headers = ['source_port',
            'destination_port',
            'sequence_number',
            'ack',
            'data_offset',
            'flags',
            'window_size',
            'checksum',
            'urgent'
            ]

# for each header returns the its initial byte on the head and its size
_headers_dic = {
        'source_port': (0, 2),
        'destination_port': (2, 2),
        'sequence_number': (4, 4),
        'ack': (8, 4),
        'data_offset': (12, 1),
        'flags': (13, 1),
        'window_size': (14, 2),
        'checksum': (16, 2),
        'urgent': (18, 2)
        }


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
    dic = {item: int.from_bytes(pack[_headers_dic[item][0] + of:_headers_dic[item][0] + _headers_dic[item][1] + of],
                                byteorder='little', signed=True) for item in _headers_dic.keys()}
    return dic, pack[20+of:]


def make_package_from_int(data: bytes, dic) -> bytes:
    header = b''
    for item in _headers:
        header += int.to_bytes(dic[item], _headers_dic[item][1], byteorder='little', signed=True)
    return header + data


def send_pack(pack, addr, s: socket.socket):
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


def make_checksum(data: bytes) -> int:
    total = 0
    for i in range(0, len(data), 2):
        total += int.from_bytes(data[i:i + 1], byteorder='little', signed=True)
    return total % (2**14)


def check_checksum(data: bytes, checksum: int) -> bool:
    total = 0
    for i in range(0, len(data), 2):
        total += int.from_bytes(data[i:i + 1], byteorder='little', signed=True)
    total = total % (2**14)
    return checksum == total

