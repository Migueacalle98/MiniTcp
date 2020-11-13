import os
import shutil
import unittest
import time
from functools import partial

from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import OVSController
from mininet.node import CPULimitedHost

from tests import config
from tests.topos.single_switch import SingleSwitchTopo
from tests.utils import file_hashes, is_port_open, wait_for


class TestServeFile(unittest.TestCase):
    def setUp(self):
        try:
            os.makedirs('tests/data/tmp-data')
        except:
            pass
        setLogLevel(config.MININET_LOG_LEVEL)
        self.topo = SingleSwitchTopo(n=2)
        self.net = Mininet(topo=self.topo, host=CPULimitedHost, link=TCLink)
        self.net.start()

    def test_download_small(self):
        server_file = 'tests/data/small.txt'
        client_file = 'tests/tmp-data/small.txt'

        h1, h2 = self.net.get('h1', 'h2')

        address = '{}:8888'.format(h1.IP())

        h1.cmdPrint('{} ./serve_file/__main__.py --accept {} --file {} &'
            .format(config.PYTHON, address, server_file)
        )           
        
        # wait_for(partial(is_port_open, address, h1))
        
        h2.cmdPrint(
            '{} ./serve_file/__main__.py --dial {} --file {}'
            .format(config.PYTHON, address, client_file)
        )
            
        status = int(h2.cmd('echo $?'))

        self.assertEqual(status, 0)

        self.assertTrue(os.path.isfile(client_file))

        hashes = set(
            file_hashes(server_file, client_file).values()
        )

        self.assertEqual(len(hashes), 1)

    def tearDown(self):
        self.net.stop()
        shutil.rmtree('tests/data/tmp-data')
