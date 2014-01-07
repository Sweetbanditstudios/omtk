import pymel.core as pymel
from classRigCtrl import RigCtrl
from classRigPart import RigPart
import libUtils as Utils


class CtrlIk(RigCtrl):
    kAttrName_State = 'ikFk'

    def __init__(self, *args, **kwargs):
        super(CtrlIk, self).__init__(*args, **kwargs)

        pymel.addAttr(self.node, longName=self.kAttrName_State)
        self.m_attState = getattr(self.node, self.kAttrName_State)


class CtrlIkSwivel(RigCtrl):
    def __init__(self, _oLineTarget, *args, **kwargs):
        super(CtrlIkSwivel, self).__init__(*args, **kwargs)

        # Create line
        oCtrlShape = self.node.getShape()
        oLineShape = pymel.createNode('annotationShape')
        oLineTransform = oLineShape.getParent()
        pymel.connectAttr(oCtrlShape.worldMatrix, oLineShape.dagObjectMatrix[0], force=True)
        oLineTransform.setParent(self.offset)
        pymel.pointConstraint(_oLineTarget, oLineTransform)

    def __createNode__(self, *args, **kwargs):
        n = super(CtrlIkSwivel, self).__createNode__(*args, **kwargs)
        oMake = n.getShape().create.inputs()[0]
        oMake.radius.set(oMake.radius.get() * 0.5)
        oMake.degree.set(1)
        oMake.sections.set(4)
        return n

# Todo: Support more complex IK limbs (ex: 2 knees)
class IK(RigPart):
    def __init__(self, *args, **kwargs):
        super(IK, self).__init__(*args, **kwargs)
        self.bStretch = True

    def Build(self, _bOrientIkCtrl=True, *args, **kwargs):
        super(IK, self).Build(*args, **kwargs)
        oChainS = self.aInput[0]
        oChainE = self.aInput[self.iCtrlIndex]

        # Compute chainLength
        fChainLength = 0
        for oInput in self.aInput[1:self.iCtrlIndex + 1]:
            fChainLength += oInput.t.get().length()

        # Compute swivel position
        p3ChainS = oChainS.getTranslation(space='world')
        p3ChainE = oChainE.getTranslation(space='world')
        fRatio = self.aInput[1].t.get().length() / fChainLength
        p3SwivelBase = (p3ChainE - p3ChainS) * fRatio + p3ChainS
        p3SwivelDir = (self.aInput[1].getTranslation(space='world') - p3SwivelBase).normal()
        p3SwivelPos = p3SwivelBase + p3SwivelDir * fChainLength

        # Create ikChain
        oChainRoot = pymel.createNode('transform', name=self._pNameMapRig.Serialize('ikChain'), parent=self.oGrpRig)
        oChainRoot.setMatrix(oChainS.getMatrix(worldSpace=True), worldSpace=True)
        oChainS.setParent(oChainRoot)

        self._oIkHandle, oIkEffector = pymel.ikHandle(startJoint=oChainS, endEffector=oChainE, solver='ikRPsolver')
        self._oIkHandle.rename(self._pNameMapRig.Serialize('ikHandle'))
        self._oIkHandle.setParent(oChainRoot)
        oIkEffector.rename(self._pNameMapRig.Serialize('ikEffector'))

        # Create ctrls
        self._oCtrlIK = CtrlIk()
        self._oCtrlIK.setParent(self.oGrpAnm)
        self._oCtrlIK.rename(self._pNameMapAnm.Serialize('ik'))
        self._oCtrlIK.offset.setTranslation(oChainE.getTranslation(space='world'), space='world')
        if _bOrientIkCtrl is True:
            print _bOrientIkCtrl
            self._oCtrlIK.offset.setRotation(oChainE.getRotation(space='world'), space='world')

        self._oCtrlSwivel = CtrlIkSwivel(self.aInput[1])
        self._oCtrlSwivel.setParent(self.oGrpAnm)
        self._oCtrlSwivel.rename(self._pNameMapAnm.Serialize('ikSwivel'))
        self._oCtrlSwivel.offset.setTranslation(p3SwivelPos, space='world')
        self._oCtrlSwivel.offset.setRotation(self.aInput[self.iCtrlIndex - 1].getRotation(space='world'), space='world')

        # Connect rig -> anm
        pymel.pointConstraint(self._oCtrlIK, self._oIkHandle)
        pymel.orientConstraint(self._oCtrlIK, oChainE, maintainOffset=True)
        pymel.poleVectorConstraint(self._oCtrlSwivel, self._oIkHandle)

        # Connect stretch
        if self.bStretch is True:
            attChainDistance = Utils.CreateUtilityNode('distanceBetween', inMatrix1=oChainRoot.worldMatrix,
                                                       inMatrix2=self._oCtrlIK.worldMatrix).distance
            attStretch = Utils.CreateUtilityNode('multiplyDivide', operation=2, input1X=attChainDistance,
                                                 input2X=fChainLength).outputX
            attStretch = Utils.CreateUtilityNode('condition', operation=2, firstTerm=attStretch, secondTerm=1.0,
                                                 colorIfTrueR=attStretch, colorIfFalseR=1.0).outColorR # GreaterThan
            for oInput in self.aInput[1:self.iCtrlIndex + 1]:
                attNewPos = Utils.CreateUtilityNode('multiplyDivide', input1=oInput.t.get(), input2X=attStretch,
                                                    input2Y=attStretch, input2Z=attStretch).output
                pymel.connectAttr(attNewPos, oInput.t)

        # Connect to parent
        if self._oParent is not None:
            pymel.parentConstraint(self._oParent, oChainRoot, maintainOffset=True)
