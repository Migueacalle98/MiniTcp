import hashlib
import time


def file_hash(f):
    with open(f, 'rb') as fp:
        data = fp.read()
        return hashlib.sha1(data).hexdigest()


def file_hashes(*files):
    hashes = dict()

    for f in files:
        sha1sum = file_hash(f)
        hashes[f] = sha1sum

    return hashes


def wait_for(func, delta=0.1, timeout=3):
    t = time.time()

    while True:
        tc = time.time()
        if tc > t + timeout:
            raise Exception('timeout exception')

        if func():
            break

        time.sleep(delta)


def is_port_open(address, host_ctrl):
    host, port = address.split(':')

    host_ctrl.cmd('nc -z -v {} {}'.format(host, port))

    return int(host_ctrl.cmd('echo $?')) == 0
