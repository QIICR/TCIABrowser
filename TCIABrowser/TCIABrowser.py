import urllib2, urllib,sys, os
import string, json, zipfile, os.path
import xml.etree.ElementTree as ET
import webbrowser
import unittest
from __main__ import vtk, qt, ctk, slicer

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

    self.progress = qt.QProgressDialog(slicer.util.mainWindow())
    # setup API key
    self.slicerApiKey = '2a38f167-95f1-4f03-99c1-0bc45472d64a'
    self.tciaBrowserModuleDirectoryPath = slicer.modules.tciabrowser.path.replace("TCIABrowser.py","")
    item = qt.QStandardItem()

    # setup the TCIA client
  
  def setup(self):
    # Instantiate and connect widgets ...

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

    # Layout within the dummy collapsible button
    browserFormLayout = qt.QVBoxLayout(browserCollapsibleButton)

    #
    # Connect Button
    #
    self.connectButton = qt.QPushButton("Connect")
    self.connectButton.toolTip = "Connect to TCIA Server."
    self.connectButton.enabled = True
    browserFormLayout.addWidget(self.connectButton)
    #
    collectionsCollapsibleGroupBox = ctk.ctkCollapsibleGroupBox()
    collectionsCollapsibleGroupBox.setTitle('Collections')
    browserFormLayout.addWidget(collectionsCollapsibleGroupBox)  # 
    collectionsFormLayout = qt.QFormLayout(collectionsCollapsibleGroupBox)
    #
    # Collection Selector ComboBox
    #
    self.collectionSelector = qt.QComboBox()
    collectionsFormLayout.addRow('Current Collection:', self.collectionSelector)
    '''
    self.infoPushButton = qt.QPushButton("?")
    collectionsFormLayout.addRow(self.infoPushButton,self.collectionSelector)
    self.infoPushButton.setMaximumWidth(25)
    '''
    #
    # Patient Table Widget 
    #
    patientsCollapsibleGroupBox = ctk.ctkCollapsibleGroupBox()
    patientsCollapsibleGroupBox.setTitle('Patients')
    browserFormLayout.addWidget(patientsCollapsibleGroupBox)
    patientsVBoxLayout1 = qt.QVBoxLayout(patientsCollapsibleGroupBox)
    patientsExpdableArea = ctk.ctkExpandableWidget()
    patientsVBoxLayout1.addWidget(patientsExpdableArea)
    patientsVBoxLayout2 = qt.QVBoxLayout(patientsExpdableArea)
    patientsVerticalLayout = qt.QVBoxLayout(patientsExpdableArea)
    self.patientsTableWidget = qt.QTableWidget()
    self.patientsModel = qt.QStandardItemModel()
    self.patientsTableWidgetHeaderLabels = ['Patient ID','Patient Name','Patient BirthDate',
        'Patient Sex','Ethnic Group']
    self.patientsTableWidget.setColumnCount(5)
    self.patientsTableWidget.setHorizontalHeaderLabels(self.patientsTableWidgetHeaderLabels)
    patientsTableWidgetHeader = self.patientsTableWidget.horizontalHeader()
    patientsTableWidgetHeader.setStretchLastSection(True)
    patientsVBoxLayout2.addWidget(self.patientsTableWidget)
    self.patientsTreeSelectionModel = self.patientsTableWidget.selectionModel()
    abstractItemView =qt.QAbstractItemView()
    self.patientsTableWidget.setSelectionBehavior(abstractItemView.SelectRows) 
    verticalheader = self.patientsTableWidget.verticalHeader()
    verticalheader.setDefaultSectionSize(20)

    # 
    # Studies Table Widget 
    #
    studiesCollapsibleGroupBox = ctk.ctkCollapsibleGroupBox()
    studiesCollapsibleGroupBox.setTitle('Studies')
    browserFormLayout.addWidget(studiesCollapsibleGroupBox) 
    studiesVBoxLayout1 = qt.QVBoxLayout(studiesCollapsibleGroupBox)
    studiesExpdableArea = ctk.ctkExpandableWidget()
    studiesVBoxLayout1.addWidget(studiesExpdableArea)
    studiesVBoxLayout2 = qt.QVBoxLayout(studiesExpdableArea)
    self.studiesTableWidget = qt.QTableWidget()
    self.studiesModel = qt.QStandardItemModel()
    self.studiesTableHeaderLabels = ['Study Instance UID','Study Date','Study Description',
        'Admitting Diagnosis Descrition','Study ID','Patient Age','Series Count']
    self.studiesTableWidget.setColumnCount(7)
    self.studiesTableWidget.setHorizontalHeaderLabels(self.studiesTableHeaderLabels)
    studiesVBoxLayout2.addWidget(self.studiesTableWidget)
    self.studiesTreeSelectionModel = self.studiesTableWidget.selectionModel()
    self.studiesTableWidget.setSelectionBehavior(abstractItemView.SelectRows) 
    studiesVerticalheader = self.studiesTableWidget.verticalHeader()
    studiesVerticalheader.setDefaultSectionSize(20)
    studiesTableWidgetHeader = self.studiesTableWidget.horizontalHeader()
    studiesTableWidgetHeader.setStretchLastSection(True)

    #
    # Series Table Widget 
    #
    seriesCollapsibleGroupBox = ctk.ctkCollapsibleGroupBox()
    seriesCollapsibleGroupBox.setTitle('Series')
    browserFormLayout.addWidget(seriesCollapsibleGroupBox)  # 
    seriesVBoxLayout1 = qt.QVBoxLayout(seriesCollapsibleGroupBox)
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
    seriesVBoxLayout2.addWidget(self.seriesTableWidget)
    self.seriesTreeSelectionModel = self.studiesTableWidget.selectionModel()
    self.seriesTableWidget.setSelectionBehavior(abstractItemView.SelectRows) 
    seriesTableWidgetHeader = self.seriesTableWidget.horizontalHeader()
    seriesTableWidgetHeader.setStretchLastSection(True)
    seriesVerticalheader = self.seriesTableWidget.verticalHeader()
    seriesVerticalheader.setDefaultSectionSize(20)

    #
    # Load Button
    #
    self.loadButton = qt.QPushButton("Download and Load")
    self.loadButton.toolTip = "Download the selected sereies and load in Slicer scene."
    self.loadButton.enabled = True
    browserFormLayout.addWidget(self.loadButton)

    #
    # Settings Area
    #
    settingsCollapsibleButton = ctk.ctkCollapsibleButton()
    settingsCollapsibleButton.text = "Advanced Settings"
    # self.layout.addWidget(settingsCollapsibleButton)
    settingsVBoxLayout = qt.QVBoxLayout(settingsCollapsibleButton)

    apiSettingsCollapsibleGroupBox = ctk.ctkCollapsibleGroupBox()
    apiSettingsCollapsibleGroupBox.setTitle('API Settings')
    settingsVBoxLayout.addWidget(apiSettingsCollapsibleGroupBox)
    apiSettingsFormLayout = qt.QFormLayout(apiSettingsCollapsibleGroupBox)

    #
    # API Settings Table
    #
    self.apiSettingsTableWidget = qt.QTableWidget()
    self.apiSettingsTableWidget.setColumnCount(2)
    self.apiSettingsTableHeaderLabels = ['API Name', 'API Key']
    self.apiSettingsTableWidget.setHorizontalHeaderLabels(self.apiSettingsTableHeaderLabels)
    apiSettingsFormLayout.addWidget(self.apiSettingsTableWidget)
    self.apiSettingsTableWidget.setSelectionBehavior(abstractItemView.SelectRows) 
    apiSettingsTableWidgetHeader = self.apiSettingsTableWidget.horizontalHeader()
    apiSettingsTableWidgetHeader.setStretchLastSection(True)
    apiSettingsVerticalheader = self.seriesTableWidget.verticalHeader()
    apiSettingsVerticalheader.setDefaultSectionSize(20)

    #
    # API Settings Buttons
    #
    self.addApiButton = qt.QPushButton("Add API")
    self.addApiButton.toolTip = "Add your own API Key."
    self.addApiButton.enabled = True
    self.removeApiButton = qt.QPushButton("Remove API")
    self.removeApiButton .toolTip = "Add your own API Key."
    self.removeApiButton .enabled = False 
    apiSettingsFormLayout.addWidget(self.addApiButton)
    apiSettingsFormLayout.addWidget(self.removeApiButton)
    
    # Layout within the dummy collapsible button

    # connections
    self.collectionSelector.connect('currentIndexChanged(QString)',self.collectionSelected)
    self.patientsTableWidget.connect('cellClicked(int,int)',self.patientSelected)
    self.studiesTableWidget.connect('cellClicked(int,int)',self.studySelected)
    self.seriesTableWidget.connect('cellClicked(int,int)',self.seriesSelected)
    self.connectButton.connect('clicked(bool)', self.onConnectButton)
    self.loadButton.connect('clicked(bool)', self.onLoadButton)

    # Add vertical spacer
    self.layout.addStretch(1)

  def cleanup(self):
    pass

  def showProgress(self, message):
    self.progress.minimumDuration = 0
    self.progress.setValue(0)
    self.progress.setMaximum(0)
    self.progress.setCancelButton(0)
    self.progress.setWindowModality(2)
    self.progress.show()
    self.progress.setLabelText(message)
    slicer.app.processEvents(qt.QEventLoop.ExcludeUserInputEvents)
    self.progress.repaint()

  def closeProgress(self):
    self.progress.close()
    self.progress.reset()

  def onConnectButton(self):
    logic = TCIABrowserLogic()
    # Instantiate TCIAClient object
    self.tcia_client = TCIAClient(self.slicerApiKey, baseUrl = 
        "https://services.cancerimagingarchive.net/services/TCIA/TCIA/query")  # Set the API-Key
    self.showProgress("Getting Available Collections")
    try:    
      response = self.tcia_client.get_collection_values()
      # self.tcia_client.printServerResponse(response)
      responseString = response.read()[:]
      self.populateCollectionsTreeView(responseString)
      self.closeProgress()
    except urllib2.HTTPError, err:
      print "Error executing program:\nError Code: ", str(err.code) , "\nMessage: " , err.read()

  def collectionSelected(self,item):
    self.clearPatientsTableWidget()
    self.clearStudiesTableWidget()
    self.clearSeriesTableWidget()
    self.selectedCollection = item
    progressMessage = "Getting available patients for collection: " + self.selectedCollection
    self.showProgress(progressMessage)
    try:    
      response = self.tcia_client.get_patient(collection = self.selectedCollection)
      # self.tcia_client.printServerResponse(response)
      responseString = response.read()[:]
      self.populatePatientsTableWidget(responseString)
      self.closeProgress()
    except urllib2.HTTPError, err:
      print "Error executing program:\nError Code: ", str(err.code) , "\nMessage: " , err.read()

  def patientSelected(self,row,column):
    self.clearStudiesTableWidget()
    self.clearSeriesTableWidget()
    self.selectedPatient = self.patientsIDs[row].text()
    progressMessage = "Getting available studies for patient ID: " + self.selectedPatient
    self.showProgress(progressMessage)
    try:    
      response = self.tcia_client.get_patient_study(patientId = self.selectedPatient)
      # self.tcia_client.printServerResponse(response)
      responseString = response.read()[:]
      self.populateStudiesTableWidget(responseString)
      self.closeProgress()
    except urllib2.HTTPError, err:
      print "Error executing program:\nError Code: ", str(err.code) , "\nMessage: " , err.read()

  def studySelected(self,row,column):
    self.clearSeriesTableWidget()
    self.selectedStudy = self.studyInstanceUIDs[row].text()
    progressMessage = "Getting available series for studyInstanceUID: " + self.selectedStudy
    self.showProgress(progressMessage)
    try:    
      response = self.tcia_client.get_series(studyInstanceUID = self.selectedStudy)
      # self.tcia_client.printServerResponse(response)
      responseString = response.read()[:]
      self.populateSeriesTableWidget(responseString)
      self.closeProgress()
    except urllib2.HTTPError, err:
      print "Error executing program:\nError Code: ", str(err.code) , "\nMessage: " , err.read()

  def seriesSelected(self,row,column):
    self.selectedSeriesUIdForDownload = self.seriesInstanceUIDs[row].text()

  def onLoadButton(self):
    #currentSeriesIndex = self.seriesTreeSelectionModel.currentIndex().row() 
    selectedCollection = self.selectedCollection
    selectedPatient = self.selectedPatient
    selectedStudy = self.selectedStudy
    selectedSeries = self.selectedSeriesUIdForDownload
    #selectedseries = self.seriesinstanceuids[currentseriesindex].text()
    # get image request
    dicomAppWidget = ctk.ctkDICOMAppWidget()
    databaseDirectory = dicomAppWidget.databaseDirectory
    tempPath = databaseDirectory + "/TCIA-Temp/" + str(selectedCollection) + "/" + str(selectedPatient) + "/" + str(selectedStudy)+ "/"
    if not os.path.exists(tempPath):
      os.makedirs(tempPath)
    fileName = tempPath + str(selectedSeries) + ".zip"
    imagesDirectory = tempPath + str(selectedSeries)
    progressMessage = "Downloading Images for series InstanceUID: " + selectedSeries
    self.showProgress(progressMessage)
    try:
      response = self.tcia_client.get_image(seriesInstanceUid = selectedSeries );
      # Save server response as images.zip in current directory
      if response.getcode() == 200:
        print "\n" + str(response.info())
        bytesRead = response.read()
        fout = open(fileName, "wb")
        fout.write(bytesRead)
        fout.close()
        print "\nDownloaded file %s.zip from the server" %fileName
        self.closeProgress()
      else:
        print "Error : " + str(response.getcode) # print error code
        print "\n" + str(response.info())
    except urllib2.HTTPError, err:
      print "Error executing program:\nError Code: ", str(err.code) , "\nMessage: " , err.read()

    progressMessage = "Extracting Images"
    # Unzip the data
    self.showProgress(progressMessage)
    self.unzip(fileName,imagesDirectory)
    self.closeProgress()
    # Import the data into dicomAppWidget and open the dicom browser
    os.remove(fileName)
    dicomAppWidget.onImportDirectory(imagesDirectory)
    # slicer.util.selectModule('DICOM')
    # load the data into slicer scene
    # print self.selectedSeriesUIdForDownload
    seriesUIDs = []
    seriesUIDs.append(self.selectedSeriesUIdForDownload)

    dicomWidget = slicer.modules.dicom.widgetRepresentation().self()
    dicomWidget.detailsPopup.offerLoadables(seriesUIDs, 'SeriesUIDList')
    dicomWidget.detailsPopup.examineForLoading()
    loadablesByPlugin = dicomWidget.detailsPopup.loadablesByPlugin
    dicomWidget.detailsPopup.loadCheckedLoadables() 

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
      self.collectionSelector.addItem(str(collections[n]['Collection']))
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
          patientID = qt.QTableWidgetItem(str(patient['PatientID']))
          self.patientsIDs.append(patientID)
          table.setItem(n,0,patientID)
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

  def populateSeriesTableWidget(self,responseString):
    self.clearSeriesTableWidget()
    table = self.seriesTableWidget
    seriesCollection = json.loads(responseString)
    table.setRowCount(len(seriesCollection))
  
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

  def clearPatientsTableWidget(self):
    table = self.patientsTableWidget
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
    import urllib2, urllib,sys, os
    import xml.etree.ElementTree as ET
    import webbrowser
    import string, json
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

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_TCIABrowser1()

  def test_TCIABrowser1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests sould exercise the functionality of the logic with different inputs
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
        print('Requesting download %s from %s...\n' % (name, url))
        urllib.urlretrieve(url, filePath)
      if loader:
        print('Loading %s...\n' % (name,))
        loader(filePath)
    self.delayDisplay('Finished with download and loading\n')

    volumeNode = slicer.util.getNode(pattern="FA")
    logic = TCIABrowserLogic()
    self.assertTrue( logic.hasImageData(volumeNode) )
    self.delayDisplay('Test passed!')



#
# Refer https://wiki.cancerimagingarchive.net/display/Public/REST+API+Usage+Guide for complete list of API
#
class TCIAClient:
    GET_IMAGE = "getImage"
    GET_MANUFACTURER_VALUES = "getManufacturerValues"
    GET_MODALITY_VALUES = "getModalityValues"
    GET_COLLECTION_VALUES = "getCollectionValues"
    GET_BODY_PART_VALUES = "getBodyPartValues"
    GET_PATIENT_STUDY = "getPatientStudy"
    GET_SERIES = "getSeries"
    GET_PATIENT = "getPatient"
    
    def __init__(self, apiKey , baseUrl):
        self.apiKey = apiKey
        self.baseUrl = baseUrl
        
    def execute(self, url, queryParameters={}):
        queryParameters = dict((k, v) for k, v in queryParameters.iteritems() if v)
        headers = {"api_key" : self.apiKey }
        queryString = "?%s" % urllib.urlencode(queryParameters)
        requestUrl = url + queryString
        request = urllib2.Request(url=requestUrl , headers=headers)
        resp = urllib2.urlopen(request)
        
        return resp
    
    def get_modality_values(self,collection = None , bodyPartExamined = None , modality = None , outputFormat = "json" ):
        serviceUrl = self.baseUrl + "/" + self.GET_MODALITY_VALUES
        queryParameters = {"Collection" : collection , "BodyPartExamined" : bodyPartExamined , "Modality" : modality , "format" : outputFormat }
        resp = self.execute(serviceUrl , queryParameters)
        return resp
    
    def get_manufacturer_values(self,collection = None , bodyPartExamined = None , modality = None , outputFormat = "json" ):
        serviceUrl = self.baseUrl + "/" + self.GET_MANUFACTURER_VALUES
        queryParameters = {"Collection" : collection , "BodyPartExamined" : bodyPartExamined , "Modality" : modality , "format" : outputFormat }
        resp = self.execute(serviceUrl , queryParameters)
        return resp
        
    def get_collection_values(self,outputFormat = "json" ):
        serviceUrl = self.baseUrl + "/" + self.GET_COLLECTION_VALUES
        queryParameters = { "format" : outputFormat }
        resp = self.execute(serviceUrl , queryParameters)
        return resp
        
    def get_body_part_values(self,collection = None , bodyPartExamined = None , modality = None , outputFormat = "csv" ):
        serviceUrl = self.baseUrl + "/" + self.GET_BODY_PART_VALUES
        queryParameters = {"Collection" : collection , "BodyPartExamined" : bodyPartExamined , "Modality" : modality , "format" : outputFormat }
        resp = self.execute(serviceUrl , queryParameters)
        return resp
    def get_patient_study(self,collection = None , patientId = None , studyInstanceUid = None , outputFormat = "json" ):
        serviceUrl = self.baseUrl + "/" + self.GET_PATIENT_STUDY
        queryParameters = {"Collection" : collection , "PatientID" : patientId , "StudyInstanceUID" : studyInstanceUid , "format" : outputFormat }
        resp = self.execute(serviceUrl , queryParameters)
        return resp
    def get_series(self,collection = None , patientId = None , studyInstanceUID = None, modality = None , outputFormat = "json" ):
        serviceUrl = self.baseUrl + "/" + self.GET_SERIES
        queryParameters = {"Collection" : collection , "PatientID" : patientId ,"StudyInstanceUID": studyInstanceUID, "Modality" : modality , "format" : outputFormat }
        resp = self.execute(serviceUrl , queryParameters)
        return resp
    def get_patient(self,collection = None , outputFormat = "json" ):
        serviceUrl = self.baseUrl + "/" + self.GET_PATIENT
        queryParameters = {"Collection" : collection , "format" : outputFormat }
        resp = self.execute(serviceUrl , queryParameters)
        return resp
    def get_image(self , seriesInstanceUid):
        serviceUrl = self.baseUrl + "/" + self.GET_IMAGE
        queryParameters = { "SeriesInstanceUID" : seriesInstanceUid }
        resp = self.execute( serviceUrl , queryParameters)
        return resp

    def printServerResponse(self, response):
      if response.getcode() == 200:
        print "Server Returned:\n"
        print response.read()
        print "\n"
      else:
        print "Error : " + str(response.getcode) # print error code
