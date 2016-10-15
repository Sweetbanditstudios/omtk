import pymel.core as pymel
import libSerialization

def run():
    nets = pymel.ls(type='network')
    net_rig = next(iter(net for net in nets if libSerialization.isNetworkInstanceOfClass(net, 'Rig')), None)

    for net in nets:
        if not libSerialization.isNetworkInstanceOfClass(net, 'Module'):
            continue
        if not net.hasAttr('rig'):
            print("Add attribute 'rig' on {0}".format(net))
            pymel.addAttr(net, longName='rig', niceName='rig', attributeType='message')
        if not net.rig.isDestination():
            pymel.connectAttr(net_rig.message, net.rig)
