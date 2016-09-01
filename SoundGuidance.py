import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import math
import time
import SimpleITK
import numpy as np
import OSC
import numpy.linalg
#from sympy import Plane, Point, Point3D
#
# SoundGuidance
#

class SoundGuidance(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "SoundGuidance" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Examples"]
    self.parent.dependencies = []
    self.parent.contributors = ["John Doe (AnyWare Corp.)"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
    This is an example of scripted loadable module bundled in an extension.
    It performs a simple thresholding on the input volume and optionally captures a screenshot.
    """
    self.parent.acknowledgementText = """
    This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
    and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.

#
# SoundGuidanceWidget
#

class SoundGuidanceWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    
    self.logic = SoundGuidanceLogic()

    # Instantiate and connect widgets ...
    self.defaultStyleSheet = "QLabel { color : #000000; \
                                       font: bold 14px}"

     # Load models first
    self.SoundGuidanceModuleModelsPath = slicer.modules.soundguidance.path.replace("SoundGuidance.py","") + 'Resources/Models/'

    self.boxModel = slicer.util.getNode('boxModel')
    if not self.boxModel:
        slicer.util.loadModel(self.SoundGuidanceModuleModelsPath + 'box.stl')
        self.boxModel = slicer.util.getNode(pattern="box")
        self.boxModelDisplay=self.boxModel.GetModelDisplayNode()
        self.boxModelDisplay.SetColor([0.098,0.5,0.42])
        self.boxModelDisplay.SetOpacity(0.3)

    self.aroModel = slicer.util.getNode('aroModel')
    if not self.aroModel:
        slicer.util.loadModel(self.SoundGuidanceModuleModelsPath + 'aro.stl')
        self.aroModel = slicer.util.getNode(pattern="aro")
        self.aroModelDisplay=self.aroModel.GetModelDisplayNode()
        self.aroModelDisplay.SetColor([0.063,0.14,0.5])
    
    #We create models
    self.needleModel = slicer.util.getNode('NeedleModel')
    if not self.needleModel:
        slicer.util.loadModel(self.SoundGuidanceModuleModelsPath + 'NeedleModel.stl')
        self.needleModel = slicer.util.getNode(pattern="NeedleModel")
        self.needleModelDisplay=self.needleModel.GetModelDisplayNode()
        self.needleModelDisplay.SetColor([0,1,1])

    self.pointerModel = slicer.util.getNode('PointerModel')
    if not self.pointerModel:
        slicer.util.loadModel(self.SoundGuidanceModuleModelsPath + 'PointerModel.stl')
        self.pointerModel = slicer.util.getNode(pattern="PointerModel")
        self.pointerModelDisplay=self.pointerModel.GetModelDisplayNode()
        self.pointerModelDisplay.SetColor([0,0,0])

    self.targetFiducial = slicer.util.getNode('targetFiducial')
    if not self.targetFiducial:
      slicer.util.loadMarkupsFiducialList(self.SoundGuidanceModuleModelsPath + 'Target.fcsv')
      self.targetFiducial = slicer.util.getNode(pattern="Target")

    self.surfaceFiducial = slicer.util.getNode('surfaceFiducial')
    if not self.surfaceFiducial:
      slicer.util.loadMarkupsFiducialList(self.SoundGuidanceModuleModelsPath + 'surfacePoint.fcsv')
      self.surfaceFiducial = slicer.util.getNode(pattern="surfacePoint")

    self.xAxisFiducial = slicer.util.getNode('xAxisFiducial')
    if not self.xAxisFiducial:
      slicer.util.loadMarkupsFiducialList(self.SoundGuidanceModuleModelsPath + 'xAxisFiducial.fcsv')
      self.xAxisFiducial= slicer.util.getNode(pattern="xAxisFiducial")
    # Parameters Area
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)

    # Layout within the dummy collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)
    
    
    #
    # Apply Button
    #
    self.applyButton = qt.QPushButton("Calculate Distance")
    self.applyButton.toolTip = "Run the algorithm."
    self.applyButton.enabled = True
    self.applyButton.checkable = True
    parametersFormLayout.addRow(self.applyButton)

    # Calculate Distance Label
    self.calculateDistanceLabel = qt.QLabel('-')
    self.calculateDistanceLabel.setStyleSheet(self.defaultStyleSheet)
    self.QFormLayoutLabel = qt.QLabel('Distance to target (mm): ')
    self.QFormLayoutLabel.setStyleSheet(self.defaultStyleSheet)
    parametersFormLayout.addRow(self.QFormLayoutLabel, self.calculateDistanceLabel) 

    #
    # Sound Button
    #
    self.playSoundButton = qt.QPushButton("Play Sound")
    self.playSoundButton.enabled = True
    self.playSoundButton.checkable = True
    parametersFormLayout.addRow(self.playSoundButton)



    #Load transformations
    self.pointerToTracker = slicer.util.getNode('PointerToTracker')
    if not self.pointerToTracker:
        print('ERROR: pointerToTracker transform node was not found')

    self.needleToTracker = slicer.util.getNode('NeedleToTracker')
    if not self.needleToTracker:
        print('ERROR: needleToTracker transform node was not found')

    self.referenceToTracker = slicer.util.getNode('ReferenceToTracker')
    if not self.referenceToTracker:
        print('ERROR: referenceToTracker transform node was not found')


    self.trackerToReference = slicer.util.getNode('TrackerToReference')
    if not self.trackerToReference:
        print('ERROR: TrackerToReference transform node was not found')

    # Load models first
    self.SoundGuidanceModuleDataPath = slicer.modules.soundguidance.path.replace("SoundGuidance.py","") + 'Resources/Data/'

    self.needleTipToNeedle = slicer.util.getNode('NeedleTipToNeedle')
    if not self.needleTipToNeedle:
      slicer.util.loadTransform(self.SoundGuidanceModuleDataPath + 'NeedleTipToNeedle.h5')
      self.needleTipToNeedle = slicer.util.getNode(pattern="NeedleTipToNeedle")

    self.pointerTipToPointer = slicer.util.getNode('PointerTipToPointer')
    if not self.pointerTipToPointer:
        slicer.util.loadTransform(self.SoundGuidanceModuleDataPath + 'PointerTipToPointer.h5')
        self.pointerTipToPointer = slicer.util.getNode(pattern="PointerTipToPointer")
      
    self.boxToReference = slicer.util.getNode('BoxToReference')
    if not self.boxToReference:
      slicer.util.loadTransform(self.SoundGuidanceModuleDataPath + 'BoxToReference.h5')
      self.boxToReference = slicer.util.getNode(pattern="BoxToReference")
    
        
    
    # Tranformations to fix models orientation
    self.needleModelToNeedleTip = slicer.util.getNode('needleModelToNeedleTip')
    if not self.needleModelToNeedleTip:
      self.needleModelToNeedleTip=slicer.vtkMRMLLinearTransformNode()
      self.needleModelToNeedleTip.SetName("needleModelToNeedleTip")
      matrixNeedleModel = vtk.vtkMatrix4x4()
      matrixNeedleModel.SetElement( 0, 0, -1 ) # Row 1
      matrixNeedleModel.SetElement( 0, 1, 0 )
      matrixNeedleModel.SetElement( 0, 2, 0 )
      matrixNeedleModel.SetElement( 0, 3, 0 )      
      matrixNeedleModel.SetElement( 1, 0, 0 )  # Row 2
      matrixNeedleModel.SetElement( 1, 1, 1 )
      matrixNeedleModel.SetElement( 1, 2, 0 )
      matrixNeedleModel.SetElement( 1, 3, 0 )       
      matrixNeedleModel.SetElement( 2, 0, 0 )  # Row 3
      matrixNeedleModel.SetElement( 2, 1, 0 )
      matrixNeedleModel.SetElement( 2, 2, -1 )
      matrixNeedleModel.SetElement( 2, 3, 0 )
      self.needleModelToNeedleTip.SetMatrixTransformToParent(matrixNeedleModel)
      slicer.mrmlScene.AddNode(self.needleModelToNeedleTip)

    self.pointerModelToPointerTip = slicer.util.getNode('pointerModelToPointerTip')
    if not self.pointerModelToPointerTip:
      self.pointerModelToPointerTip=slicer.vtkMRMLLinearTransformNode()
      self.pointerModelToPointerTip.SetName("pointerModelToPointerTip")
      matrixPointerModel = vtk.vtkMatrix4x4()
      matrixPointerModel.SetElement( 0, 0, 0 ) # Row 1
      matrixPointerModel.SetElement( 0, 1, 0 )
      matrixPointerModel.SetElement( 0, 2, 1 )
      matrixPointerModel.SetElement( 0, 3, 0 )      
      matrixPointerModel.SetElement( 1, 0, 0 )  # Row 2
      matrixPointerModel.SetElement( 1, 1, 1 )
      matrixPointerModel.SetElement( 1, 2, 0 )
      matrixPointerModel.SetElement( 1, 3, 0 )       
      matrixPointerModel.SetElement( 2, 0, -1 )  # Row 3
      matrixPointerModel.SetElement( 2, 1, 0 )
      matrixPointerModel.SetElement( 2, 2, 0 )
      matrixPointerModel.SetElement( 2, 3, 0 )
      self.pointerModelToPointerTip.SetMatrixTransformToParent(matrixPointerModel)
      slicer.mrmlScene.AddNode(self.pointerModelToPointerTip)

    # connections
    self.applyButton.connect('clicked(bool)', self.onCalculateDistanceButton)
    self.playSoundButton.connect('clicked(bool)', self.onplaySoundButtonClicked)

    
    

    
    #Build Transforms tree

    # Pointer
    self.pointerModel.SetAndObserveTransformNodeID(self.pointerModelToPointerTip.GetID())
    self.pointerModelToPointerTip.SetAndObserveTransformNodeID(self.pointerTipToPointer.GetID())
    self.pointerTipToPointer.SetAndObserveTransformNodeID(self.pointerToTracker.GetID())
    
    # Needle
    self.needleModel.SetAndObserveTransformNodeID(self.needleModelToNeedleTip.GetID())
    self.needleModelToNeedleTip.SetAndObserveTransformNodeID(self.needleTipToNeedle.GetID())
    self.needleTipToNeedle.SetAndObserveTransformNodeID(self.needleToTracker.GetID())

    #Box and aro
    self.boxModel.SetAndObserveTransformNodeID(self.boxToReference.GetID())
    self.aroModel.SetAndObserveTransformNodeID(self.boxToReference.GetID())
    self.targetFiducial.SetAndObserveTransformNodeID(self.boxToReference.GetID())
    self.surfaceFiducial.SetAndObserveTransformNodeID(self.boxToReference.GetID())
    self.xAxisFiducial.SetAndObserveTransformNodeID(self.boxToReference.GetID())
    self.boxToReference.SetAndObserveTransformNodeID(self.referenceToTracker.GetID())  


    # Add vertical spacer
    self.layout.addStretch(1)

   

  def cleanup(self):
    pass

  
  def onCalculateDistanceButton(self):
    
    self.logic.transferValues(self.needleTipToNeedle, self.pointerTipToPointer, self.needleToTracker, self.targetFiducial, self.surfaceFiducial, self.boxToReference, self.xAxisFiducial)

    self.logic.setOutPutDistanceLabel(self.calculateDistanceLabel)
    
    
    self.logic.plotLineZaxis()
    self.logic.addCalculateDistanceObserver()

  def onplaySoundButtonClicked(self):
    #IP = "172.16.203.210"
    self.logic.changeSendDataStatus()
    #initialization
    #c = SendOSC()
    #c.connect("localhost", 8080)
    #self.logic.activateOSC()
    

#
# SoundGuidanceLogic
#

class SoundGuidanceLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  def __init__(self):
    self.sendDataOK = False
    self.OSC_active = False
    self.line = slicer.util.getNode('Line')
    if not self.line:
      self.line = slicer.vtkMRMLModelNode()
      self.line.SetName('Line')
      linePolyData = vtk.vtkPolyData()
      self.line.SetAndObservePolyData(linePolyData)      
      modelDisplay = slicer.vtkMRMLModelDisplayNode()
      modelDisplay.SetSliceIntersectionVisibility(True)
      modelDisplay.SetColor(0,1,0)
      slicer.mrmlScene.AddNode(modelDisplay)      
      self.line.SetAndObserveDisplayNodeID(modelDisplay.GetID())      
      slicer.mrmlScene.AddNode(self.line)
  def transferValues(self, needleTTNeedle, pointerTTPointer, needleTTracker, tFiducial,sFiducial, btr, xaf):

    self.needleTipToNeedle = needleTTNeedle
    self.pointerTipToPointer = pointerTTPointer
    self.needleToTracker = needleTTracker
    self.targetFiducial = tFiducial
    self.surfaceFiducial = sFiducial
    self.boxToReference = btr
    self.xAxisFiducial = xaf

  def addCalculateDistanceObserver(self):
    print("[TEST] addCalculateDistanceObserver")
    #self.tipFiducial.SetAndObserveTransformNodeID(self.toolTipToTool.GetID())
    self.observerTag = self.needleToTracker.AddObserver('ModifiedEvent', self.calculateCallback) # slicer.vtkMRMLMarkupsNode.MarkupAddedEvent
    logging.info('addCalculateDistanceObserver')
      
  def removeCalculateDistanceObserver(self):
    print("[TEST] removeCalculateDistanceObserver")
    self.callbackObserverTag = 1
    if self.callbackObserverTag != -1:
      self.toolToReference.RemoveObserver(self.observerTag)
      self.callbackObserverTag = -1
      logging.info('removeCalculateDistanceObserver')
      
  def calculateCallback(self, transformNode, event=None):
    self.calculateDistance()

  def calculateDistance(self):

    pointerTipPoint = [0.0,0.0,0.0]
    
     
    m = vtk.vtkMatrix4x4()
    self.pointerTipToPointer.GetMatrixTransformToWorld(m)
    pointerTipPoint[0] = m.GetElement(0, 3)
    pointerTipPoint[1] = m.GetElement(1, 3)
    pointerTipPoint[2] = m.GetElement(2, 3)
    

    distance = math.sqrt(math.pow(pointerTipPoint[0]-self.pos[0], 2) + math.pow(pointerTipPoint[1]-self.pos[1], 2) + math.pow(pointerTipPoint[2]-self.pos[2], 2))
    
    # La distancia se da en mm ----> 50mm = 5cm
    # Voy a normalizar con un tope de 20cm
    normalizedDistance = [(distance - 0)/200]
    
    if self.OSC_active:
      #print ("HOLAAA")
      c.send("/dumpOSC/0/0", 0)

    self.outputDistanceLabel.setText('%.1f' % distance)
    
    self.pos = [self.pos[i] for i in (0,1,2)]
    self.drawLineBetweenPoints(pointerTipPoint, self.pos)

    if self.sendDataOK:
      self.sendData(normalizedDistance)

  def setOutPutDistanceLabel(self, label):
    self.outputDistanceLabel = label

  def drawLineBetweenPoints(self, point1, point2):        
    # Create a vtkPoints object and store the points in it
    points = vtk.vtkPoints()
    points.InsertNextPoint(point1)
    points.InsertNextPoint(point2)

    # Create line
    line = vtk.vtkLine()
    #line.SetLineWidth(12.0)
    line.GetPointIds().SetId(0,0) 
    line.GetPointIds().SetId(1,1)
    lineCellArray = vtk.vtkCellArray()
    lineCellArray.InsertNextCell(line)
    
    # Update model data
    self.line.GetPolyData().SetPoints(points)
    self.line.GetPolyData().SetLines(lineCellArray)

  def activateOSC(self):
    self.OSC_active = True
 
  def sendData(self, distance):

    client = OSC.OSCClient()
    client.connect(("192.168.0.70",7400))

    message = OSC.OSCMessage()
    message.setAddress("/dumpOSC/0/0")
    message.append(distance)

    client.send(message)
  def changeSendDataStatus(self):
    self.sendDataOK = True

  def plotLineZaxis(self):

    # Create a vtkPoints object and store the points in it
    self.pos = [0.0, 0.0, 0.0, 0.0]  
    self.targetFiducial.GetNthFiducialWorldCoordinates(0, self.pos)
    targetP = [self.pos[i] for i in (0,1,2)]

    self.surfPoint = [0.0, 0.0, 0.0, 0.0]  
    self.surfaceFiducial.GetNthFiducialWorldCoordinates(0, self.surfPoint)
    surfaceP = [self.surfPoint[i] for i in (0,1,2)]

    self.zVector = np.subtract(targetP,surfaceP)

    points = vtk.vtkPoints()
    points.InsertNextPoint(targetP)

    points.InsertNextPoint(surfaceP)

    # Create line
    line = vtk.vtkLine()
    line.GetPointIds().SetId(0,0)
    line.GetPointIds().SetId(1,1)
    lineCellArray = vtk.vtkCellArray()
    lineCellArray.InsertNextCell(line)

    self.lineNode = slicer.vtkMRMLModelNode()
    self.lineNode.SetName('LineZ')
    linePolyData = vtk.vtkPolyData()
    self.lineNode.SetAndObservePolyData(linePolyData)
    modelDisplay = slicer.vtkMRMLModelDisplayNode()
    modelDisplay.SetSliceIntersectionVisibility(True)
    modelDisplay.SetColor(1,1,1)
    slicer.mrmlScene.AddNode(modelDisplay)

    self.lineNode.SetAndObserveDisplayNodeID(modelDisplay.GetID())
    slicer.mrmlScene.AddNode(self.lineNode)

    self.lineNode.GetPolyData().SetPoints(points)
    self.lineNode.GetPolyData().SetLines(lineCellArray)

    #self.lineNode.SetAndObserveTransformNodeID(self.boxToReference.GetID())
    self.drawPlane(surfaceP, self.zVector)
    self.definePlaneAxis(surfaceP, self.zVector)

  def drawPlane(self, m, V_norm):
    scene = slicer.mrmlScene

    #create a plane to cut,here it cuts in the XZ direction (xz normal=(1,0,0);XY =(0,0,1),YZ =(0,1,0)
    planex=vtk.vtkPlane()
    planex.SetOrigin(m[0],m[1],m[2])
    planex.SetNormal(V_norm[0],V_norm[1],V_norm[2])

    renderer = slicer.app.layoutManager().threeDWidget(0).threeDView().renderWindow().GetRenderers().GetFirstRenderer()
    viewSize = renderer.ComputeVisiblePropBounds()
    #viewSize = (-50.0, 50.0, -50.0, 50.0, -50.0, 50.0)


    planexSample = vtk.vtkSampleFunction()
    planexSample.SetImplicitFunction(planex)
    planexSample.SetModelBounds(viewSize)
    #planexSample.SetSampleDimensions(200,200,200)
    planexSample.ComputeNormalsOff()
    plane1 = vtk.vtkContourFilter()
    plane1.SetInputConnection(planexSample.GetOutputPort())


    # Create model Plane A node
    planeA = slicer.vtkMRMLModelNode()
    planeA.SetScene(scene)
    planeA.SetName("X-Y Plane")
    planeA.SetAndObservePolyData(plane1.GetOutput())

    # Create display model Plane A node
    planeAModelDisplay = slicer.vtkMRMLModelDisplayNode()
    planeAModelDisplay.SetColor(0.145,0.77,0.596)
    
    planeAModelDisplay.BackfaceCullingOff()
    planeAModelDisplay.SetScene(scene)
    scene.AddNode(planeAModelDisplay)
    planeA.SetAndObserveDisplayNodeID(planeAModelDisplay.GetID())

    #Add to scene
    planeAModelDisplay.SetInputPolyDataConnection(plane1.GetOutputPort())
    scene.AddNode(planeA)

    # adjust center of 3d view to plane
    layoutManager = slicer.app.layoutManager()
    threeDWidget = layoutManager.threeDWidget(0)
    threeDView = threeDWidget.threeDView()
    threeDView.resetFocalPoint()

  def definePlaneAxis(self, oPoint, zV):
    
    xP = [0.0, 0.0, 0.0, 0.0]  
    self.xAxisFiducial.GetNthFiducialWorldCoordinates(0, xP)
   # a = Plane(Point3D(1,4,6), normal_vector=(2,4,6))
    
    xAxisPoint = [xP[i] for i in (0,1,2)]
 
    self.zVector = zV
    self.xVector = np.subtract(xAxisPoint,oPoint)

    self.yVector = np.cross(self.zVector, self.xVector)

    #Para hallar la matriz de transformacion es necesario tener vectores unitarios!

    xUnitario = self.xVector/numpy.linalg.norm(self.xVector)
    yUnitario = self.yVector/numpy.linalg.norm(self.yVector)
    zUnitario = self.zVector/numpy.linalg.norm(self.zVector)

    print type(self.xVector)
    print ('Vector x:')
    print (self.xVector)
    print (self.xVector[0])
    print ('Vector y:')
    print (self.yVector)
    print ('Vector z:')
    print (self.zVector)
    print oPoint

    #We create the transformation matrix so that change the coordinates system:
    R = vtk.vtkMatrix3x3()
    R.SetElement( 0, 0, xUnitario[0]  ) # Row 1
    R.SetElement( 0, 1, xUnitario[1]  )
    R.SetElement( 0, 2, xUnitario[2]  )
    R.SetElement( 1, 0, yUnitario[0] )  # Row 2
    R.SetElement( 1, 1, yUnitario[1] )
    R.SetElement( 1, 2, yUnitario[2] )
    R.SetElement( 2, 0, zUnitario[0] )  # Row 3
    R.SetElement( 2, 1, zUnitario[1] )
    R.SetElement( 2, 2, zUnitario[2] )
    
    resultPoint = [0.0, 0.0, 0.0]
    R.MultiplyPoint(oPoint, resultPoint)
   
    matrixTransfBOX = vtk.vtkMatrix4x4()
    matrixTransfBOX.SetElement( 0, 0, xUnitario[0] ) # Row 1
    matrixTransfBOX.SetElement( 0, 1, xUnitario[1] )
    matrixTransfBOX.SetElement( 0, 2, xUnitario[2] )
    matrixTransfBOX.SetElement( 0, 3, -resultPoint[0] )      
    matrixTransfBOX.SetElement( 1, 0, yUnitario[0] )  # Row 2
    matrixTransfBOX.SetElement( 1, 1, yUnitario[1] )
    matrixTransfBOX.SetElement( 1, 2, yUnitario[2] )
    matrixTransfBOX.SetElement( 1, 3, -resultPoint[1] )       
    matrixTransfBOX.SetElement( 2, 0, zUnitario[0] )  # Row 3
    matrixTransfBOX.SetElement( 2, 1, zUnitario[1] )
    matrixTransfBOX.SetElement( 2, 2, zUnitario[2] )
    matrixTransfBOX.SetElement( 2, 3, -resultPoint[2] )
    matrixTransfBOX.SetElement( 3, 0, 0 )  # Row 4
    matrixTransfBOX.SetElement( 3, 1, 0)
    matrixTransfBOX.SetElement( 3, 2, 0 )
    matrixTransfBOX.SetElement( 3, 3, 1 )
      
    print (matrixTransfBOX)
    #self.planeA.SetAndObserveTransformNodeID(self.boxToReference.GetID())
    oPoint = oPoint + [1.0]
    nuevoOrigen = [0.0, 0.0, 0.0 , 0.0]
    matrixTransfBOX.MultiplyPoint(oPoint, nuevoOrigen)

    print nuevoOrigen

class SoundGuidanceTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_SoundGuidance1()

  def test_SoundGuidance1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    import urllib
    downloads = (
        ('http://slicer.kitware.com/midas3/download?items=5767', 'FA.nrrd', slicer.util.loadVolume),
        )

    for url,name,loader in downloads:
      filePath = slicer.app.temporaryPath + '/' + name
      if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
        logging.info('Requesting download %s from %s...\n' % (name, url))
        urllib.urlretrieve(url, filePath)
      if loader:
        logging.info('Loading %s...' % (name,))
        loader(filePath)
    self.delayDisplay('Finished with download and loading')

    volumeNode = slicer.util.getNode(pattern="FA")
    logic = SoundGuidanceLogic()
    self.assertTrue( logic.hasImageData(volumeNode) )
    self.delayDisplay('Test passed!')


from OSC import OSCClient, OSCMessage

class SendOSC(object):

    def __init__(self):
        self.osc_message = None
        self.osc_client = OSCClient()
        self.osc_message = OSCMessage()        
        
        self.ip = ""
        self.port = 0

    def connect(self, ip="localhost", port=8080):
        self.ip = ip
        self.port = port
        self.osc_client.connect((self.ip, self.port))

    def send(self, address, value):
        self.osc_message.setAddress(address)
        self.osc_message.append(value)
        self.osc_client.send(self.osc_message)

    def send_distane(self, distance):
        oscdump = "/dumpOSC/DistanceTipTarget"
        self.send(oscdump, distance)

    def send_needle_tip_position(self, x, y, z):
        oscdump = "/dumpOSC/needltip/x"
        self.send(oscdump, x)
        oscdump = "/dumpOSC/needltip/y"
        self.send(oscdump, y)
        oscdump = "/dumpOSC/needltip/z"
        self.send(oscdump, z)