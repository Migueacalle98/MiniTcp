import socket
import random
import time

class ConnException(Exception):
    pass

states = ['closed', 'listen', 'syn_recv', 'syn_sent', 'established', 'fin_wait_1', 'fin_wait_2', 'time_wait', 'close_wait', 'last_ack']

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
                                byteorder='big', signed=False) for item in _headers_dic.keys()}
    return dic, pack[dic['data_offset']+of:]


def make_package_from_int(data: bytes, dic) -> bytes:
    header = b''
    for item in _headers:
        header += int.to_bytes(dic[item], _headers_dic[item][1], byteorder='big', signed=False)
    return header + data


def send_pack(pack, addr, s: socket.socket):
    time.sleep(0.002)
    s.sendto(pack, (addr, 0))


def receive_pack(host, s: socket.socket):
    pack, addr_info = s.recvfrom(65565)
    return pack, addr_info

def make_checksum(data: bytes) -> int:
    total = 0
    for i in range(0, len(data), 2):
        total += int.from_bytes(data[i:i + 1], byteorder='big', signed=False)
    return total % (2**16-1)


def check_checksum(data: bytes, checksum: int) -> bool:
    total = 0
    for i in range(0, len(data), 2):
        total += int.from_bytes(data[i:i + 1], byteorder='big', signed=False)
    total = total % (2**16-1)
    return checksum == total

