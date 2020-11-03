import unittest

from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import OVSController
from mininet.node import CPULimitedHost

from tests import config
from tests.topos.single_switch import SingleSwitchTopo


class TestServeFile(unittest.TestCase):
    def setUp(self):
        setLogLevel(config.MININET_LOG_LEVEL)
        self.topo = SingleSwitchTopo(n=2)
        self.net = Mininet(topo=self.topo, host=CPULimitedHost, link=TCLink)
        self.net.start()

    def test_download_small(self):
        self.net.pingAll()

    def tearDown(self):
        self.net.stop()
