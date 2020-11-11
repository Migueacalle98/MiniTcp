import socket
import logging
import random
import threading
import time
from utils import *

logger = logging.getLogger('serve-file')


class Conn:

    packet_size = 256
    def __init__(self, partner=None, source_port=1515, source_ip='0.0.0.0', max_buffer_size = 2048):
        self.send_ip = partner[0] if partner is not None else None
        self.destination_port = partner[1] if partner is not None else None
        self.source_ip = source_ip
        self.source_port = source_port
        self.max_buffer_size = max_buffer_size
        self.state = 'closed'
        self.sequence_number = 0
        self.last_ack = 0
        self.window_size = 5 * self.packet_size
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
        self.recv_buffer = b''
        self._rtt = 0.2
        self._dev_rtt = 0.01
        self._rtt_seq = None
        self._rtt_start_time = None
        self.receiver = threading.Thread(target=self._receive)
        self.receiver.start()

    def _receive(self):
        # State Machine
        while True:
            pack, addr_info = receive_pack((self.source_ip, self.source_port), self.socket)
            headers, data = split_package_to_int(pack)
            _, ack, _, rst, syn, end = flags_splitter_from_int(headers['flags'])
            if headers['destination_port'] == self.source_port:
                # print('Head', headers)
                # print('ack: ', self.last_ack)
                # print(self.state)
                # Manging State
                if self.state == 'closed':
                    return
                if self.state == 'listen':
                    if syn:
                        self.state = 'syn_recv'
                        self.send_ip = addr_info[0]
                        self.destination_port = headers['source_port']
                        self.last_ack = headers['sequence_number'] + 1
                        self.send_syn_plus_ack()
                if self.state == 'syn_recv':
                    if rst:
                        self.state = 'listen'
                    elif syn:
                        self.send_syn_plus_ack()
                    elif ack:
                        if headers['ack'] > self.sequence_number:
                            self.last_ack = headers['sequence_number']
                            self.sequence_number = headers['ack']
                            self.state = 'established'
                if self.state == 'syn_sent':
                    if syn and ack:
                        if headers['ack'] > self.sequence_number:
                            self.state = 'established'
                            self.sequence_number = max(headers['ack'], self.sequence_number)
                            self.last_ack = max(headers['sequence_number'] + 1, self.last_ack)
                            self.send_ack()
                    elif syn:
                        self.state = 'syn_recv'
                        self.send_syn_plus_ack()
                if self.state == 'established':
                    if syn and ack and headers['ack'] >= self.sequence_number:
                        self.send_ack()
                    elif ack and check_checksum(data, headers['checksum']):
                        self.sequence_number = max(headers['ack'], self.sequence_number)
                    if headers['flags'] == 0 and headers['sequence_number'] == self.last_ack:
                        self.recv_buffer += data
                        self.last_ack += len(data)
                        self.send_ack(data)
                    if end:
                        self.last_ack = headers['sequence_number'] + 1
                        self.sequence_number += 1
                        self.state = 'close_wait'
                        self.send_ack()
                        self.send_end()
                if self.state == 'fin_wait_1':
                    if ack and headers['ack'] > self.sequence_number:
                        self.sequence_number = headers['ack']
                        self.state = 'fin_wait_2'
                if self.state == 'fin_wait_2':
                    if end:
                        self.last_ack = headers['sequence_number'] + 1
                        self.state = 'time_wait'
                if self.state == 'time_wait':
                    pass
                if self.state == 'close_wait':
                    if end:
                        self.send_ack()
                        self.send_end()
                    if ack and headers['ack'] > self.sequence_number:
                        self.state = 'last_ack'
                if self.state == 'last_ack':
                    if ack and headers['ack'] > self.sequence_number:
                        self.state = 'closed'
                # update rtt in case needed
                if ack and headers['ack'] == self._rtt_seq:
                    self._update_rtt()


    def send_package(self, flags=0, data=b'', seq_num=None):
        # Computing rtt
        if self._rtt_seq is None:
            self._rtt_seq = self.sequence_number
            self._rtt_start_time = time.time()
        head = headers_maker_from_int(source_port=self.source_port,
                                      destination_port=self.destination_port,
                                      sequence_number=self.sequence_number if seq_num is None else seq_num,
                                      ack=self.last_ack,
                                      data_offset=20,
                                      flags=flags,
                                      window_size=max(0, self.max_buffer_size - len(self.recv_buffer)),
                                      checksum=make_checksum(data)
                                      )
        msg = make_package_from_int(data, head)
        send_pack(msg, self.send_ip, self.socket)

    def send_syn(self):
        self.send_package(flags_maker_from_int(syn=True))

    def send_ack(self, data=b'', seq_num=None):
        self.send_package(flags_maker_from_int(ack=True), data, seq_num)

    def send_syn_plus_ack(self):
        self.send_package(flags_maker_from_int(ack=True, syn=True))

    def send_end(self):
        self.send_package(flags_maker_from_int(end=True))

    def close(self):
        self.state = 'closed'
        self.send_ip = None
        self.destination_port = None
        self.sequence_number = 0
        self.last_ack = 0
        self.recv_buffer = b''

    def timeout(self):
        return self._rtt + 4 * self._dev_rtt

    def _update_rtt(self):
        a = 0.85
        b =0.25
        sample_rtt = time.time() - self._rtt_start_time
        self._dev_rtt = (1 - b) * self._dev_rtt + b * (sample_rtt - self._rtt)
        self._rtt = (1 - a) * self._rtt + a * sample_rtt
        self._rtt_start_time = None
        self._rtt_start_time = None


SLEEP_INTERVAL = 0.001
END_ELAPSE = 5

def listen(address: str) -> Conn:
    host, port = parse_address(address)
    conn = Conn(source_port=port)
    logger.info(f'Socket binded to {host}:{port}')
    conn.state = 'listen'
    return conn


def accept(conn: Conn) -> Conn:
    logger.info(f'Expecting HandShake')
    if conn.state == 'closed':
        conn.state = 'listen'
    while conn.state != 'established':
        time.sleep(SLEEP_INTERVAL)
    logger.info(f'HandShake Complete whit {conn.send_ip}:{conn.destination_port}')
    return conn


def dial(address) -> Conn:
    logger.info('Starting Handshake')
    host, port = parse_address(address)
    conn = Conn((host, int(port)), 1515)
    conn.state = 'syn_sent'
    while conn.state != 'established':
        conn.send_syn()
        time.sleep(SLEEP_INTERVAL)
    logger.info(f'HandShake Complete whit {conn.send_ip}:{conn.destination_port}')
    return conn


def send(conn: Conn, data: bytes) -> int:
    #print(conn.timeout())
    num_bytes = len(data)
    ini_seq_num = conn.sequence_number
    base = conn.sequence_number
    next_to_send = conn.sequence_number
    start_time = time.time()
    # logger.info(f'Sending Data...')
    if conn.state == 'established':
        while base < ini_seq_num + num_bytes:
            while next_to_send <= base + conn.window_size:
                if next_to_send < ini_seq_num + num_bytes:
                    pkt_data = data[next_to_send - ini_seq_num:next_to_send - ini_seq_num + conn.packet_size]
                    #if len(pkt_data) > 0:
                    conn.send_package(0, pkt_data, next_to_send)
                next_to_send += conn.packet_size
            time.sleep(SLEEP_INTERVAL)
            if conn.timeout() < (time.time() - start_time) or conn.sequence_number > base:
                base = conn.sequence_number
                next_to_send = base
                start_time = time.time()
        return base - ini_seq_num
    else:
        raise ConnException


def recv(conn: Conn, length: int) -> bytes:
    # logger.info(f'Receiving Data...')
    start_time = time.time()
    while len(conn.recv_buffer) < length:
        time.sleep(SLEEP_INTERVAL)
        if conn.state == 'closed':
            break
        if conn.timeout() < (time.time() - start_time):
            conn.send_ack()
            start_time = time.time()
    data = conn.recv_buffer[0:length]
    conn.recv_buffer = conn.recv_buffer[length:]
    if len(conn.recv_buffer) == 0 and conn.state == 'closed':
        conn.close()
    return data


def close(conn: Conn):
    logger.info('Ending Connection')
    conn.state = 'fin_wait_1'
    while conn.state == 'fin_wait_1':
        conn.send_end()
        time.sleep(SLEEP_INTERVAL)
    while conn.state == 'fin_wait_2':
        time.sleep(SLEEP_INTERVAL)

    start_time = time.time()
    while conn.state == 'time_wait':
        conn.send_ack()
        time.sleep(SLEEP_INTERVAL)
        if END_ELAPSE < (time.time() - start_time):
            break

    conn.close()


