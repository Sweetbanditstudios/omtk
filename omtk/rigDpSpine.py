import pymel.core as pymel
from classModule import Module
from classCtrl import BaseCtrl
from rigRibbon import Ribbon
from libs import libCtrlShapes, libPymel, libRigging


class Ctrl_DpSpine_IK(BaseCtrl):
    def __createNode__(self, **kwargs):
        node = libCtrlShapes.create_shape_box(**kwargs)
        return node

class Ctrl_DpSpine_FK(BaseCtrl):
    def __createNode__(self, **kwargs):
        return super(Ctrl_DpSpine_FK, self).__createNode__(normal=(0,1,0), **kwargs)

class DpSpine(Module):
    """
    Spine setup similar to dpAutoRig.
    Note that the spline ctrls orientation follow the world axis by default.
    """
    def __init__(self, *args, **kwargs):
        super(DpSpine, self).__init__(*args, **kwargs)
        self.ctrl_ik_dwn = None
        self.ctrl_ik_upp = None
        self.ctrl_fk_dwn = None
        self.ctrl_fk_mid = None
        self.ctrl_fk_upp = None

    def build(self, *args, **kwargs):
        if len(self.chain) != 3:
            raise Exception("Expected 3 joints. Got {0}.".format(len(self.chain)))

        super(DpSpine, self).build(segmentScaleCompensate=True, *args, **kwargs)

        #
        # Create ctrls
        #

        jnt_dwn = self.input[0]
        jnt_mid = self.input[1]
        jnt_upp = self.input[2]

        pos_dwn_world = jnt_dwn.getTranslation(space='world')
        pos_mid_world = jnt_mid.getTranslation(space='world')
        pos_upp_world = jnt_upp.getTranslation(space='world')

        # Create IK ctrls
        ctrl_ik_dwn_name = self.name_anm.resolve('HipsA')
        ctrl_ik_dwn_size = libRigging.get_recommended_ctrl_size(jnt_dwn)
        if not isinstance(self.ctrl_ik_dwn, Ctrl_DpSpine_IK):
            self.ctrl_ik_dwn = Ctrl_DpSpine_IK()
        self.ctrl_ik_dwn.build(name=ctrl_ik_dwn_name, size=ctrl_ik_dwn_size)
        self.ctrl_ik_dwn.setTranslation(pos_dwn_world)
        self.ctrl_ik_dwn.setParent(self.grp_anm)

        ctrl_ik_upp_name = self.name_anm.resolve('ChestA')
        ctrl_ik_upp_size = libRigging.get_recommended_ctrl_size(jnt_upp)
        if not isinstance(self.ctrl_ik_upp, Ctrl_DpSpine_IK):
            self.ctrl_ik_upp = Ctrl_DpSpine_IK()
        self.ctrl_ik_upp.build(name=ctrl_ik_upp_name, size=ctrl_ik_upp_size)
        self.ctrl_ik_upp.setTranslation(pos_upp_world)
        self.ctrl_ik_upp.setParent(self.ctrl_ik_dwn)

        # Ensure the ctrl_ik_upp pivot is a the middle.
        ctrl_ik_upp_pivot = pos_mid_world - pos_upp_world
        self.ctrl_ik_upp.rotatePivot.set(ctrl_ik_upp_pivot)
        self.ctrl_ik_upp.scalePivot.set(ctrl_ik_upp_pivot)

        # Create FK ctrls
        ctrl_fk_dwn_name = self.name_anm.resolve('HipsB')
        if not isinstance(self.ctrl_fk_dwn, Ctrl_DpSpine_FK):
            self.ctrl_fk_dwn = Ctrl_DpSpine_FK()
        self.ctrl_fk_dwn.build(name=ctrl_fk_dwn_name)
        self.ctrl_fk_dwn.setTranslation(pos_dwn_world)
        self.ctrl_fk_dwn.setParent(self.ctrl_ik_dwn)

        ctrl_fk_upp_name = self.name_anm.resolve('ChestB')
        if not isinstance(self.ctrl_fk_upp, Ctrl_DpSpine_FK):
            self.ctrl_fk_upp = Ctrl_DpSpine_FK()
        self.ctrl_fk_upp.build(name=ctrl_fk_upp_name)
        self.ctrl_fk_upp.setTranslation(pos_upp_world)
        self.ctrl_fk_upp.setParent(self.ctrl_ik_upp)

        ctrl_fk_mid_name = self.name_anm.resolve('Middle1')
        if not isinstance(self.ctrl_fk_mid, Ctrl_DpSpine_FK):
            self.ctrl_fk_mid = Ctrl_DpSpine_FK()
        self.ctrl_fk_mid.build(name=ctrl_fk_mid_name)
        self.ctrl_fk_mid.setTranslation(pos_mid_world)
        self.ctrl_fk_mid.setParent(self.ctrl_ik_dwn)

        # Ensure the ctrl_fk_mid follow ctrl_ik_upp and ctrl_ik_dwn
        pymel.parentConstraint(self.ctrl_fk_dwn, self.ctrl_fk_upp, self.ctrl_fk_mid.offset, maintainOffset=True)

        #
        # Create ribbon rig
        #

        sys_ribbon = Ribbon(self.input)
        sys_ribbon.root = self.root  # TODO: Find a cleaner way
        sys_ribbon.build(segmentScaleCompensate=None, create_ctrl=False, degree=3)
        sys_ribbon.grp_rig.setParent(self.grp_rig)

        # Constraint the ribbon joints to the ctrls
        pymel.parentConstraint(self.ctrl_fk_dwn, sys_ribbon._ribbon_jnts[0], maintainOffset=True)
        pymel.pointConstraint(self.ctrl_fk_mid, sys_ribbon._ribbon_jnts[1], maintainOffset=True)
        pymel.parentConstraint(self.ctrl_fk_upp, sys_ribbon._ribbon_jnts[2], maintainOffset=True)

        # Ensure the last ribbon chain follow the rotation of the chest ctrl.
        last_jnt = self.chain.end
        last_jnt.rotateX.disconnect()
        last_jnt.rotateY.disconnect()
        last_jnt.rotateZ.disconnect()
        pymel.orientConstraint(ctrl_fk_upp_name, last_jnt, maintainOffset=True)

        #
        # Configure the squash
        #

        # Add squash amount attribute
        squash_attr_name = 'squashAmount'
        pymel.addAttr(self.grp_rig, longName=squash_attr_name, defaultValue=1.0)
        attr_squash_amount = self.grp_rig.attr(squash_attr_name)

        # Compute the squash
        attr_stretch_u, attr_stretch_v, node_arc_length = libRigging.create_stretch_attr_from_nurbs_plane(sys_ribbon._ribbon_shape, v=0.5)
        node_arc_length.setParent(self.grp_rig)
        attr_squash_raw = libRigging.create_squash_attr_simple(attr_stretch_u)
        attr_squash = libRigging.create_utility_node('blendTwoAttr', input=[1.0, attr_squash_raw], attributesBlender=attr_squash_amount).output

        # Apply the squash
        # Note that the squash on the first joint is hardcoded to 80%.
        first_jnt = self.chain[0]
        attr_squash_first_jnt = libRigging.create_utility_node('blendTwoAttr', input=[1.0, attr_squash_raw], attributesBlender=0.8).output
        pymel.connectAttr(attr_squash_first_jnt , first_jnt.scaleY)
        pymel.connectAttr(attr_squash_first_jnt , first_jnt.scaleZ)

        middle_jnt = self.chain[1]
        pymel.connectAttr(attr_squash , middle_jnt.scaleY)
        pymel.connectAttr(attr_squash , middle_jnt.scaleZ)

    def get_parent(self, parent):
        if parent == self.chain[0]:
            return self.ctrl_fk_dwn
        if parent == self.chain[-1]:
            return self.ctrl_fk_upp

        return super(DpSpine, self).get_parent(parent)



