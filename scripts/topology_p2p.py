from mininet.net import Mininet
from mininet.node import Controller
from mininet.link import TCLink

TOTAL_BOTS = 40
BW_BOTS = 100      # Mbps: enlaces bot<->switch (holgados)
BW_TRUNK = 10      # Mbps: enlaces troncales switch<->switch (CUELLO DE BOTELLA)

def build_network():
    net = Mininet(controller=Controller, link=TCLink)

    net.addController("c0")

    switches = []
    for i in range(1, 5):
        switches.append(net.addSwitch(f"s{i}"))

    # Enlaces troncales = cuello de botella: el tráfico entre zonas del anillo los cruza
    for i in range(len(switches) - 1):
        net.addLink(switches[i], switches[i + 1], bw=BW_TRUNK)

    for i in range(1, TOTAL_BOTS + 1):
        bot = net.addHost(f"b{i}", ip=f"10.0.0.{i}/24")
        sw = switches[(i - 1) % len(switches)]
        net.addLink(bot, sw, bw=BW_BOTS)

    return net
