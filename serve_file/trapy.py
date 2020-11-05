import socket
import logging
import random
import threading
import time
from utils import *
from timer import Timer

logger = logging.getLogger('serve-file')


class Conn:
    client: tuple
    server: tuple
    ack: int
    sequence_number: int
    sender_socket: socket.socket
    receive_socket: socket.socket

    def __init__(self, client: tuple, server: tuple):
        self.client = client
        self.server = server
        self.sender_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
        self.receive_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
        self.receive_socket.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        self.receive_socket.bind(('localhost', 0))


class ConnException(Exception):
    pass


# Shared resources across threads
SLEEP_INTERVAL = 0.001
TIMEOUT_INTERVAL = 0.003
END_ELAPSE = 5
base = 0
send_timer = Timer(TIMEOUT_INTERVAL)
mutex = threading.Lock()
packet_size = 256
window_size = packet_size * 10
end_timer = Timer(END_ELAPSE)


def listen(address: str) -> Conn:
    host, port = parse_address(address)
    conn = Conn((None, None), (host, int(port)))
    logger.info(f'Socket binded to {host}:{port}')
    return conn


def accept(conn: Conn) -> Conn:
    global mutex
    global send_timer
    global base

    # expecting sync
    logger.info(f'Expecting HandShake')
    while True:
        pack, addr_info = receive_pack(conn.server[0], conn.receive_socket)
        headers, data = split_package_to_int(pack)
        if headers['destination_port'] == conn.server[1]:
            if flags_splitter_from_int(headers['flags'])[4]:
                break
    r_number = random.randint(0, 2 ** 16 - 1)
    conn.client = (addr_info[0], headers['source_port'])
    conn.sequence_number = r_number
    # making SYNACK
    head = headers_maker_from_int(source_port=conn.server[1],
                                  destination_port=headers['source_port'],
                                  sequence_number=r_number,
                                  ack=headers['sequence_number'],
                                  flags=flags_maker_from_int(syn=True)
                                  )
    msg = make_package_from_int(b'', head)
    # logger.info('Sending SYNACK')
    base = 0
    threading.Thread(target=_accept_thread,
                     args=(conn, r_number)).start()

    while base < 1:
        mutex.acquire()
        send_pack(msg, addr_info[0], conn.sender_socket)
        # receiving SYNACK confirmation
        if not send_timer.running():
            send_timer.start()
        if not send_timer.running() and not send_timer.timeout():
            mutex.release()
            time.sleep(SLEEP_INTERVAL)
            mutex.acquire()
        if send_timer.timeout():
            send_timer.stop()
        mutex.release()
    while threading.active_count() > 1:
        time.sleep(SLEEP_INTERVAL)
    conn.sequence_number = r_number + 1
    return conn


def _accept_thread(conn: Conn, r_number):
    global mutex
    global send_timer
    global base

    while True:
        con_pack, con_addr_info = receive_pack(conn.server[0], conn.receive_socket)
        con_headers, con_data = split_package_to_int(con_pack)
        if con_headers['destination_port'] == conn.server[1]:
            if con_headers['ack'] > r_number:
                with mutex:
                    base = 1
                    logger.info(f'synack received')
                    send_timer.stop()
                break
    logger.info(f'HandShake Complete whit {conn.client[0]}:{conn.client[1]}')
    return conn


def dial(address) -> Conn:
    global mutex
    global base
    global send_timer

    logger.info('Starting Handshake')
    host, port = parse_address(address)
    conn = Conn(('localhost', 1515), (host, int(port)))
    # Making Syn Package
    r_number = random.randint(0, 2 ** 16 - 1)
    head = headers_maker_from_int(flags=flags_maker_from_int(syn=True),
                                  sequence_number=r_number,
                                  source_port=conn.client[1],
                                  destination_port=conn.server[1]
                                  )
    msg = make_package_from_int(b'', head)
    # Sending Syn Package
    # logger.info('Sending Syn')
    base = 0
    threading.Thread(target=_dial_thread, args=(conn, r_number)).start()
    while base < 1:
        mutex.acquire()
        send_pack(msg, conn.server[0], conn.sender_socket)
        if not send_timer.running():
            send_timer.start()
        if not send_timer.running() and not send_timer.timeout():
            mutex.release()
            time.sleep(SLEEP_INTERVAL)
            mutex.acquire()
        if send_timer.timeout():
            send_timer.stop()
        mutex.release()
    while threading.active_count() > 1:
        time.sleep(SLEEP_INTERVAL)
    return conn


def _dial_thread(conn: Conn, r_number: int):
    global mutex
    global base

    while True:
        # receiving SYNACK confirmation
        con_pack, con_addr_info = receive_pack(conn.server[0], conn.receive_socket)
        con_headers, con_data = split_package_to_int(con_pack)
        if con_headers['destination_port'] == conn.client[1]:
            if con_headers['ack'] == r_number:
                with mutex:
                    logger.info('SYNACK received')
                    base = 1
                break
    conn.ack = con_headers['sequence_number'] + 1
    logger.info(f'HandShake Complete whit {conn.server[0]}:{conn.server[1]}')


def send(conn: Conn, data: bytes) -> int:
    global mutex
    global base
    global send_timer

    num_bytes = len(data)
    ini_seq_num = conn.sequence_number
    next_to_send = ini_seq_num
    base = ini_seq_num

    logger.info(f'Sending Data...')
    # Start the receiver thread
    threading.Thread(target=_send_thread, args=(conn, num_bytes)).start()

    while base < ini_seq_num + num_bytes:
        while next_to_send <= base + window_size:
            if next_to_send < ini_seq_num + num_bytes:
                pkt_data = data[next_to_send - ini_seq_num:next_to_send - ini_seq_num + packet_size]
                head = headers_maker_from_int(source_port=conn.server[1],
                                              destination_port=conn.client[1],
                                              sequence_number=next_to_send,
                                              ack=0,
                                              flags=flags_maker_from_int(ack=True),
                                              checksum=make_checksum(pkt_data),
                                              data_offset=20
                                              )
                pkt = make_package_from_int(pkt_data, head)
                send_pack(pkt, conn.client[0], conn.sender_socket)
            next_to_send += packet_size

        if not send_timer.running():
            with mutex:
                send_timer.start()

        if not send_timer.running() and not send_timer.timeout():
            time.sleep(SLEEP_INTERVAL)

        if send_timer.timeout():
            with mutex:
                next_to_send = base
                send_timer.stop()
    conn.sequence_number = base
    return base - ini_seq_num


# received ack thread
def _send_thread(conn: Conn, num_byes):
    global mutex
    global base
    global send_timer

    ini_seq_num = conn.sequence_number
    while base < ini_seq_num + num_byes:
        pkt, addr = receive_pack(conn.client[0], conn.receive_socket)
        headers, data = split_package_to_int(pkt)
        _, ack, _, rst, syn, end = flags_splitter_from_int(headers['flags'])
        if ack and not rst and not syn and not end and check_checksum(data, headers['checksum']):
            if headers['destination_port'] == conn.server[1]:
                ack = headers['ack']
                # print(ack,' ack:base', base)
                if ack > base:
                    window_size = headers['window_size']
                    with mutex:
                        base = ack
                        send_timer.stop()


def recv(conn: Conn, length: int) -> bytes:
    # logger.info(f'Receiving Data...')
    expected_seq_num = conn.ack
    all_data = b''
    while len(all_data) < length:
        # print(expected_seq_num)
        # Get the next packet from the sender
        pkt, addr = receive_pack(conn.server[0], conn.receive_socket)
        headers, data = split_package_to_int(pkt)
        _, ack, _, rst, syn, end = flags_splitter_from_int(headers['flags'])
        seq_num = headers['sequence_number']
        if headers['destination_port'] == conn.client[1]:
            if seq_num == expected_seq_num:
                if check_checksum(data, headers['checksum']):
                    if end:
                        if len(all_data) > 0:
                            conn.ack = expected_seq_num
                            return all_data
                        return close_receiver(conn)
                    if not syn and ack:
                        expected_seq_num += len(data)
                        all_data += data
                        # print(f'Accepted PKT {seq_num}, sending ack {expected_seq_num}')
            # Send back an ACK
            head = headers_maker_from_int(flags=flags_maker_from_int(ack=True),
                                          sequence_number=0,
                                          ack=expected_seq_num,
                                          source_port=conn.client[1],
                                          destination_port=conn.server[1],
                                          checksum=make_checksum(data),
                                          data_offset=20,
                                          window_size=length-len(all_data)
                                          )
            pkt = make_package_from_int(data, head)
            send_pack(pkt, conn.server[0], conn.sender_socket)
    conn.ack = expected_seq_num
    return all_data


def close_receiver(conn: Conn):
    r_number = random.randint(0, 2 ** 16 - 1)
    head = headers_maker_from_int(flags=flags_maker_from_int(end=True),
                                  sequence_number=r_number,
                                  ack=conn.ack + 1,
                                  source_port=conn.client[1],
                                  destination_port=conn.server[1]
                                  )
    msg = make_package_from_int(b'', head)
    global base
    global mutex
    base = 0
    threading.Thread(target=_close_receiver_thread, args=(conn, r_number)).start()
    while base < 1:
        mutex.acquire()
        send_pack(msg, conn.server[0], conn.sender_socket)
        if not send_timer.running():
            send_timer.start()
        if not send_timer.running() and not send_timer.timeout():
            mutex.release()
            time.sleep(SLEEP_INTERVAL)
            mutex.acquire()
        if send_timer.timeout():
            send_timer.stop()
        mutex.release()
    while threading.active_count() > 1:
        time.sleep(SLEEP_INTERVAL)
    conn.sender_socket.close()
    conn.receive_socket.close()
    conn.client = None
    conn.server = None
    return b''


def _close_receiver_thread(conn: Conn, r_number: int):
    global mutex
    global base
    while base < 1:
        # receiving ENDACK confirmation
        con_pack, con_addr_info = receive_pack(conn.server[0], conn.receive_socket)
        con_headers, con_data = split_package_to_int(con_pack)
        if con_headers['destination_port'] == conn.client[1]:
            if con_headers['ack'] == r_number:
                with mutex:
                    base = 1
                break
    # logger.info(f'Connection Ended whit {conn.server[0]}:{conn.server[0]}')


def close(conn: Conn):
    global mutex
    global base
    global end_timer
    global send_timer
    logger.info('Ending Connection')
    head = headers_maker_from_int(flags=flags_maker_from_int(end=True),
                                  sequence_number=conn.sequence_number,
                                  source_port=conn.server[1],
                                  destination_port=conn.client[1])
    msg = make_package_from_int(b'', head)
    base = 0
    threading.Thread(target=_close_thread, args=(conn,)).start()
    while base < 3:
        mutex.acquire()
        send_pack(msg, conn.client[0], conn.sender_socket)
        if not send_timer.running():
            send_timer.start()
        if not send_timer.running() and not send_timer.timeout():
            mutex.release()
            time.sleep(SLEEP_INTERVAL)
            mutex.acquire()
        if send_timer.timeout():
            send_timer.stop()
        mutex.release()

    while True:
        mutex.acquire()
        if not end_timer.running():
            end_timer.start()
        if not end_timer.running() and not end_timer.timeout():
            mutex.release()
            time.sleep(SLEEP_INTERVAL)
            mutex.acquire()
        if end_timer.timeout():
            end_timer.stop()
            base = 4
            break
        mutex.release()
    mutex.release()
    while threading.active_count() > 1:
        time.sleep(SLEEP_INTERVAL)


def _close_thread(conn: Conn):
    global mutex
    global base
    global end_timer
    global send_timer
    end_seq_num = 0
    end_received = False
    end_ack_received = False
    while base < 3:
        pack, addr_info = receive_pack(conn.server[0], conn.receive_socket)
        headers, data = split_package_to_int(pack)
        _, ack, _, rst, syn, end = flags_splitter_from_int(headers['flags'])
        if headers['destination_port'] == conn.server[1]:
            if headers['ack'] == conn.sequence_number + 1:
                end_ack_received = True
            if end:
                end_received = True
                end_seq_num = headers['sequence_number']
        with mutex:
            base = 3 if end_ack_received and end_received else base
            end_timer.stop()
            end_timer.start()

    while base < 4:
        head = headers_maker_from_int(flags=flags_maker_from_int(end=True),
                                      sequence_number=conn.sequence_number,
                                      ack=end_seq_num,
                                      source_port=conn.server[1],
                                      destination_port=conn.client[1])
        msg = make_package_from_int(b'', head)
        send_pack(msg, conn.client[0], conn.sender_socket)
        time.sleep(2 * SLEEP_INTERVAL)
    logger.info(f'connection Ended whit {conn.client[0]}:{conn.client[1]}')
