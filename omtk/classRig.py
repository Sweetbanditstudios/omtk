from maya import cmds
import pymel.core as pymel
from classCtrl import BaseCtrl
from classNode import Node
from classModule import Module
import className
from libs import libPymel
import time


class CtrlRoot(BaseCtrl):
    """
    The main ctrl. Support global uniform scaling only.
    """
    def __init__(self, *args, **kwargs):
        super(CtrlRoot, self).__init__(create_offset=False, *args, **kwargs)

    def __createNode__(self, *args, **kwargs):
        """
        Create a wide circle.
        """
        # use meshes boundinx box
        node = pymel.circle(*args, **kwargs)[0]
        make = node.getShape().create.inputs()[0]
        make.radius.set(10)
        make.normal.set((0,1,0))

        # Add a globalScale attribute to replace the sx, sy and sz.
        pymel.addAttr(node, longName='globalScale', k=True, defaultValue=1.0)
        pymel.connectAttr(node.globalScale, node.sx)
        pymel.connectAttr(node.globalScale, node.sy)
        pymel.connectAttr(node.globalScale, node.sz)
        node.s.set(lock=True, channelBox=False)

        return node

class Rig(object):
    DEFAULT_NAME = 'untitled'

    #
    # className.BaseNomenclature implementation
    #

    def _get_nomenclature_cls(self):
        """
        :return: Return the nomenclature type class that will determine the production specific nomenclature to use.
        """
        return className.BaseName

    @property
    def nomenclature(self):
        """
        Singleton that will return the nomenclature to use.
        """
        return self._get_nomenclature_cls()

    #
    # collections.MutableSequence implementation
    #
    def __getitem__(self, item):
        self.children.__getitem__(item)

    def __setitem__(self, index, value):
        self.children.__setitem__(index, value)

    def __delitem__(self, index):
        self.children.__delitem__(index)

    def __len__(self):
        return self.children.__len__()

    def insert(self, index, value):
        self.children.insert(index, value)
        value._parent = self # Store the parent for optimized network serialization (see libs.libSerialization)

    def __iter__(self):
        return iter(self.children)

    def __init__(self, name=None):
        self.name = name if name else self.DEFAULT_NAME
        self.children = []
        self.grp_anms = None
        self.grp_geos = None
        self.grp_jnts = None
        self.grp_rigs = None
        self.layer_anm = None
        self.layer_geo = None
        self.layer_rig = None

    def __str__(self):
        return '<rig {0}/>'.format(self.name)

    #
    # libSerialization implementation
    #
    def __callbackNetworkPostBuild__(self):
        """
        Cleaning routine automatically called by libSerialization after a network import.
        """

        # Ensure there's no None value in the .children array.
        try:
            self.children = filter(None, self.children)
        except (AttributeError, TypeError):
            pass


    #
    # Main implementation
    #

    def add_module(self, module):
        #if not isinstance(part, Module):
        #    raise IOError("[Rig:AddPart] Unexpected type. Got '{0}'. {1}".format(type(part), part))
        module.root = self
        self.children.append(module)

    def is_built(self):
        """
        :return: True if any module dag nodes exist in the scene.
        """
        for child in self.children:  # note: libSerialization can return None anytime
            if child.is_built():
                return True
        return False

    def _clean_invalid_pynodes(self):
        fnCanDelete = lambda x: (isinstance(x, (pymel.PyNode, pymel.Attribute)) and not libPymel.is_valid_PyNode(x))
        for key, val in self.__dict__.iteritems():
            if fnCanDelete(val):
                setattr(self, key, None)
            elif isinstance(val, (list, set, tuple)):
                for i in reversed(range(len(val))):
                    if fnCanDelete(val[i]):
                        val.pop(i)
                if len(val) == 0:
                    setattr(self, key, None)

    def build(self, **kwargs):
        # Aboard if already built
        if self.is_built():
            pymel.warning("Can't build {0} because it's already built!".format(self))
            return False

        sTime = time.time()

        #
        # Prebuild
        #

        # Ensure we got a root joint
        # If needed, parent orphan joints to this one
        all_root_jnts = libPymel.ls_root_jnts()

        if not libPymel.is_valid_PyNode(self.grp_jnts):
            if cmds.objExists(self.nomenclature.root_jnt_name):
                self.grp_jnts = pymel.PyNode(self.nomenclature.root_jnt_name)
            else:
                self.grp_jnts = pymel.createNode('joint', name=self.nomenclature.root_jnt_name)

        all_root_jnts.setParent(self.grp_jnts)

        #
        # Build
        #

        #try:
        for child in self.children:
            #try:
            child.build(**kwargs)
            #except Exception, e:
            #    logging.error("\n\nAUTORIG BUILD FAIL! (see log)\n")
            #    traceback.print_stack()
            #    logging.error(str(e))
            #    raise e

        #
        # Post-build
        #

        # Create anm root
        anm_grps = [module.grp_anm for module in self.children if module.grp_anm is not None]
        if not isinstance(self.grp_anms, CtrlRoot):
            self.grp_anms = CtrlRoot()
        if not self.grp_anms.is_built():
            self.grp_anms.build()
        self.grp_anms.rename(self.nomenclature.root_anm_name)
        for anm_grp in anm_grps:
            anm_grp.setParent(self.grp_anms)

        # Connect globalScale attribute to each modules globalScale.
        for child in self.children:
            if child.globalScale:
                pymel.connectAttr(self.grp_anms.globalScale, child.globalScale, force=True)

        # Constraint grp_jnts to grp_anms
        pymel.delete([child for child in self.grp_jnts.getChildren() if isinstance(child, pymel.nodetypes.Constraint)])
        pymel.parentConstraint(self.grp_anms, self.grp_jnts, maintainOffset=True)
        pymel.connectAttr(self.grp_anms.globalScale, self.grp_jnts.scaleX, force=True)
        pymel.connectAttr(self.grp_anms.globalScale, self.grp_jnts.scaleY, force=True)
        pymel.connectAttr(self.grp_anms.globalScale, self.grp_jnts.scaleZ, force=True)

        # Create rig root
        rig_grps = [module.grp_rig for module in self.children if module.grp_rig is not None]
        if not isinstance(self.grp_rigs, Node):
            self.grp_rigs = Node()
        if not self.grp_rigs.is_built():
            self.grp_rigs.build()
        self.grp_rigs.rename(self.nomenclature.root_rig_name)
        for rig_grp in rig_grps:
            rig_grp.setParent(self.grp_rigs)

        # Create geo root
        all_geos = libPymel.ls_root_geos()
        if not isinstance(self.grp_geos, Node):
            self.grp_geos = Node()
        if not self.grp_geos.is_built():
            self.grp_geos.build()
        self.grp_geos.rename(self.nomenclature.root_geo_name)
        all_geos.setParent(self.grp_geos)

        # Setup displayLayers
        self.layer_anm = pymel.createDisplayLayer(name=self.nomenclature.layer_anm_name, number=1, empty=True)
        pymel.editDisplayLayerMembers(self.layer_anm, self.grp_anms, noRecurse=True)
        self.layer_anm.color.set(17)  # Yellow

        self.layer_rig = pymel.createDisplayLayer(name=self.nomenclature.layer_rig_name, number=1, empty=True)
        pymel.editDisplayLayerMembers(self.layer_rig, self.grp_rigs, noRecurse=True)
        pymel.editDisplayLayerMembers(self.layer_rig, self.grp_jnts, noRecurse=True)
        self.layer_rig.color.set(13)  # Red
        #self.layer_rig.visibility.set(0)  # Hidden
        self.layer_rig.displayType.set(2)  # Frozen

        self.layer_geo = pymel.createDisplayLayer(name=self.nomenclature.layer_geo_name, number=1, empty=True)
        pymel.editDisplayLayerMembers(self.layer_geo, self.grp_geos, noRecurse=True)
        self.layer_geo.color.set(12)  # Green?
        self.layer_geo.displayType.set(2)  # Frozen

        print ("[classRigRoot.Build] took {0} ms".format(time.time() - sTime))

        return True

    def unbuild(self, **kwargs):
        """
        :param kwargs: Potential parameters to pass recursively to the unbuild method of each module.
        :return: True if successful.
        """
        # Unbuild all children
        for child in self.children:
            if child.is_built():
                child.unbuild(**kwargs)

        # Delete anm_grp
        if isinstance(self.grp_anms, CtrlRoot) and self.grp_anms.is_built():
            self.grp_anms.unbuild()

        # Delete the rig group if it isnt used anymore
        if libPymel.is_valid_PyNode(self.grp_rigs) and len(self.grp_rigs.getChildren()) == 0:
            pymel.delete(self.grp_rigs)
            self.grp_rigs = None

        # Delete the displayLayers
        if libPymel.is_valid_PyNode(self.layer_anm):
            pymel.delete(self.layer_anm)
            self.layer_anm = None
        if libPymel.is_valid_PyNode(self.layer_geo):
            pymel.delete(self.layer_geo)
            self.layer_geo = None
        if libPymel.is_valid_PyNode(self.layer_rig):
            pymel.delete(self.layer_rig)

        # Remove any references to missing pynodes
        self._clean_invalid_pynodes()

        return True

