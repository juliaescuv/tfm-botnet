from mininet.net import Mininet
from mininet.node import Controller
from mininet.link import TCLink

TOTAL_BOTS = 40
BW_BOTS = 100   # Mbps: enlaces de los bots (holgados)
BW_C2 = 10      # Mbps: enlace del C2 (CUELLO DE BOTELLA compartido por todos los bots)

def build_network():
    net = Mininet(controller=Controller, link=TCLink)

    net.addController("c0")
    s1 = net.addSwitch("s1")

    c2 = net.addHost("c2", ip="10.0.0.100/24")
    # El enlace del C2 es el cuello de botella: todos los bots compiten por él
    net.addLink(c2, s1, bw=BW_C2)

    for i in range(1, TOTAL_BOTS + 1):
        bot = net.addHost(f"b{i}", ip=f"10.0.0.{i}/24")
        net.addLink(bot, s1, bw=BW_BOTS)

    return net
