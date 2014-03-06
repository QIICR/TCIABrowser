from __future__  import division
import urllib2, urllib,sys, os
import time
import string, json, zipfile, os.path
import csv
import xml.etree.ElementTree as ET
import webbrowser
import unittest
from __main__ import vtk, qt, ctk, slicer
import TCIABrowserLib

#
# TCIABrowser
#

class TCIABrowser:
  def __init__(self, parent):
    parent.title = "TCIA Browser" # TODO make this more human readable by adding spaces
    parent.categories = ["Informatics"]
    parent.dependencies = []
    parent.contributors = ["Alireza Mehrtash (SPL, BWH), Andrey Fedorov (SPL, BWH)"]  
    parent.helpText = """
    Connect to TCIA web archive and get a list of all available collections. From collection selector choose a collection and the patients table will be populated. Click on a patient and the studies for the patient will be presented. Do the same for studies. Finally choose a series from the series table and download the images from the server by pressing the "Download and Load" button. 
    """
    parent.acknowledgementText = """
    Supported by NIH U01CA151261 (PI Fennessy) and U24 CA180918 (PIs Kikinis and Fedorov)
""" 
    self.parent = parent

    # Add this test to the SelfTest module's list for discovery when the module
    # is created.  Since this module may be discovered before SelfTests itself,
    # create the list if it doesn't already exist.
    try:
      slicer.selfTests
    except AttributeError:
      slicer.selfTests = {}
    slicer.selfTests['TCIABrowser'] = self.runTest

  def runTest(self):
    tester = TCIABrowserTest()
    tester.runTest()
#
# qTCIABrowserWidget
#

class TCIABrowserWidget:
  def __init__(self, parent = None):
    if not parent:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout(qt.QVBoxLayout())
      self.parent.setMRMLScene(slicer.mrmlScene)
    else:
      self.parent = parent
    self.layout = self.parent.layout()
    if not parent:
      self.setup()
      self.parent.show()

    self.loadToScene = False

    self.browserWidget = qt.QWidget()
    self.browserWidget.setWindowTitle('TCIA Browser')

    self.downloadProgressBarCounts = 0 
    self.downloadProgressBarDict = {}
    self.selectedSereisNicknamesDic = {} 
    self.downloadQueueTempathDict = {}

    self.progressLabels = []
    self.downloadProgressBars = []
    self.downloadProgressBarWidgets = []

    self.progress = qt.QProgressDialog(self.browserWidget)
    self.progress.setWindowTitle("TCIA Browser")
    # setup API key
    self.slicerApiKey = '2a38f167-95f1-4f03-99c1-0bc45472d64a'
    self.currentAPIKey = self.slicerApiKey
    self.tciaBrowserModuleDirectoryPath = slicer.modules.tciabrowser.path.replace("TCIABrowser.py","")
    item = qt.QStandardItem()

    dicomAppWidget = ctk.ctkDICOMAppWidget()
    databaseDirectory = dicomAppWidget.databaseDirectory
    self.storagePath = databaseDirectory + "/TCIA-Temp/"
    self.cachePath = self.storagePath + "/TCIA-Cache/"
    if not os.path.exists(self.cachePath):
      os.makedirs(self.cachePath)
    self.useCacheFlag = True  
    
    # setup the TCIA client
  
  def enter(self):
    if self.showBrowserButton != None and self.showBrowserButton.enabled == True:
      self.showBrowser()

  def exit(self):
    print 'exit'
    #self.browserWidget.hide()

  def setup(self):
    # Instantiate and connect widgets ...

    self.reportIcon = qt.QIcon(self.tciaBrowserModuleDirectoryPath+'/Resources/Icons/report.png')
    self.downloadAndIndexIcon = qt.QIcon(self.tciaBrowserModuleDirectoryPath+'/Resources/Icons/downloadAndIndex.png')
    self.downloadAndLoadIcon = qt.QIcon(self.tciaBrowserModuleDirectoryPath+'/Resources/Icons/downloadAndLoad.png')
    self.browserIcon = qt.QIcon(self.tciaBrowserModuleDirectoryPath+'/Resources/Icons/TCIABrowser.png')
    self.browserWidget.setWindowIcon(self.browserIcon)
    #
    # Reload and Test area
    #
    reloadCollapsibleButton = ctk.ctkCollapsibleButton()
    reloadCollapsibleButton.text = "Reload && Test"
    # uncomment the next line for developing and testing
    self.layout.addWidget(reloadCollapsibleButton)
    reloadFormLayout = qt.QFormLayout(reloadCollapsibleButton)

    # reload button
    # (use this during development, but remove it when delivering
    #  your module to users)
    self.reloadButton = qt.QPushButton("Reload")
    self.reloadButton.toolTip = "Reload this module."
    self.reloadButton.name = "TCIABrowser Reload"
    reloadFormLayout.addWidget(self.reloadButton)
    self.reloadButton.connect('clicked()', self.onReload)

    # reload and test button
    # (use this during development, but remove it when delivering
    #  your module to users)
    self.reloadAndTestButton = qt.QPushButton("Reload and Test")
    self.reloadAndTestButton.toolTip = "Reload this module and then run the self tests."
    reloadFormLayout.addWidget(self.reloadAndTestButton)
    self.reloadAndTestButton.connect('clicked()', self.onReloadAndTest)

    #
    # Browser Area
    #
    browserCollapsibleButton = ctk.ctkCollapsibleButton()
    browserCollapsibleButton.text = "TCIA Browser"
    self.layout.addWidget(browserCollapsibleButton)
    browserLayout = qt.QVBoxLayout(browserCollapsibleButton)

    #
    # Connection Area
    #
    connectWidget = qt.QWidget()
    connectGridLayout = qt.QHBoxLayout(connectWidget)
    browserLayout.addWidget(connectWidget)
    # Add remove button
    self.addRemoveApisButton = qt.QPushButton("+")
    self.addRemoveApisButton.toolTip = "Add or Remove APIs"
    self.addRemoveApisButton.enabled = True
    self.addRemoveApisButton.setMaximumWidth(20)
    connectGridLayout.addWidget(self.addRemoveApisButton)
    # API selection combo box
    self.apiSelectionComboBox = qt.QComboBox()
    self.apiSelectionComboBox.addItem('Slicer API')
    connectGridLayout.addWidget(self.apiSelectionComboBox)
    settings = qt.QSettings()
    settings.beginGroup("TCIABrowser/API-Keys")
    self.userApiNames = settings.childKeys()
    for api in self.userApiNames:
      self.apiSelectionComboBox.addItem(api)
    settings.endGroup()

    self.connectButton = qt.QPushButton("Connect")
    self.connectButton.toolTip = "Connect to TCIA Server."
    self.connectButton.enabled = True
    connectGridLayout.addWidget(self.connectButton)
    
    self.popupGeometry = qt.QRect()
    settings = qt.QSettings()
    mainWindow = slicer.util.mainWindow()
    width = mainWindow.width* 3/4 
    height = mainWindow.height* 3/4 
    self.popupGeometry.setWidth(width)
    self.popupGeometry.setHeight(height)
    self.popupPositioned = False

    self.browserWidget.setGeometry(self.popupGeometry)

    #
    # Show Browser Button
    #
    self.showBrowserButton = qt.QPushButton("Show Browser")
    # self.showBrowserButton.toolTip = "."
    self.showBrowserButton.enabled = False 
    browserLayout.addWidget(self.showBrowserButton)

    # Browser Widget Layout within the collapsible button
    browserWidgetLayout = qt.QVBoxLayout(self.browserWidget)
    # browserWidgetLayout = self.browserWidget.layout
    #
    
    collectionsCollapsibleGroupBox = ctk.ctkCollapsibleGroupBox()
    collectionsCollapsibleGroupBox.setTitle('Collections')
    browserWidgetLayout.addWidget(collectionsCollapsibleGroupBox)  # 
    collectionsFormLayout = qt.QHBoxLayout(collectionsCollapsibleGroupBox)
    

    #
    # Collection Selector ComboBox
    #
    self.collectionSelectorLabel = qt.QLabel('Current Collection:')
    collectionsFormLayout.addWidget(self.collectionSelectorLabel)
    # Selector ComboBox
    self.collectionSelector = qt.QComboBox()
    self.collectionSelector.setMinimumWidth(200)
    collectionsFormLayout.addWidget( self.collectionSelector)
    ##
    # Use Cache CheckBox
    #
    collectionsFormLayout.addStretch(4)
    self.useCacheCeckBox= qt.QCheckBox("Use Cache")
    self.useCacheCeckBox.toolTip = "If checked the browser will use previous cached queries (saved on disk) else it will request new queries from the server and updates cache."
    collectionsFormLayout.addWidget(self.useCacheCeckBox)
    self.useCacheCeckBox.setCheckState(True)
    self.useCacheCeckBox.setTristate(False)
    '''
    self.infoPushButton = qt.QPushButton("?")
    collectionsFormLayout.addRow(self.infoPushButton,self.collectionSelector)
    self.infoPushButton.setMaximumWidth(25)
    '''
    #
    # Patient Table Widget 
    #
    self.patientsCollapsibleGroupBox = ctk.ctkCollapsibleGroupBox()
    self.patientsCollapsibleGroupBox.setTitle('Patients')
    browserWidgetLayout.addWidget(self.patientsCollapsibleGroupBox)
    patientsVBoxLayout1 = qt.QVBoxLayout(self.patientsCollapsibleGroupBox)
    patientsExpdableArea = ctk.ctkExpandableWidget()
    patientsVBoxLayout1.addWidget(patientsExpdableArea)
    patientsVBoxLayout2 = qt.QVBoxLayout(patientsExpdableArea)
    #patientsVerticalLayout = qt.QVBoxLayout(patientsExpdableArea)
    self.patientsTableWidget = qt.QTableWidget()
    self.patientsModel = qt.QStandardItemModel()
    self.patientsTableWidgetHeaderLabels = ['Patient ID','Patient Name','Patient BirthDate',
        'Patient Sex','Ethnic Group','Clinical Data']
    self.patientsTableWidget.setColumnCount(6)
    self.patientsTableWidget.setHorizontalHeaderLabels(self.patientsTableWidgetHeaderLabels)
    patientsTableWidgetHeader = self.patientsTableWidget.horizontalHeader()
    patientsTableWidgetHeader.setStretchLastSection(True)
    # patientsTableWidgetHeader.setResizeMode(qt.QHeaderView.Stretch)
    patientsVBoxLayout2.addWidget(self.patientsTableWidget)
    self.patientsTreeSelectionModel = self.patientsTableWidget.selectionModel()
    abstractItemView =qt.QAbstractItemView()
    self.patientsTableWidget.setSelectionBehavior(abstractItemView.SelectRows) 
    verticalheader = self.patientsTableWidget.verticalHeader()
    verticalheader.setDefaultSectionSize(20)

    # 
    # Studies Table Widget 
    #
    self.studiesCollapsibleGroupBox = ctk.ctkCollapsibleGroupBox()
    self.studiesCollapsibleGroupBox.setTitle('Studies')
    browserWidgetLayout.addWidget(self.studiesCollapsibleGroupBox) 
    studiesVBoxLayout1 = qt.QVBoxLayout(self.studiesCollapsibleGroupBox)
    studiesExpdableArea = ctk.ctkExpandableWidget()
    studiesVBoxLayout1.addWidget(studiesExpdableArea)
    studiesVBoxLayout2 = qt.QVBoxLayout(studiesExpdableArea)
    self.studiesTableWidget = qt.QTableWidget()
    self.studiesModel = qt.QStandardItemModel()
    self.studiesTableHeaderLabels = ['Study Instance UID','Study Date','Study Description',
        'Admitting Diagnosis Descrition','Study ID','Patient Age','Series Count']
    self.studiesTableWidget.setColumnCount(7)
    self.studiesTableWidget.setHorizontalHeaderLabels(self.studiesTableHeaderLabels)
    self.studiesTableWidget.resizeColumnsToContents()
    studiesVBoxLayout2.addWidget(self.studiesTableWidget)
    self.studiesTreeSelectionModel = self.studiesTableWidget.selectionModel()
    self.studiesTableWidget.setSelectionBehavior(abstractItemView.SelectRows) 
    studiesVerticalheader = self.studiesTableWidget.verticalHeader()
    studiesVerticalheader.setDefaultSectionSize(20)
    studiesTableWidgetHeader = self.studiesTableWidget.horizontalHeader()
    studiesTableWidgetHeader.setStretchLastSection(True)
    # studiesTableWidgetHeader.setResizeMode(qt.QHeaderView.Stretch)

    #
    # Series Table Widget 
    #
    self.seriesCollapsibleGroupBox = ctk.ctkCollapsibleGroupBox()
    self.seriesCollapsibleGroupBox.setTitle('Series')
    browserWidgetLayout.addWidget(self.seriesCollapsibleGroupBox)  # 
    seriesVBoxLayout1 = qt.QVBoxLayout(self.seriesCollapsibleGroupBox)
    seriesExpdableArea = ctk.ctkExpandableWidget()
    seriesVBoxLayout1.addWidget(seriesExpdableArea)
    seriesVBoxLayout2 = qt.QVBoxLayout(seriesExpdableArea)
    self.seriesTableWidget = qt.QTableWidget()
    #self.seriesModel = qt.QStandardItemModel()
    self.seriesTableWidget.setColumnCount(12)
    self.seriesTableHeaderLabels = ['Series Instance UID','Modality','Protocol Name','Series Date'
        ,'Series Description','Body Part Examined','Series Number','Annotation Flag','Manufacturer'
        ,'Manufacturer Model Name','Software Versions','Image Count']
    self.seriesTableWidget.setHorizontalHeaderLabels(self.seriesTableHeaderLabels)
    self.seriesTableWidget.resizeColumnsToContents()
    seriesVBoxLayout2.addWidget(self.seriesTableWidget)
    self.seriesTreeSelectionModel = self.studiesTableWidget.selectionModel()
    self.seriesTableWidget.setSelectionBehavior(abstractItemView.SelectRows) 
    self.seriesTableWidget.setSelectionMode(3) 
    seriesTableWidgetHeader = self.seriesTableWidget.horizontalHeader()
    seriesTableWidgetHeader.setStretchLastSection(True)
    #seriesTableWidgetHeader.setResizeMode(qt.QHeaderView.Stretch)
    seriesVerticalheader = self.seriesTableWidget.verticalHeader()
    seriesVerticalheader.setDefaultSectionSize(20)

    selectOptionsWidget = qt.QWidget()
    selectOptionsLayout = qt.QHBoxLayout(selectOptionsWidget)
    seriesVBoxLayout2.addWidget(selectOptionsWidget)
    selectLabel = qt.QLabel('Select:')
    selectOptionsLayout.addWidget(selectLabel)
    self.selectAllButton = qt.QPushButton('All')
    self.selectAllButton.enabled = False
    self.selectAllButton.setMaximumWidth(50)
    selectOptionsLayout.addWidget(self.selectAllButton)
    self.selectNoneButton = qt.QPushButton('None')
    self.selectNoneButton.enabled = False
    self.selectNoneButton.setMaximumWidth(50)
    selectOptionsLayout.addWidget(self.selectNoneButton)
    selectOptionsLayout.addStretch(1)

    downloadButtonsWidget = qt.QWidget()
    downloadWidgetLayout = qt.QHBoxLayout(downloadButtonsWidget)
    browserWidgetLayout.addWidget(downloadButtonsWidget)
    
    # Index Button
    #
    self.indexButton = qt.QPushButton()
    self.indexButton.setMinimumWidth(50)
    self.indexButton.toolTip = "Download and Index: The browser will download the selected sereies and index them in 3D Slicer DICOM Database."
    self.indexButton.setIcon(self.downloadAndIndexIcon)
    iconSize = qt.QSize(50,50)
    self.indexButton.setIconSize(iconSize)
    self.indexButton.setMinimumHeight(50)
    self.indexButton.enabled = False 
    downloadWidgetLayout.addStretch(4)
    downloadWidgetLayout.addWidget(self.indexButton)

    downloadWidgetLayout.addStretch(1)
    #
    # Load Button
    #
    self.loadButton = qt.QPushButton("")
    self.loadButton.setMinimumWidth(50)
    self.loadButton.setIcon(self.downloadAndLoadIcon)
    self.loadButton.setIconSize(iconSize)
    self.loadButton.setMinimumHeight(50)
    self.loadButton.toolTip = "Download and Load: The browser will download the selected sereies and Load them in 3D Slicer scene."
    self.loadButton.enabled = False 
    downloadWidgetLayout.addWidget(self.loadButton)
    downloadWidgetLayout.addStretch(4)

    #
    # context menu
    #
    self.patientsTableWidget.setContextMenuPolicy(2)
    self.clinicalDataRetrieveAction = qt.QAction("Get Clincal Data", self.patientsTableWidget)
    self.patientsTableWidget.addAction(self.clinicalDataRetrieveAction)
    #self.contextMenu = qt.QMenu(self.patientsTableWidget)
    #self.contextMenu.addAction(self.clinicalDataRetrieveAction)
    self.clinicalDataRetrieveAction.enabled = False 

    #
    # Settings Area
    #
    settingsCollapsibleButton = ctk.ctkCollapsibleButton()
    settingsCollapsibleButton.text = "Settings"
    self.layout.addWidget(settingsCollapsibleButton)
    settingsFormLayout = qt.QFormLayout(settingsCollapsibleButton)
#
    # Storage Path button
    #
    #storageWidget = qt.QWidget()
    #storageFormLayout = qt.QFormLayout(storageWidget)
    #settingsVBoxLayout.addWidget(storageWidget)
    self.storagePathButton = ctk.ctkDirectoryButton()
    self.storagePathButton.directory = self.storagePath

    settingsFormLayout.addRow("Storage Directory: ", self.storagePathButton)
    
    self.apiSettingsPopup = TCIABrowserLib.APISettingsPopup()
    self.clinicalPopup = TCIABrowserLib.clinicalDataPopup(self.cachePath,self.reportIcon)

    #
    # Download Status Area
    #
    downloadStatusCollapsibleButton = ctk.ctkCollapsibleButton()
    downloadStatusCollapsibleButton.text = "Download Status"
    self.layout.addWidget(downloadStatusCollapsibleButton)
    downloadVBoxLayout = qt.QVBoxLayout(downloadStatusCollapsibleButton)
    #
    downloadStatusExpdableArea = ctk.ctkExpandableWidget()
    downloadVBoxLayout.addWidget(downloadStatusExpdableArea)
    self.downloadFormLayout = qt.QFormLayout(downloadStatusExpdableArea)
    self.layout.addStretch(1)
    
    # connections
    self.showBrowserButton.connect('clicked(bool)', self.onShowBrowserButton)
    self.addRemoveApisButton.connect('clicked(bool)', self.apiSettingsPopup.open)
    self.apiSelectionComboBox.connect('currentIndexChanged(QString)',self.apiKeySelected)
    self.collectionSelector.connect('currentIndexChanged(QString)',self.collectionSelected)
    self.patientsTableWidget.connect('cellClicked(int,int)',self.patientSelected)
    self.studiesTableWidget.connect('cellClicked(int,int)',self.studySelected)
    self.seriesTableWidget.connect('cellClicked(int,int)',self.seriesSelected)
    self.connectButton.connect('clicked(bool)', self.onConnectButton)
    self.useCacheCeckBox.connect('stateChanged(int)', self.onUseCacheStateChanged)
    self.indexButton.connect('clicked(bool)', self.onIndexButton)
    self.loadButton.connect('clicked(bool)', self.onLoadButton)
    self.storagePathButton.connect('directoryChanged(const QString &)',self.onStoragePathButton)
    self.clinicalDataRetrieveAction.connect('triggered()', self.onContextMenuTriggered)
    self.clinicalDataRetrieveAction.connect('triggered()', self.clinicalPopup.open)
    self.selectAllButton.connect('clicked(bool)', self.onSelectAllButton)
    self.selectNoneButton.connect('clicked(bool)', self.onSelectNoneButton)

    # Add vertical spacer
    self.layout.addStretch(1)

  def cleanup(self):
    pass

  def apiKeySelected(self):
    settings = qt.QSettings()
    settings.beginGroup("TCIABrowser/API-Keys")
    
    self.connectButton.enabled = True
    if self.apiSelectionComboBox.currentText == 'Slicer API':
      self.currentAPIKey = self.slicerApiKey 
    else:
      self.currentAPIKey = settings.value(self.apiSelectionComboBox.currentText)

  def onShowBrowserButton(self):
    self.showBrowser()

  def onUseCacheStateChanged(self,state):
    if state == 0:
      self.useCacheFlag = False
    elif state ==2:
      self.useCacheFlag= True

  def onContextMenuTriggered(self):
    self.clinicalPopup.getData(self.selectedCollection,self.selectedPatient)

  def showBrowser(self):

    if not self.browserWidget.isVisible():
      self.popupPositioned = False
      self.browserWidget.show()
      if self.popupGeometry.isValid():
        self.browserWidget.setGeometry(self.popupGeometry)
    self.browserWidget.raise_() 

    if not self.popupPositioned:
      mainWindow = slicer.util.mainWindow()
      screenMainPos = mainWindow.pos
      x = screenMainPos.x() + 100
      y = screenMainPos.y() + 100
      self.browserWidget.move(qt.QPoint(x,y))
      self.popupPositioned = True

  def showProgress(self, message):
    self.progress.minimumDuration = 0
    self.progress.setValue(0)
    self.progress.setMaximum(0)
    self.progress.setCancelButton(0)
    self.progress.show()
    self.progress.setLabelText(message)
    slicer.app.processEvents()
    self.progress.repaint()

  def closeProgress(self):
    self.progress.close()
    self.progress.reset()
    #self.showBrowser()

  def onStoragePathButton(self):
    self.storagePath = self.storagePathButton.directory

  def onConnectButton(self):
    self.connectButton.enabled = False 
    logic = TCIABrowserLogic()
    # Instantiate TCIAClient object
    self.tcia_client = TCIABrowserLib.TCIAClient(self.currentAPIKey, baseUrl = 
        "https://services.cancerimagingarchive.net/services/TCIA/TCIA/query")  # Set the API-Key
    self.showProgress("Getting Available Collections")
    try:    
      response = self.tcia_client.get_collection_values()
      responseString = response.read()[:]
      self.populateCollectionsTreeView(responseString)
      self.closeProgress()

    except Exception, error:
      self.closeProgress()
      message = "Error in getting response from TCIA server.\nHTTP Error:\n"+ str(error)
      qt.QMessageBox.critical(slicer.util.mainWindow(),
                        'TCIA Browser', message, qt.QMessageBox.Ok)
    self.showBrowserButton.enabled = True
    self.showBrowser()

  def onSelectAllButton(self):
    self.seriesTableWidget.selectAll()
    '''
    for n in range(len(self.seriesInstanceUIDs)):
      self.seriesInstanceUIDs[n].setSelected(True)
    '''

  def onSelectNoneButton(self):
    self.seriesTableWidget.clearSelection()
    '''
    for n in range(len(self.seriesInstanceUIDs)):
      self.seriesInstanceUIDs[n].setSelected(False)
    '''
   
  def collectionSelected(self,item):
    self.loadButton.enabled = False
    self.indexButton.enabled = False
    self.clearPatientsTableWidget()
    self.clearStudiesTableWidget()
    self.clearSeriesTableWidget()
    self.selectedCollection = item
    cacheFile = self.cachePath+self.selectedCollection+'.json'
    self.progressMessage = "Getting available patients for collection: " + self.selectedCollection
    self.showProgress(self.progressMessage)
    if self.selectedCollection[0:4] != 'TCGA':
      self.clinicalDataRetrieveAction.enabled = False 
    else:
      self.clinicalDataRetrieveAction.enabled = True

    if os.path.isfile(cacheFile) and self.useCacheFlag:
      f = open(cacheFile,'r')
      responseString = f.read()[:]
      f.close()
      self.populatePatientsTableWidget(responseString)
      self.closeProgress()
      groupBoxTitle = 'Patients (Accessed: '+ time.ctime(os.path.getmtime(cacheFile))+')'
      self.patientsCollapsibleGroupBox.setTitle(groupBoxTitle)

    else:
      try:    
        response = self.tcia_client.get_patient(collection = self.selectedCollection)
        '''
        responseString = response.read()[:]
        with open(cacheFile, 'w') as outputFile:
          outputFile.write(responseString)
          outputFile.close()
        '''
        with open(cacheFile, 'w') as outputFile:
          self.stringBufferRead(outputFile, response)
        outputFile.close()
        f = open(cacheFile,'r')
        responseString = f.read()[:]
        self.populatePatientsTableWidget(responseString)
        groupBoxTitle = 'Patients (Accessed: '+ time.ctime(os.path.getmtime(cacheFile))+')'
        self.patientsCollapsibleGroupBox.setTitle(groupBoxTitle)
        self.closeProgress()
    
      except Exception, error:
        self.closeProgress()
        message = "Error in getting response from TCIA server.\nHTTP Error:\n"+ str(error)
        qt.QMessageBox.critical(slicer.util.mainWindow(),
                        'TCIA Browser', message, qt.QMessageBox.Ok)

  def patientSelected(self,row,column):
    self.loadButton.enabled = False
    self.indexButton.enabled = False
    self.clearStudiesTableWidget()
    self.clearSeriesTableWidget()
    self.selectedPatient = self.patientsIDs[row].text()
    cacheFile = self.cachePath+self.selectedPatient+'.json'
    self.progressMessage = "Getting available studies for patient ID: " + self.selectedPatient
    self.showProgress(self.progressMessage)
    if os.path.isfile(cacheFile) and self.useCacheFlag:
      f = open(cacheFile,'r')
      responseString = f.read()[:]
      f.close()
      self.populateStudiesTableWidget(responseString)
      self.closeProgress()
      groupBoxTitle = 'Studies (Accessed: '+ time.ctime(os.path.getmtime(cacheFile))+')'
      self.studiesCollapsibleGroupBox.setTitle(groupBoxTitle)

    else:
      try:    
        response = self.tcia_client.get_patient_study(patientId = self.selectedPatient)
        responseString = response.read()[:]
        with open(cacheFile, 'w') as outputFile:
          outputFile.write(responseString)
          outputFile.close()
        f = open(cacheFile,'r')
        responseString = f.read()[:]
        self.populateStudiesTableWidget(responseString)
        groupBoxTitle = 'Studies (Accessed: '+ time.ctime(os.path.getmtime(cacheFile))+')'
        self.studiesCollapsibleGroupBox.setTitle(groupBoxTitle) 
        self.closeProgress()
      
      except Exception, error:
        self.closeProgress()
        message = "Error in getting response from TCIA server.\nHTTP Error:\n"+ str(error)
        qt.QMessageBox.critical(slicer.util.mainWindow(),
                          'TCIA Browser', message, qt.QMessageBox.Ok)

  def studySelected(self,row,column):
    self.loadButton.enabled = False
    self.indexButton.enabled = False
    self.clearSeriesTableWidget()
    self.selectedStudy = self.studyInstanceUIDs[row].text()
    self.selectedStudyRow = row
    self.progressMessage = "Getting available series for studyInstanceUID: " + self.selectedStudy
    self.showProgress(self.progressMessage)
    cacheFile = self.cachePath+self.selectedStudy+'.json'
    if os.path.isfile(cacheFile) and self.useCacheFlag:
      f = open(cacheFile,'r')
      responseString = f.read()[:]
      f.close()
      self.populateSeriesTableWidget(responseString)
      self.closeProgress()
      groupBoxTitle = 'Series (Accessed: '+ time.ctime(os.path.getmtime(cacheFile))+')'
      self.seriesCollapsibleGroupBox.setTitle(groupBoxTitle)

    else:
      self.progressMessage = "Getting available series for studyInstanceUID: " + self.selectedStudy
      self.showProgress(self.progressMessage)
      try:    
        response = self.tcia_client.get_series(studyInstanceUID = self.selectedStudy)
        responseString = response.read()[:]
        with open(cacheFile, 'w') as outputFile:
          outputFile.write(responseString)
          outputFile.close()
        self.populateSeriesTableWidget(responseString)
        groupBoxTitle = 'Series (Accessed: '+ time.ctime(os.path.getmtime(cacheFile))+')'
        self.seriesCollapsibleGroupBox.setTitle(groupBoxTitle)
        self.closeProgress()
        
      except Exception, error:
        self.closeProgress()
        message = "Error in getting response from TCIA server.\nHTTP Error:\n"+ str(error)
        qt.QMessageBox.critical(slicer.util.mainWindow(),
                          'TCIA Browser', message, qt.QMessageBox.Ok)

  def seriesSelected(self,row,column):
    #self.selectedSeriesUIdForDownloadRow = row
    self.selectedSeriesImageCount = self.imageCounts[row].text()
    self.selectedSeriesUIdForDownload = self.seriesInstanceUIDs[row].text()
    self.selectedSereiesRow = row

  def onIndexButton(self):
    self.loadToScene = False
    self.addSelectedToDownloadQueue()
    #self.addFilesToDatabase()

  def onLoadButton(self):
    self.loadToScene = True
    self.addSelectedToDownloadQueue()
    #self.addFilesToDatabase()

  def addFilesToDatabase(self,seriesUID):
    self.progressMessage = "Adding Files to DICOM Database "
    self.showProgress(self.progressMessage)
    dicomWidget = slicer.modules.dicom.widgetRepresentation().self()
    
    indexer = ctk.ctkDICOMIndexer() 
    indexer.addDirectory(slicer.dicomDatabase, self.extractedFilesDirectory)
    indexer.waitForImportFinished()
    #seriesUID = self.selectedSeriesUIdForDownload
    seriesUID = seriesUID.replace("'","")
    self.dicomDatabase = slicer.dicomDatabase
    self.fileList = slicer.dicomDatabase.filesForSeries(seriesUID)
    originalDatabaseDirectory = os.path.split(slicer.dicomDatabase.databaseFilename)[0]
    # change database directory to update dicom browser tables
    dicomWidget.onDatabaseDirectoryChanged(self.extractedFilesDirectory)
    dicomWidget.onDatabaseDirectoryChanged(originalDatabaseDirectory)
    self.closeProgress()

  def addSelectedToDownloadQueue(self):
    for n in range(len(self.seriesInstanceUIDs)):
      #print self.seriesInstanceUIDs[n]
      if self.seriesInstanceUIDs[n].isSelected() == True:
        selectedCollection = self.selectedCollection
        selectedPatient = self.selectedPatient
        selectedStudy = self.selectedStudy
        selectedSeries =  self.seriesInstanceUIDs[n].text()
        # selectedSeries = self.selectedSeriesUIdForDownload
        self.selectedSereisNicknamesDic [selectedSeries] = str(selectedPatient)+'-' +str(self.selectedStudyRow+1)+'-'+str(n+1) 

        # get image request
        tempPath = self.storagePath  + "/" + str(selectedCollection) + "/" + str(selectedPatient) + "/" + str(selectedStudy)+ "/"
        # create download queue
        self.downloadQueueTempathDict  [selectedSeries] = tempPath

        # make progress bar
        self.makeDownloadProgressBar(selectedSeries)
        # run downloader

    self.seriesTableWidget.clearSelection()
    self.downloadSelectedSeries()

  def downloadSelectedSeries(self):

    while self.downloadQueueTempathDict:
      selectedSeries, tempPath = self.downloadQueueTempathDict.popitem()
      if not os.path.exists(tempPath):
        os.makedirs(tempPath)
      fileName = tempPath + str(selectedSeries) + ".zip"
      self.extractedFilesDirectory = tempPath + str(selectedSeries)
      self.progressMessage = "Downloading Images for series InstanceUID: " + selectedSeries
      #self.showProgress(self.progressMessage)
      try:
        response = self.tcia_client.get_image(seriesInstanceUid = selectedSeries );
        slicer.app.processEvents()
        # Save server response as images.zip in current directory
        if response.getcode() == 200:
          #print "\n" + str(response.info())
          #self.makeDownloadProgressBar(selectedSeries)
          destinationFile = open(fileName, "wb")
          self.__bufferRead(destinationFile, response, selectedSeries)
          
          destinationFile.close()
          # print "\nDownloaded file %s.zip from the TCIA server" %fileName
          self.closeProgress()

        else:
          print "Error : " + str(response.getcode) # print error code
          print "\n" + str(response.info())
      
      except Exception, error:
        self.closeProgress()
        message = "Error in getting response from TCIA server.\nHTTP Error:\n"+ str(error)
        qt.QMessageBox.critical(slicer.util.mainWindow(),
                          'TCIA Browser', message, qt.QMessageBox.Ok)

      self.progressMessage = "Extracting Images"
      # Unzip the data
      self.showProgress(self.progressMessage)
      self.unzip(fileName,self.extractedFilesDirectory)
      self.closeProgress()
      # Import the data into dicomAppWidget and open the dicom browser
      os.remove(fileName)
      self.addFilesToDatabase(selectedSeries)
      if self.loadToScene == True:
        self.progressMessage = "Examine Files to Load"
        self.showProgress(self.progressMessage)
        plugin = slicer.modules.dicomPlugins['DICOMScalarVolumePlugin']()
        loadables = plugin.examine([self.fileList])
        self.closeProgress()
        volume = plugin.load(loadables[0])

  def makeDownloadProgressBar(self, selectedSeries):
    #downloadProgressBarWidget = qt.QWidget()
    #self.downloadHBoxLayout = qt.QHBoxLayout(downloadProgressBarWidget)
    #self.downloadVBoxLayout.addWidget(downloadProgressBarWidget)
    #self.downloadProgressBarWidgets.append(downloadProgressBarWidget)
    self.downloadProgressBar = qt.QProgressBar()
    self.downloadProgressBarDict [selectedSeries] = self.downloadProgressBarCounts
    #self.downloadProgressBar.setMinimumWidth(250)
    titleLabel = qt.QLabel(selectedSeries)
    #self.downloadHBoxLayout.addWidget(titleLabel)
    #self.downloadHBoxLayout.addWidget(self.downloadProgressBar)
    self.downloadProgressBars.append(self.downloadProgressBar)
    self.progressLabel = qt.QLabel(self.selectedSereisNicknamesDic[selectedSeries]+' (0 KB)')
    self.progressLabels.append(self.progressLabel)
    #self.downloadHBoxLayout.addWidget(self.progressLabel)
    #self.downloadHBoxLayout.addStretch(1)
    self.downloadFormLayout.addRow(self.progressLabel,self.downloadProgressBar)
    '''
    # show in folder
    showInFolderPushButton = qt.QPushButton('Show in folder')
    showInFolderPushButton.setFlat(True)
    # remove from list
    removeFromListPushButton = qt.QPushButton('Remove from list')
    removeFromListPushButton.setFlat(True) 
    self.downloadFormLayout.addRow(showInFolderPushButton,removeFromListPushButton)
    '''

    self.downloadProgressBarCounts += 1
    
  def stringBufferRead(self, dstFile, response, bufferSize=819):
    self.downloadSize = 0
    while 1:     

      #
      # If DOWNLOAD FINISHED
      #
      buffer = response.read(bufferSize)[:]
      slicer.app.processEvents()
      if not buffer: 
        # Pop from the queue
        break
      #
      # Otherwise, Write buffer chunk to file
      #
      slicer.app.processEvents()
      dstFile.write(buffer)
      #
      # And update progress indicators
      #
      self.downloadSize += len(buffer)
      #print self.downloadSize


  def __bufferRead(self, dstFile, response, selectedSeries, bufferSize=8192):

    currentDownloadProgressBar = self.downloadProgressBars[self.downloadProgressBarDict[selectedSeries]]
    currentProgressLabel = self.progressLabels[self.downloadProgressBarDict[selectedSeries]]
    #--------------------
    # Define the buffer read loop
    #--------------------
    self.downloadSize = 0
    while 1:     
      '''
        #
        # If DOWNLOAD CANCELLED
        #              
        if not self.inDownloadQueue(_src):
            print "Cancelling download of '%s'"%(_src)
            dstFile.close()
            os.remove(dstFile.name)
            self.runEventCallbacks('downloadCancelled', _src)
            break
      '''

      #
      # If DOWNLOAD FINISHED
      #
      buffer = response.read(bufferSize)
      slicer.app.processEvents()
      if not buffer: 
        # Pop from the queue
        currentDownloadProgressBar .setMaximum(100)
        currentDownloadProgressBar .setValue(100)
        currentDownloadProgressBar.setVisible(False)
        currentProgressLabel.setVisible(False)

        self.downloadQueueTempathDict.pop(selectedSeries, None)
        break
      #
      # Otherwise, Write buffer chunk to file
      #
      slicer.app.processEvents()
      dstFile.write(buffer)
      #
      # And update progress indicators
      #
      self.downloadSize += len(buffer)
      currentDownloadProgressBar .setValue(0)
      currentDownloadProgressBar .setValue(0)
      currentDownloadProgressBar .setMaximum(0)
      currentProgressLabel.text = self.selectedSereisNicknamesDic[selectedSeries]+' ('+str(int(self.downloadSize/1024)) + " KB)"
      #print self.downloadSize

    return self.downloadSize

  def unzip(self,sourceFilename, destinationDir):
    with zipfile.ZipFile(sourceFilename) as zf:
      for member in zf.infolist():
        words = member.filename.split('/')
        path = destinationDir 
        for word in words[:-1]:
          drive, word = os.path.splitdrive(word)
          head, word = os.path.split(word)
          if word in (os.curdir, os.pardir, ''): continue
          path = os.path.join(path, word)
        zf.extract(member, path)

  def populateCollectionsTreeView(self,responseString):
    collections = json.loads(responseString)
    # populate collection selector
    n = 0
    self.collectionSelector.disconnect('currentIndexChanged(QString)')
    self.collectionSelector.clear()
    self.collectionSelector.connect('currentIndexChanged(QString)',self.collectionSelected)
    for collection in collections:
      collectionText = str(collections[n]['Collection'])
      self.collectionSelector.addItem(collectionText)
      n += 1

  def populatePatientsTableWidget(self,responseString):
    self.clearPatientsTableWidget()
    table = self.patientsTableWidget
    patients = json.loads(responseString)
    table.setRowCount(len(patients))
    n = 0
    for patient in patients:
      keys = patient.keys()
      for key in keys:
        if key == 'PatientID':
          patientIDString = str(patient['PatientID'])
          patientID = qt.QTableWidgetItem(patientIDString)
          self.patientsIDs.append(patientID)
          table.setItem(n,0,patientID)
          if patientIDString[0:4] == 'TCGA':
            patientID.setIcon(self.reportIcon)
        if key == 'PatientName':
          patientName = qt.QTableWidgetItem(str(patient['PatientName']))
          self.patientNames.append(patientName)
          table.setItem(n,1,patientName )
        if key == 'PatientBirthDate':
          patientBirthDate= qt.QTableWidgetItem(str(patient['PatientBirthDate']))
          self.patientBirthDates.append(patientBirthDate)
          table.setItem(n,2,patientBirthDate)
        if key == 'PatientSex':
          patientSex = qt.QTableWidgetItem(str(patient['PatientSex']))
          self.patientSexes.append(patientSex)
          table.setItem(n,3,patientSex)
        if key == 'EthnicGroup':
          ethnicGroup= qt.QTableWidgetItem(str(patient['EthnicGroup']))
          self.ethnicGroups.append(ethnicGroup)
          table.setItem(n,4,ethnicGroup)
      n += 1
    self.patientsTableWidget.resizeColumnsToContents()

  def populateStudiesTableWidget(self,responseString):
    self.clearStudiesTableWidget()
    table = self.studiesTableWidget
    studies = json.loads(responseString)
    table.setRowCount(len(studies))
    n = 0
    for study in studies:
      keys = study.keys()
      for key in keys:
        if key == 'StudyInstanceUID':
          studyInstanceUID= qt.QTableWidgetItem(str(study['StudyInstanceUID']))
          self.studyInstanceUIDs.append(studyInstanceUID)
          table.setItem(n,0,studyInstanceUID)
        if key == 'StudyDate':
          studyDate = qt.QTableWidgetItem(str(study['StudyDate']))
          self.studyDates.append(studyDate)
          table.setItem(n,1,studyDate)
        if key == 'StudyDescription':
          studyDescription = qt.QTableWidgetItem(str(study['StudyDescription']))
          self.studyDescriptions.append(studyDescription)
          table.setItem(n,2,studyDescription)
        if key == 'AdmittingDiagnosesDescriptions':
          admittingDiagnosesDescription= qt.QTableWidgetItem(str(study['AdmittingDiagnosesDescriptions']))
          self.admittingDiagnosesDescriptions.append(admittingDiagnosesDescription)
          table.setItem(n,3,admittingDiagnosesDescription)
        if key == 'StudyID':
          studyID= qt.QTableWidgetItem(str(study['StudyID']))
          self.studyIDs.append(studyID)
          table.setItem(n,4,studyID)
        if key == 'PatientAge':
          patientAge = qt.QTableWidgetItem(str(study['PatientAge']))
          self.patientAges.append(patientAge)
          table.setItem(n,5,patientAge)
        if key == 'SeriesCount':
          seriesCount = qt.QTableWidgetItem(str(study['SeriesCount']))
          self.seriesCounts.append(seriesCount)
          table.setItem(n,6,seriesCount)
      n += 1
    self.studiesTableWidget.resizeColumnsToContents()

  def populateSeriesTableWidget(self,responseString):
    self.clearSeriesTableWidget()
    table = self.seriesTableWidget
    seriesCollection = json.loads(responseString)
    table.setRowCount(len(seriesCollection))
    self.selectAllButton.enabled = True 
    self.selectNoneButton.enabled = True 
    self.loadButton.enabled = True
    self.indexButton.enabled = True
  
    n = 0
    for series in seriesCollection:
      keys = series.keys()
      for key in keys:
        if key == 'SeriesInstanceUID':
          seriesInstanceUID = qt.QTableWidgetItem(str(series['SeriesInstanceUID']))
          self.seriesInstanceUIDs.append(seriesInstanceUID)
          table.setItem(n,0,seriesInstanceUID)
        if key == 'Modality':
          modality = qt.QTableWidgetItem(str(series['Modality']))
          self.modalities.append(modality)
          table.setItem(n,1,modality)
        if key == 'ProtocolName':
          protocolName = qt.QTableWidgetItem(str(series['ProtocolName']))
          self.protocolNames.append(protocolName)
          table.setItem(n,2,protocolName)
        if key == 'SeriesDate':
          seriesDate = qt.QTableWidgetItem(str(series['SeriesDate']))
          self.seriesDates.append(seriesDate)
          table.setItem(n,3,seriesDate)
        if key == 'SeriesDescription':
          seriesDescription = qt.QTableWidgetItem(str(series['SeriesDescription']))
          self.seriesDescriptions.append(seriesDescription)
          table.setItem(n,4,seriesDescription)
        if key == 'BodyPartExamined':
          bodyPartExamined = qt.QTableWidgetItem(str(series['BodyPartExamined']))
          self.bodyPartsExamined.append(bodyPartExamined)
          table.setItem(n,5,bodyPartExamined)
        if key == 'SeriesNumber':
          seriesNumber = qt.QTableWidgetItem(str(series['SeriesNumber']))
          self.seriesNumbers.append(seriesNumber)
          table.setItem(n,6,seriesNumber)
        if key == 'AnnotationsFlag':
          annotationsFlag = qt.QTableWidgetItem(str(series['AnnotationsFlag']))
          self.annotationsFlags.append(annotationsFlag)
          table.setItem(n,7,annotationsFlag)
        if key == 'Manufacturer':
          manufacturer = qt.QTableWidgetItem(str(series['Manufacturer']))
          self.manufacturers.append(manufacturer)
          table.setItem(n,8,manufacturer)
        if key == 'ManufacturerModelName':
          manufacturerModelName = qt.QTableWidgetItem(str(series['ManufacturerModelName']))
          self.manufacturerModelNames.append(manufacturerModelName )
          table.setItem(n,9,manufacturerModelName)
        if key == 'SoftwareVersions':
          softwareVersions = qt.QTableWidgetItem(str(series['SoftwareVersions']))
          self.softwareVersionsCollection.append(softwareVersions )
          table.setItem(n,10,softwareVersions)
        if key == 'ImageCount':
          imageCount = qt.QTableWidgetItem(str(series['ImageCount']))
          self.imageCounts.append(imageCount )
          table.setItem(n,11,imageCount )
      n += 1
    self.seriesTableWidget.resizeColumnsToContents()

  def clearPatientsTableWidget(self):
    table = self.patientsTableWidget
    self.patientsCollapsibleGroupBox.setTitle('Patients')
    self.patientsIDs =[]
    self.patientNames = []
    self.patientBirthDates = []
    self.patientSexes = []
    self.ethnicGroups = []
    #self.collections = []
    table.clear()
    table.setHorizontalHeaderLabels(self.patientsTableWidgetHeaderLabels)
    
  def clearStudiesTableWidget(self):
    table = self.studiesTableWidget
    self.studiesCollapsibleGroupBox.setTitle('Studies')
    self.studyInstanceUIDs =[]
    self.studyDates = []
    self.studyDescriptions = []
    self.admittingDiagnosesDescriptions = []
    self.studyIDs = []
    self.patientAges = []
    self.seriesCounts = []
    table.clear()
    table.setHorizontalHeaderLabels(self.studiesTableHeaderLabels)
   
  def clearSeriesTableWidget(self):
    table = self.seriesTableWidget
    self.seriesCollapsibleGroupBox.setTitle('Series')
    self.seriesInstanceUIDs= []
    self.modalities = []
    self.protocolNames = []
    self.seriesDates = []
    self.seriesDescriptions = []
    self.bodyPartsExamined = []
    self.seriesNumbers =[]
    self.annotationsFlags = []
    self.manufacturers = []
    self.manufacturerModelNames = []
    self.softwareVersionsCollection = []
    self.imageCounts = []
    #self.collections = []
    table.clear()
    table.setHorizontalHeaderLabels(self.seriesTableHeaderLabels)
    
  def onReload(self,moduleName="TCIABrowser"):
    """Generic reload method for any scripted module.
    ModuleWizard will subsitute correct default moduleName.
    """
    import imp, sys, os, slicer
    import time
    import urllib2, urllib,sys, os
    import xml.etree.ElementTree as ET
    import webbrowser
    import string, json
    import csv
    import zipfile, os.path

    widgetName = moduleName + "Widget"

    # reload the source code
    # - set source file path
    # - load the module to the global space
    filePath = eval('slicer.modules.%s.path' % moduleName.lower())
    p = os.path.dirname(filePath)
    if not sys.path.__contains__(p):
      sys.path.insert(0,p)
    fp = open(filePath, "r")
    globals()[moduleName] = imp.load_module(
        moduleName, fp, filePath, ('.py', 'r', imp.PY_SOURCE))
    fp.close()

    # rebuild the widget
    # - find and hide the existing widget
    # - create a new widget in the existing parent
    parent = slicer.util.findChildren(name='%s Reload' % moduleName)[0].parent().parent()
    for child in parent.children():
      try:
        child.hide()
      except AttributeError:
        pass
    # Remove spacer items
    item = parent.layout().itemAt(0)
    while item:
      parent.layout().removeItem(item)
      item = parent.layout().itemAt(0)

    # delete the old widget instance
    if hasattr(globals()['slicer'].modules, widgetName):
      getattr(globals()['slicer'].modules, widgetName).cleanup()

    # create new widget inside existing parent
    globals()[widgetName.lower()] = eval(
        'globals()["%s"].%s(parent)' % (moduleName, widgetName))
    globals()[widgetName.lower()].setup()
    setattr(globals()['slicer'].modules, widgetName, globals()[widgetName.lower()])

  def onReloadAndTest(self,moduleName="TCIABrowser"):
    try:
      self.onReload()
      evalString = 'globals()["%s"].%sTest()' % (moduleName, moduleName)
      tester = eval(evalString)
      tester.runTest()
    except Exception, e:
      import traceback
      traceback.print_exc()
      qt.QMessageBox.warning(slicer.util.mainWindow(), 
          "Reload and Test", 'Exception!\n\n' + str(e) + "\n\nSee Python Console for Stack Trace")
#
# TCIABrowserLogic
#

class TCIABrowserLogic:
  """This class should implement all the actual 
  computation done by your module.  The interface 
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget
  """
  def __init__(self):
    pass

  def hasImageData(self,volumeNode):
    """This is a dummy logic method that 
    returns true if the passed in volume
    node has valid image data
    """
    if not volumeNode:
      print('no volume node')
      return False
    if volumeNode.GetImageData() == None:
      print('no image data')
      return False
    return True

  def delayDisplay(self,message,msec=1000):
    #
    # logic version of delay display
    #
    print(message)
    self.info = qt.QDialog()
    self.infoLayout = qt.QVBoxLayout()
    self.info.setLayout(self.infoLayout)
    self.label = qt.QLabel(message,self.info)
    self.infoLayout.addWidget(self.label)
    qt.QTimer.singleShot(msec, self.info.close)
    self.info.exec_()

  def takeScreenshot(self,name,description,type=-1):
    # show the message even if not taking a screen shot
    self.delayDisplay(description)

    if self.enableScreenshots == 0:
      return

    lm = slicer.app.layoutManager()
    # switch on the type to get the requested window
    widget = 0
    if type == -1:
      # full window
      widget = slicer.util.mainWindow()
    elif type == slicer.qMRMLScreenShotDialog().FullLayout:
      # full layout
      widget = lm.viewport()
    elif type == slicer.qMRMLScreenShotDialog().ThreeD:
      # just the 3D window
      widget = lm.threeDWidget(0).threeDView()
    elif type == slicer.qMRMLScreenShotDialog().Red:
      # red slice window
      widget = lm.sliceWidget("Red")
    elif type == slicer.qMRMLScreenShotDialog().Yellow:
      # yellow slice window
      widget = lm.sliceWidget("Yellow")
    elif type == slicer.qMRMLScreenShotDialog().Green:
      # green slice window
      widget = lm.sliceWidget("Green")

    # grab and convert to vtk image data
    qpixMap = qt.QPixmap().grabWidget(widget)
    qimage = qpixMap.toImage()
    imageData = vtk.vtkImageData()
    slicer.qMRMLUtils().qImageToVtkImageData(qimage,imageData)

    annotationLogic = slicer.modules.annotations.logic()
    annotationLogic.CreateSnapShot(name, description, type, self.screenshotScaleFactor, imageData)

  def run(self,inputVolume,outputVolume,enableScreenshots=0,screenshotScaleFactor=1):
    """
    Run the actual algorithm
    """

    self.delayDisplay('Running the aglorithm')

    self.enableScreenshots = enableScreenshots
    self.screenshotScaleFactor = screenshotScaleFactor

    self.takeScreenshot('TCIABrowser-Start','Start',-1)

    return True


class TCIABrowserTest(unittest.TestCase):
  """
  This is the test case for your scripted module.
  """

  def delayDisplay(self,message,msec=1000):
    """This utility method displays a small dialog and waits.
    This does two things: 1) it lets the event loop catch up
    to the state of the test so that rendering and widget updates
    have all taken place before the test continues and 2) it
    shows the user/developer/tester the state of the test
    so that we'll know when it breaks.
    """
    print(message)
    self.info = qt.QDialog()
    self.infoLayout = qt.QVBoxLayout()
    self.info.setLayout(self.infoLayout)
    self.label = qt.QLabel(message,self.info)
    self.infoLayout.addWidget(self.label)
    qt.QTimer.singleShot(msec, self.info.close)
    self.info.exec_()

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)
    mainWindow = slicer.util.mainWindow()
    mainWindow.moduleSelector().selectModule('TCIABrowser')
    module = slicer.modules.tciabrowser
    self.moduleWidget = module.widgetRepresentation()

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_download_series()

  def test_download_series(self):

    self.delayDisplay("Starting the test")

    children = self.moduleWidget.findChildren('QPushButton')
    for child in children:
      if child.text == 'Connect':
        connectButton = child
    connectButton.click()
    activeWindow = slicer.app.activeWindow()
    if activeWindow.windowTitle == 'TCIA Browser':
      browserWindow = activeWindow
    if browserWindow != None:
      collectionsCombobox = browserWindow.findChildren('QComboBox')[0]
      currentCollection = collectionsCombobox.currentText
      if currentCollection != '':
        print 'connected to the server successfully'
        print 'current collection :', currentCollection

      tableWidgets = browserWindow.findChildren('QTableWidget')

      patientsTable = tableWidgets[0]
      selectedPatient = patientsTable.item(0,0).text()
      if selectedPatient != '':
        print 'current patient:', selectedPatient
        model = patientsTable.model()
        index = model.index(0,0)
        patientsTable.clicked(index)

      studiesTable = tableWidgets[1]
      selectedStudy = studiesTable.item(0,0).text()
      if selectedStudy != '':
        print 'current study:', selectedStudy
        model = studiesTable.model()
        index = model.index(0,0)
        studiesTable.clicked(index)

      seriesTable = tableWidgets[2]
      selectedSeries = seriesTable.item(0,0).text()
      if selectedSeries != '':
        print 'current series:', selectedSeries
        '''
        model = seriesTable.model()
        index = model.index(0,0)
        seriesTable.clicked(index)
        '''
        seriesTable.selectRow(0)

      pushButtons = browserWindow.findChildren('QPushButton')
      for pushButton in pushButtons:
        toolTip = pushButton.toolTip
        if toolTip[16:20] == 'Load':
          print toolTip[16:20]
          loadButton = pushButton

      if loadButton != None:
        print 'load button clicked'
        loadButton.click()
      else:
        print 'could not find Load button'

      scene = slicer.mrmlScene
      self.assertEqual(scene.GetNumberOfNodesByClass('vtkMRMLScalarVolumeNode'), 1)
      self.delayDisplay('Test Passed!')

