import PySide2.QtWidgets as QtWidgets
from PySide2 import QtCore
import PySide2.QtGui as QtGui
import shiboken2
import maya.api.OpenMaya as om
import maya.api.OpenMayaUI as omui
import maya.OpenMayaUI as old_omui
import maya.cmds as cmds
import numpy as np

def mayaMainWindow():
    # Get the maya mainWindow C++ pointer from the maya API
    maya_main_window_ptr = old_omui.MQtUtil.mainWindow()
    # Wrap the pointer in a QWidget object and return it
    return shiboken2.wrapInstance(long(maya_main_window_ptr),QtWidgets.QWidget)


class CustomColorButton(QtWidgets.QLabel):
    def __init__(self,color=QtCore.Qt.white,parent=None):
        super(CustomColorButton,self).__init__(parent)
        self._color = QtGui.QColor()
        self.setSize(96,24)
        self.setColor(color)

    def setSize(self,width,heigth):
        self.setFixedSize(width,heigth)

    def setColor(self,color):
        color = QtGui.QColor(color)
        if self._color != color:
            self._color = color
        pixmap = QtGui.QPixmap(self.size())
        pixmap.fill(self._color)
        self.setPixmap(pixmap)

        pass

    def getColor(self):
            return self._color

    def selectColor(self):
        color = QtWidgets.QColorDialog.getColor(self._color, self, options=QtWidgets.QColorDialog.DontUseNativeDialog)
        if color.isValid():
            self.setColor(color)



class DialogWindow(QtWidgets.QDialog):
    def __init__(self,parent=mayaMainWindow()):
        # calling the parent class init function with a parent object specified attaches our DialogWindow to the specified object
        super(DialogWindow,self).__init__(parent)
        self.setWindowTitle("LightPlacer")
        self.setMinimumSize(600,200)
        self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint)
        self.distance=10

        self.createWidgets()
        self.createLayouts()
        self.createConnections()

    def createWidgets(self):
        # Create dropdown menu filled with lights
        self.light_list_combo = QtWidgets.QComboBox()
        self.light_list_combo.setMinimumWidth(400)
        self.update_lightList_combo()

        self.update_lightList_button = QtWidgets.QPushButton("Update")

        # Create distance input
        self.distance_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.distance_slider.setMinimum(1)
        self.distance_slider.setMaximum(100)
        self.distance_slider.setValue(self.distance)
        self.distance_lineEdit = QtWidgets.QLineEdit(str(self.distance_slider.value()))
        self.distance_lineEdit.setValidator(QtGui.QIntValidator(1,10000))
        self.distance_lineEdit.setFixedWidth(100)
        self.light_color = CustomColorButton(self.update_light_color())

    def createLayouts(self):
        # Create Layouts
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.form_layout = QtWidgets.QFormLayout(self)
        self.distance_layout = QtWidgets.QHBoxLayout()
        self.light_list_combo_layout = QtWidgets.QHBoxLayout()

        # Organize Layouts
        self.main_layout.addLayout(self.form_layout)
        self.form_layout.addRow("active light:", self.light_list_combo_layout)
        self.form_layout.addRow("distance:", self.distance_layout)
        self.form_layout.addRow("color:",self.light_color)

        # Fill Layouts
        self.light_list_combo_layout.addWidget(self.light_list_combo)
        self.light_list_combo_layout.addWidget(self.update_lightList_button)
        self.distance_layout.addWidget(self.distance_lineEdit)
        self.distance_layout.addWidget(self.distance_slider)

        pass

    def createConnections(self):
        self.light_list_combo.currentIndexChanged.connect(self.update_light_properties)
        self.update_lightList_button.clicked.connect(self.update_lightList_combo)
        self.distance_slider.valueChanged.connect(self.update_distance_lineEdit)
        self.distance_lineEdit.editingFinished.connect(self.update_distance_slider)
        pass

    def closeEvent(*args, **kwargs):
        print "internal close"
        cmds.setToolTo(initial_context)

    def update_light_properties(self):
        self.light_color.setColor(self.update_light_color())

    def update_lightList_combo(self):
        self.lightShapes = sorted(cmds.ls(lights=True))
        self.light_list_combo.clear()
        for light in self.lightShapes:
            light_transform = cmds.listRelatives(light,parent=True, path=True)[0]
            self.light_list_combo.addItem(light_transform)

    def update_light_color(self):
        print "Update light color"
        color = cmds.getAttr("{0}.color".format(self.light_list_combo.currentText()))[0]
        return QtGui.QColor.fromRgbF(color[0],color[1],color[2],1.0)


    def update_distance_lineEdit(self):
        self.distance_lineEdit.setText(str(self.distance_slider.value()))
        cmds.move(  0, 0, (self.distance_slider.value() - self.distance), self.light_list_combo.currentText() , r=True, os=True)
        self.distance = self.distance_slider.value()

    def update_distance_slider(self):
        if int(self.distance_lineEdit.text()) > self.distance_slider.maximum():
            self.distance_slider.setMaximum(int(self.distance_lineEdit.text()))
        self.distance_slider.setValue(int(self.distance_lineEdit.text()))

def PositionLight(light,position,target):
    pass


def normalize(v):
    norm = np.linalg.norm(v)
    if norm == 0:
       return v
    return v / norm


def onPress():
    vpX, vpY, _ = cmds.draggerContext(ctx, query=True, anchorPoint=True)
    pos = om.MPoint()
    dir = om.MVector()

    # calling view to world returns the camera position and viewing direction in the variables pos and dir
    activeView = omui.M3dView().active3dView()
    activeView.viewToWorld(int(vpX), int(vpY), pos, dir)
    camera = activeView.getCamera()
    farClippingPlane =  cmds.getAttr(str(camera)+".farClipPlane")

    # Use API to go through all the meshes in the scene and check if they intersect
    # with a ray from position "pos" in direction "dir"
    for mesh in cmds.ls(type='mesh'):
        selectionList = om.MSelectionList()
        selectionList.add(mesh)
        dagPath = selectionList.getDagPath(0)
        fnMesh = om.MFnMesh(dagPath)

        # cast a ray with length "farClippingPlane" from the camera through the viewplane.
        intersection = fnMesh.closestIntersection(om.MFloatPoint(pos), om.MFloatVector(dir), om.MSpace.kWorld, farClippingPlane, False)

        if intersection:
            hitPoint, hitRayParam, hitFace, hitTriangle, hitBary1, hitBary2 = intersection
            # when nothing intersects the hitpoint will be (0,0,0,1)
            if hitPoint != om.MFloatPoint(0, 0, 0, 1):
                x, y, z, _ = hitPoint
                normal = fnMesh.getClosestNormal(om.MPoint(hitPoint))[0]
                vNormal = np.array([normalize(normal)[0], normalize(normal)[1], normalize(normal)[2]])
                vDirection = np.array(dir)
                vReflection = vDirection - (2 * np.dot(vDirection, vNormal) * vNormal)

                aim_locator = cmds.spaceLocator()[0]
                cmds.setAttr("{0}.translate".format(aim_locator), x, y, z)
                #cam_locator = cmds.spaceLocator(p= [x,y,z] - (vDirection  * int(dialog.distance_lineEdit.text())))

                #print "We've hit {0}!".format(dagPath), "{0}.f[{1}]".format(om.MFnDependencyNode(dagPath.transform()).name(),hitFace), hitPoint, dir
                #print "Surface normal = {0} \nIncidence Vector = {1}\nReflection Vector = {2}".format(vNormal,vDirection,vReflection)

                new_light_position =  [x,y,z] + (vReflection * int(dialog.distance_lineEdit.text()))
                cmds.setAttr("{0}.translate".format(dialog.light_list_combo.currentText()), new_light_position[0], new_light_position[1], new_light_position[2])

                temp_aim_constraint = cmds.aimConstraint(aim_locator, dialog.light_list_combo.currentText(), aim=(0, 0, -1))
                cmds.delete(temp_aim_constraint)
                cmds.delete(aim_locator)

                # Since we've hit something we can break the loop and stop searching
                break
        else:
            print "No Intersection"



if __name__=="__main__":
    ctx = 'myContext'
    initial_context = cmds.currentCtx()

    # attempt to delete the dialog window if it exists already
    try:
        dialog.close()
        dialog.deleteLater()
    except:
        print "There is no dialog"

    print "Opening new dialog"
    dialog = DialogWindow()
    dialog.show()


    #Start picker
    if cmds.draggerContext(ctx, exists=True):
        cmds.deleteUI(ctx)
    cmds.draggerContext(ctx, pressCommand=onPress, name=ctx, cursor='crossHair')
    cmds.setToolTo(ctx)

