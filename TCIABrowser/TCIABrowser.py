from __future__ import division

import codecs
import csv
import json
import logging
import os.path
import pickle
import string
import time
import unittest
import webbrowser
import xml.etree.ElementTree as ET
import zipfile
from random import randint
import DICOM
import pydicom
import os
import sys
import urllib
from __main__ import vtk, qt, ctk, slicer
from TCIABrowserLib import clinicalDataPopup, TCIAClient
from slicer.ScriptedLoadableModule import *
#
# TCIABrowser
#
class TCIABrowser(ScriptedLoadableModule):
  def __init__(self, parent):
    parent.title = "TCIA Browser"
    parent.categories = ["Informatics"]
    parent.dependencies = []
    parent.contributors = ["Alireza Mehrtash (SPL, BWH), Andrey Fedorov (SPL, BWH), Adam Li (GU)"]
    parent.helpText = """ Connect to TCIA web archive and get a list of all available collections.
    From collection selector choose a collection and the patients table will be populated. Click on a patient and
    the studies for the patient will be presented. Do the same for studies. Finally choose a series from the series
    table and download the images from the server by pressing the "Download and Load" button.
    See <a href=\"http://wiki.slicer.org/slicerWiki/index.php/Documentation/Nightly/Extensions/TCIABrowser\">
    the documentation</a> for more information."""
    parent.acknowledgementText = """ <img src=':Logos/QIICR.png'><br><br>
    Supported by NIH U24 CA180918 (PIs Kikinis and Fedorov)
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
# browserWidget Initialization
# Defines size and position
# 
class browserWindow(qt.QWidget):
  def __init__(self):
    super().__init__()

  def closeEvent(self, event):
    settings = qt.QSettings()
    if settings.value("loginStatus"):
        settings.setValue("browserWidgetGeometry", qt.QRect(self.pos, self.size))
    event.accept() 
    
#
# qTCIABrowserWidget
#
class TCIABrowserWidget(ScriptedLoadableModuleWidget): 
  def __init__(self, parent=None):
    self.loadToScene = False
    
    # self.browserWidget = qt.QWidget()
    self.browserWidget = browserWindow()
    self.browserWidget.setWindowTitle('TCIA Browser')

    self.initialConnection = False
    self.seriesTableRowCount = 0
    self.studiesTableRowCount = 0
    self.downloadProgressBars = {}
    self.downloadProgressLabels = {}
    self.selectedSeriesNicknamesDic = {}
    self.downloadQueue = {}
    self.seriesRowNumber = {}

    self.imagesToDownloadCount = 0

    self.downloadProgressBarWidgets = []
    self.settings = qt.QSettings()
    self.settings.setValue("loginStatus", False)
    self.settings.setValue("browserWidgetGeometry", "")
    item = qt.QStandardItem()

    # Put the files downloaded from TCIA in the DICOM database folder by default.
    # This makes downloaded files relocatable along with the DICOM database in
    # recent Slicer versions.
    databaseDirectory = slicer.dicomDatabase.databaseDirectory
    self.storagePath = self.settings.value("customStoragePath")  if self.settings.contains("customStoragePath") else databaseDirectory + "/TCIALocal/"
    if not os.path.exists(self.storagePath):
      os.makedirs(self.storagePath)
    if not self.settings.contains("defaultStoragePath"):
      self.settings.setValue("defaultStoragePath", (databaseDirectory + "/TCIALocal/"))
    self.cachePath = slicer.dicomDatabase.databaseDirectory  + "/TCIAServerResponseCache/"
    self.downloadedSeriesArchiveFile = slicer.dicomDatabase.databaseDirectory + '/TCIAArchive.p'
    if os.path.isfile(self.downloadedSeriesArchiveFile):
      print("Reading "+self.downloadedSeriesArchiveFile)
      f = open(self.downloadedSeriesArchiveFile, 'rb')
      self.previouslyDownloadedSeries = pickle.load(f)
      f.close()
    else:
      with open(self.downloadedSeriesArchiveFile, 'wb') as f:
        self.previouslyDownloadedSeries = []
        pickle.dump(self.previouslyDownloadedSeries, f)
      f.close()

    if not os.path.exists(self.cachePath):
      os.makedirs(self.cachePath)
    self.useCacheFlag = False

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
    
  def enter(self):
    pass

  def setup(self):
    # Instantiate and connect widgets ...
    if 'TCIABrowser' in slicer.util.moduleNames():
      self.modulePath = slicer.modules.tciabrowser.path.replace("TCIABrowser.py", "")
    else:
      self.modulePath = '.'
    self.reportIcon = qt.QIcon(self.modulePath + '/Resources/Icons/report.png')
    downloadAndIndexIcon = qt.QIcon(self.modulePath + '/Resources/Icons/downloadAndIndex.png')
    downloadAndLoadIcon = qt.QIcon(self.modulePath + '/Resources/Icons/downloadAndLoad.png')
    browserIcon = qt.QIcon(self.modulePath + '/Resources/Icons/TCIABrowser.png')
    cancelIcon = qt.QIcon(self.modulePath + '/Resources/Icons/cancel.png')
    self.downloadIcon = qt.QIcon(self.modulePath + '/Resources/Icons/download.png')
    self.storedlIcon = qt.QIcon(self.modulePath + '/Resources/Icons/stored.png')
    self.browserWidget.setWindowIcon(browserIcon)

    #
    # Reload and Test area
    #
    reloadCollapsibleButton = ctk.ctkCollapsibleButton()
    reloadCollapsibleButton.text = "Reload && Test"
    # uncomment the next line for developing and testing
    # self.layout.addWidget(reloadCollapsibleButton)
    # reloadFormLayout = qt.QFormLayout(reloadCollapsibleButton)

    # reload button
    # (use this during development, but remove it when delivering your module to users)
    # self.reloadButton = qt.QPushButton("Reload")
    # self.reloadButton.toolTip = "Reload this module."
    # self.reloadButton.name = "TCIABrowser Reload"
    # reloadFormLayout.addWidget(self.reloadButton)
    # self.reloadButton.connect('clicked()', self.onReload)

    # reload and test button
    # (use this during development, but remove it when delivering your module to users)
    # self.reloadAndTestButton = qt.QPushButton("Reload and Test")
    # self.reloadAndTestButton.toolTip = "Reload this module and then run the self tests."
    # reloadFormLayout.addWidget(self.reloadAndTestButton)
    # self.reloadAndTestButton.connect('clicked()', self.onReloadAndTest)

    #
    # Browser Area
    #
    browserCollapsibleButton = ctk.ctkCollapsibleButton()
    browserCollapsibleButton.text = "TCIA Browser"
    self.layout.addWidget(browserCollapsibleButton)
    browserLayout = qt.QGridLayout(browserCollapsibleButton)

    self.popupGeometry = qt.QRect()
    mainWindow = slicer.util.mainWindow()
    if mainWindow:
      width = mainWindow.width * 0.75
      height = mainWindow.height * 0.75
      self.popupGeometry.setWidth(width)
      self.popupGeometry.setHeight(height)
      self.popupPositioned = False
      self.browserWidget.setGeometry(self.popupGeometry)
    
    #
    # Login Area
    #
    self.promptLabel = qt.QLabel("To browse collections, please log in first.")
    self.usernameLabel = qt.QLabel("Username: ")
    self.passwordLabel = qt.QLabel("Password: ")
    self.usernameEdit = qt.QLineEdit("nbia_guest")
    self.usernameEdit.setPlaceholderText("For public access, enter \"nbia_guest\".")
    self.passwordEdit = qt.QLineEdit()
    self.passwordEdit.setPlaceholderText("No password required for public access.")
    self.passwordEdit.setEchoMode(qt.QLineEdit.Password)
    self.loginButton = qt.QPushButton("Log In")
    self.loginButton.toolTip = "Logging in to TCIA Server."
    self.loginButton.enabled = True
    self.nlstSwitch = qt.QCheckBox("NLST Database")
    self.nlstSwitch.setCheckState(False)
    self.nlstSwitch.setTristate(False)
    browserLayout.addWidget(self.usernameLabel, 1, 1, 1, 1)
    browserLayout.addWidget(self.usernameEdit, 1, 2, 1, 1)
    browserLayout.addWidget(self.passwordLabel, 2, 1, 1, 1)
    browserLayout.addWidget(self.passwordEdit, 2, 2, 1, 1)
    browserLayout.addWidget(self.promptLabel, 0, 0, 1, 0)
    browserLayout.addWidget(self.loginButton, 3, 1, 2, 1)
    browserLayout.addWidget(self.nlstSwitch, 3, 2, 1, 1)
    self.logoutButton = qt.QPushButton("Log Out")
    self.logoutButton.toolTip = "Logging out of TCIA Browser."
    self.logoutButton.hide()
    browserLayout.addWidget(self.logoutButton, 1, 0, 2, 1)
    
    #
    # Show Browser Button
    #
    self.showBrowserButton = qt.QPushButton("Show Browser")
    # self.showBrowserButton.toolTip = "."
    self.showBrowserButton.enabled = False
    self.showBrowserButton.hide()
    browserLayout.addWidget(self.showBrowserButton, 1, 2, 2, 1)

    # Browser Widget Layout within the collapsible button
    browserWidgetLayout = qt.QVBoxLayout(self.browserWidget)
    self.collectionsCollapsibleGroupBox = ctk.ctkCollapsibleGroupBox()
    self.collectionsCollapsibleGroupBox.setTitle('Collections')
    browserWidgetLayout.addWidget(self.collectionsCollapsibleGroupBox)
    collectionsFormLayout = qt.QHBoxLayout(self.collectionsCollapsibleGroupBox)

    #
    # Collection Selector ComboBox
    #
    self.collectionSelectorLabel = qt.QLabel('Current Collection:')
    collectionsFormLayout.addWidget(self.collectionSelectorLabel)
    # Selector ComboBox
    self.collectionSelector = qt.QComboBox()
    self.collectionSelector.setMinimumWidth(200)
    collectionsFormLayout.addWidget(self.collectionSelector)

    #
    # Use Cache CheckBox
    #
    self.useCacheCeckBox = qt.QCheckBox("Cache server responses")
    self.useCacheCeckBox.toolTip = '''For faster browsing if this box is checked\
    the browser will cache server responses and on further calls\
    would populate tables based on saved data on disk.'''

    collectionsFormLayout.addWidget(self.useCacheCeckBox)
    self.useCacheCeckBox.setCheckState(False)
    self.useCacheCeckBox.setTristate(False)
    collectionsFormLayout.addStretch(4)
    logoLabelText = "<img src='" + self.modulePath + "/Resources/Logos/logo-vertical.png'" + ">"
    self.logoLabel = qt.QLabel(logoLabelText)
    collectionsFormLayout.addWidget(self.logoLabel)
    
    #
    # Collection Description Widget
    #
    self.collectionDescriptions = []
    self.collectionDescriptionCollapsibleGroupBox = ctk.ctkCollapsibleGroupBox()
    self.collectionDescriptionCollapsibleGroupBox.setTitle('Collection Description')
    self.collectionDescription = qt.QTextBrowser()
    collectionDescriptionBoxLayout = qt.QVBoxLayout(self.collectionDescriptionCollapsibleGroupBox)
    collectionDescriptionBoxLayout.addWidget(self.collectionDescription)
    browserWidgetLayout.addWidget(self.collectionDescriptionCollapsibleGroupBox)
    
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
    # patientsVerticalLayout = qt.QVBoxLayout(patientsExpdableArea)
    self.patientsTableWidget = qt.QTableWidget()
    self.patientsModel = qt.QStandardItemModel()
    self.patientsTableHeaderLabels = ['Patient ID', 'Patient Sex', 'Phantom', 'Species Description']
    self.patientsTableWidget.setColumnCount(4)
    self.patientsTableWidget.sortingEnabled = True
    self.patientsTableWidget.setHorizontalHeaderLabels(self.patientsTableHeaderLabels)
    self.patientsTableWidgetHeader = self.patientsTableWidget.horizontalHeader()
    self.patientsTableWidgetHeader.setStretchLastSection(True)
    self.patientsTableWidgetHeader.setDefaultAlignment(qt.Qt.AlignLeft)
    # patientsTableWidgetHeader.setResizeMode(qt.QHeaderView.Stretch)
    patientsVBoxLayout2.addWidget(self.patientsTableWidget)
    self.patientsTreeSelectionModel = self.patientsTableWidget.selectionModel()
    abstractItemView = qt.QAbstractItemView()
    self.patientsTableWidget.setSelectionBehavior(abstractItemView.SelectRows)
    verticalheader = self.patientsTableWidget.verticalHeader()
    verticalheader.setDefaultSectionSize(20)
    patientsVBoxLayout1.setSpacing(0)
    patientsVBoxLayout2.setSpacing(0)
    patientsVBoxLayout1.setMargin(0)
    patientsVBoxLayout2.setContentsMargins(7, 3, 7, 7)

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
    self.studiesTableWidget.setCornerButtonEnabled(True)
    self.studiesModel = qt.QStandardItemModel()
    self.studiesTableHeaderLabels = ['Study Instance UID', 'Study Date', 'Study Description','Patient Age', 
                                     'Event Type', 'Days From Event', 'Series Count']
    self.studiesTableWidget.setColumnCount(7)
    self.studiesTableWidget.sortingEnabled = True
    self.studiesTableWidget.hideColumn(0)
    self.studiesTableWidget.setHorizontalHeaderLabels(self.studiesTableHeaderLabels)
    self.studiesTableWidget.resizeColumnsToContents()
    studiesVBoxLayout2.addWidget(self.studiesTableWidget)
    self.studiesTreeSelectionModel = self.studiesTableWidget.selectionModel()
    self.studiesTableWidget.setSelectionBehavior(abstractItemView.SelectRows)
    studiesVerticalheader = self.studiesTableWidget.verticalHeader()
    studiesVerticalheader.setDefaultSectionSize(20)
    self.studiesTableWidgetHeader = self.studiesTableWidget.horizontalHeader()
    self.studiesTableWidgetHeader.setStretchLastSection(True)
    self.studiesTableWidgetHeader.setDefaultAlignment(qt.Qt.AlignLeft)
    studiesSelectOptionsWidget = qt.QWidget()
    studiesSelectOptionsLayout = qt.QHBoxLayout(studiesSelectOptionsWidget)
    studiesSelectOptionsLayout.setMargin(0)
    studiesVBoxLayout2.addWidget(studiesSelectOptionsWidget)
    studiesSelectLabel = qt.QLabel('Select:')
    studiesSelectOptionsLayout.addWidget(studiesSelectLabel)
    self.studiesSelectAllButton = qt.QPushButton('All')
    self.studiesSelectAllButton.enabled = False
    self.studiesSelectAllButton.setMaximumWidth(50)
    studiesSelectOptionsLayout.addWidget(self.studiesSelectAllButton)
    self.studiesSelectNoneButton = qt.QPushButton('None')
    self.studiesSelectNoneButton.enabled = False
    self.studiesSelectNoneButton.setMaximumWidth(50)
    studiesSelectOptionsLayout.addWidget(self.studiesSelectNoneButton)
    studiesSelectOptionsLayout.addStretch(1)
    studiesVBoxLayout1.setSpacing(0)
    studiesVBoxLayout2.setSpacing(0)
    studiesVBoxLayout1.setMargin(0)
    studiesVBoxLayout2.setContentsMargins(7, 3, 7, 7)

    #
    # Series Table Widget
    #
    self.seriesCollapsibleGroupBox = ctk.ctkCollapsibleGroupBox()
    self.seriesCollapsibleGroupBox.setTitle('Series')
    browserWidgetLayout.addWidget(self.seriesCollapsibleGroupBox)
    seriesVBoxLayout1 = qt.QVBoxLayout(self.seriesCollapsibleGroupBox)
    seriesExpdableArea = ctk.ctkExpandableWidget()
    seriesVBoxLayout1.addWidget(seriesExpdableArea)
    seriesVBoxLayout2 = qt.QVBoxLayout(seriesExpdableArea)
    self.seriesTableWidget = qt.QTableWidget()
    # self.seriesModel = qt.QStandardItemModel()
    self.seriesTableWidget.setColumnCount(12)
    self.seriesTableWidget.sortingEnabled = True
    self.seriesTableWidget.hideColumn(0)
    self.seriesTableHeaderLabels = ['Series Instance UID', 'Status', 'Series Description', 'Series Number', 
                                    'Modality', 'Body Part Examined', 'Protocol Name', 'Manufacturer', 
                                    'Manufacturer Model Name', 'Image Count', 'File Size (MB)', 'License URI']
    self.seriesTableWidget.setHorizontalHeaderLabels(self.seriesTableHeaderLabels)
    self.seriesTableWidget.resizeColumnsToContents()
    seriesVBoxLayout2.addWidget(self.seriesTableWidget)
    self.seriesTreeSelectionModel = self.studiesTableWidget.selectionModel()
    self.seriesTableWidget.setSelectionBehavior(abstractItemView.SelectRows)
    self.seriesTableWidget.setSelectionMode(3)
    self.seriesTableWidgetHeader = self.seriesTableWidget.horizontalHeader()
    self.seriesTableWidgetHeader.setStretchLastSection(True)
    self.seriesTableWidgetHeader.setDefaultAlignment(qt.Qt.AlignLeft)
    # seriesTableWidgetHeader.setResizeMode(qt.QHeaderView.Stretch)
    seriesVerticalheader = self.seriesTableWidget.verticalHeader()
    seriesVerticalheader.setDefaultSectionSize(20)

    seriesSelectOptionsWidget = qt.QWidget()
    seriesSelectOptionsLayout = qt.QHBoxLayout(seriesSelectOptionsWidget)
    seriesVBoxLayout2.addWidget(seriesSelectOptionsWidget)
    seriesSelectOptionsLayout.setMargin(0)
    seriesSelectLabel = qt.QLabel('Select:')
    seriesSelectOptionsLayout.addWidget(seriesSelectLabel)
    self.seriesSelectAllButton = qt.QPushButton('All')
    self.seriesSelectAllButton.enabled = False
    self.seriesSelectAllButton.setMaximumWidth(50)
    seriesSelectOptionsLayout.addWidget(self.seriesSelectAllButton)
    self.seriesSelectNoneButton = qt.QPushButton('None')
    self.seriesSelectNoneButton.enabled = False
    self.seriesSelectNoneButton.setMaximumWidth(50)
    seriesSelectOptionsLayout.addWidget(self.seriesSelectNoneButton)
    seriesVBoxLayout1.setSpacing(0)
    seriesVBoxLayout2.setSpacing(0)
    seriesVBoxLayout1.setMargin(0)
    seriesVBoxLayout2.setContentsMargins(7, 3, 7, 7)

    seriesSelectOptionsLayout.addStretch(1)
    self.imagesCountLabel = qt.QLabel()
    self.imagesCountLabel.text = 'No. of images to download: ' + '<span style=" font-size:8pt; font-weight:600; ' \
                    'color:#aa0000;">' + str(self.imagesToDownloadCount) + '</span>' + ' '
    seriesSelectOptionsLayout.addWidget(self.imagesCountLabel)
    # seriesSelectOptionsLayout.setAlignment(qt.Qt.AlignTop)

    # Index Button
    #
    self.indexButton = qt.QPushButton()
    self.indexButton.setMinimumWidth(50)
    self.indexButton.toolTip = "Download and Index: The browser will download" \
                   " the selected sereies and index them in 3D Slicer DICOM Database."
    self.indexButton.setIcon(downloadAndIndexIcon)
    iconSize = qt.QSize(70, 40)
    self.indexButton.setIconSize(iconSize)
    # self.indexButton.setMinimumHeight(50)
    self.indexButton.enabled = False
    # downloadWidgetLayout.addStretch(4)
    seriesSelectOptionsLayout.addWidget(self.indexButton)

    # downloadWidgetLayout.addStretch(1)
    #
    # Load Button
    #
    self.loadButton = qt.QPushButton("")
    self.loadButton.setMinimumWidth(50)
    self.loadButton.setIcon(downloadAndLoadIcon)
    self.loadButton.setIconSize(iconSize)
    # self.loadButton.setMinimumHeight(50)
    self.loadButton.toolTip = "Download and Load: The browser will download" \
                  " the selected sereies and Load them in 3D Slicer scene."
    self.loadButton.enabled = False
    seriesSelectOptionsLayout.addWidget(self.loadButton)
    # downloadWidgetLayout.addStretch(4)

    self.cancelDownloadButton = qt.QPushButton('')
    seriesSelectOptionsLayout.addWidget(self.cancelDownloadButton)
    self.cancelDownloadButton.setIconSize(iconSize)
    self.cancelDownloadButton.toolTip = "Cancel all downloads."
    self.cancelDownloadButton.setIcon(cancelIcon)
    self.cancelDownloadButton.enabled = False

    self.statusFrame = qt.QFrame()
    browserWidgetLayout.addWidget(self.statusFrame)
    statusHBoxLayout = qt.QHBoxLayout(self.statusFrame)
    statusHBoxLayout.setMargin(0)
    statusHBoxLayout.setSpacing(0)
    self.statusLabel = qt.QLabel('')
    statusHBoxLayout.addWidget(self.statusLabel)
    statusHBoxLayout.addStretch(1)
    
    #
    # clinical data context menu
    #
    self.patientsTableWidget.setContextMenuPolicy(2)
    self.clinicalDataRetrieveAction = qt.QAction("Get Clinical Data", self.patientsTableWidget)
    self.patientsTableWidget.addAction(self.clinicalDataRetrieveAction)
    self.clinicalDataRetrieveAction.enabled = False

    #
    # delete data context menu
    #
    self.seriesTableWidget.setContextMenuPolicy(2)
    self.removeSeriesAction = qt.QAction("Remove from disk", self.seriesTableWidget)
    self.seriesTableWidget.addAction(self.removeSeriesAction)
    # self.removeSeriesAction.enabled = False

    #
    # Settings Area
    #
    settingsCollapsibleButton = ctk.ctkCollapsibleButton()
    settingsCollapsibleButton.text = "Settings"
    self.layout.addWidget(settingsCollapsibleButton)
    settingsGridLayout = qt.QGridLayout(settingsCollapsibleButton)
    settingsCollapsibleButton.collapsed = True

    # Storage Path button
    #
    # storageWidget = qt.QWidget()
    # storageFormLayout = qt.QFormLayout(storageWidget)
    # settingsVBoxLayout.addWidget(storageWidget)
    storagePathLabel = qt.QLabel("Storage Folder: ")
    self.storagePathButton = ctk.ctkDirectoryButton()
    self.storagePathButton.directory = self.storagePath
    self.storageResetButton = qt.QPushButton("Reset Path")
    self.storageResetButton.toolTip = "Resetting the storage folder to default."
    self.storageResetButton.enabled  = True if self.settings.contains("customStoragePath") else False
    settingsGridLayout.addWidget(storagePathLabel, 0, 0, 1, 1)
    settingsGridLayout.addWidget(self.storagePathButton, 0, 1, 1, 4)
    settingsGridLayout.addWidget(self.storageResetButton, 1, 0, 1, 1)
    self.clinicalPopup = clinicalDataPopup.clinicalDataPopup(self.cachePath, self.reportIcon)

    # connections
    self.showBrowserButton.connect('clicked(bool)', self.onShowBrowserButton)
    self.collectionSelector.connect('currentIndexChanged(QString)', self.collectionSelected)
    self.patientsTableWidget.connect('itemSelectionChanged()', self.patientsTableSelectionChanged)
    self.studiesTableWidget.connect('itemSelectionChanged()', self.studiesTableSelectionChanged)
    self.seriesTableWidget.connect('itemSelectionChanged()', self.seriesSelected)
    self.loginButton.connect('clicked(bool)', self.AccountSelected)
    self.logoutButton.connect('clicked(bool)', self.onLogoutButton)
    self.useCacheCeckBox.connect('stateChanged(int)', self.onUseCacheStateChanged)
    self.indexButton.connect('clicked(bool)', self.onIndexButton)
    self.loadButton.connect('clicked(bool)', self.onLoadButton)
    self.cancelDownloadButton.connect('clicked(bool)', self.onCancelDownloadButton)
    self.storagePathButton.connect('directoryChanged(const QString &)', self.onStoragePathButton)
    self.clinicalDataRetrieveAction.connect('triggered()', self.onContextMenuTriggered)
    self.removeSeriesAction.connect('triggered()', self.onRemoveSeriesContextMenuTriggered)
    self.clinicalDataRetrieveAction.connect('triggered()', self.clinicalPopup.open)
    self.seriesSelectAllButton.connect('clicked(bool)', self.onSeriesSelectAllButton)
    self.seriesSelectNoneButton.connect('clicked(bool)', self.onSeriesSelectNoneButton)
    self.studiesSelectAllButton.connect('clicked(bool)', self.onStudiesSelectAllButton)
    self.studiesSelectNoneButton.connect('clicked(bool)', self.onStudiesSelectNoneButton)
    self.storageResetButton.connect('clicked(bool)', self.onStorageResetButton)
    self.patientsTableWidget.horizontalHeader().sortIndicatorChanged.connect(lambda: self.tableWidgetReorder("patients"))
    self.studiesTableWidget.horizontalHeader().sortIndicatorChanged.connect(lambda: self.tableWidgetReorder("studies"))
    self.seriesTableWidget.horizontalHeader().sortIndicatorChanged.connect(lambda: self.tableWidgetReorder("series"))
    
    # Add vertical spacer
    self.layout.addStretch(1)
  def tableWidgetReorder(self, tableType):
    if tableType == "patients":
        self.patientsIDs = []
        self.phantoms = []
        self.patientSexes = []
        self.speciesDescriptions = []
        for n in range(self.patientsTableWidget.rowCount): 
            self.patientsIDs.append(self.patientsTableWidget.item(n, 0))
            self.phantoms.append(self.patientsTableWidget.item(n, 1))
            self.patientSexes.append(self.patientsTableWidget.item(n, 2))
            self.speciesDescriptions.append(self.patientsTableWidget.item(n, 3))
    elif tableType == "studies":
        if self.studiesTableWidget.rowCount != 0:
            self.studyInstanceUIDs = []
            self.studyDates = []
            self.studyDescriptions = []
            self.patientAges = []
            self.longitudinalTemporalEventTypes = []
            self.longitudinalTemporalOffsetFromEvents = []
            self.seriesCounts = []
            for n in range(self.studiesTableWidget.rowCount): 
                self.studyInstanceUIDs.append(self.studiesTableWidget.item(n, 0))
                self.studyDates.append(self.studiesTableWidget.item(n, 1))
                self.studyDescriptions.append(self.studiesTableWidget.item(n, 2))
                self.patientAges.append(self.studiesTableWidget.item(n, 3))
                self.longitudinalTemporalEventTypes.append(self.studiesTableWidget.item(n, 4))
                self.longitudinalTemporalOffsetFromEvents.append(self.studiesTableWidget.item(n, 5))
                self.seriesCounts.append(self.studiesTableWidget.item(n, 6))
    else:
        if self.seriesTableWidget.rowCount != 0:
            self.seriesInstanceUIDs = []
            self.downloadStatusCollection = []
            self.seriesDescriptions = []
            self.seriesNumbers = []
            self.modalities = []
            self.bodyPartsExamined = []
            self.protocolNames = []
            self.manufacturers = []
            self.manufacturerModelNames = []
            self.imageCounts = []
            self.fileSizes = []
            self.licenseURIs = []
            for n in range(self.seriesTableWidget.rowCount): 
                self.seriesInstanceUIDs.append(self.seriesTableWidget.item(n, 0))
                self.downloadStatusCollection.append(self.seriesTableWidget.item(n, 1))
                self.seriesDescriptions.append(self.seriesTableWidget.item(n, 2))
                self.seriesNumbers.append(self.seriesTableWidget.item(n, 3))
                self.modalities.append(self.seriesTableWidget.item(n, 4))
                self.bodyPartsExamined.append(self.seriesTableWidget.item(n, 5))
                self.protocolNames.append(self.seriesTableWidget.item(n, 6))
                self.manufacturers.append(self.seriesTableWidget.item(n, 7))
                self.manufacturerModelNames.append(self.seriesTableWidget.item(n, 8))
                self.imageCounts.append(self.seriesTableWidget.item(n, 9))
                self.fileSizes.append(self.seriesTableWidget.item(n, 10))
                self.licenseURIs.append(self.seriesTableWidget.item(n, 11))
  
  def cleanup(self):
    pass
  
  def AccountSelected(self):
    # print(self.closeEvent())
    if self.nlstSwitch.isChecked() and (self.usernameEdit.text.strip() != 'nbia_guest' or self.passwordEdit.text.strip() != ''):
        choice = qt.QMessageBox.warning(slicer.util.mainWindow(), 'TCIA Browser', 
                               "NLST is selected but username is not \'nbia_guest\' or password is given, any changes in these fields will be nullified, proceed?", 
                               qt.QMessageBox.Ok | qt.QMessageBox.Cancel)
        if (choice == qt.QMessageBox.Cancel):
            return None
        self.getCollectionValues()
    elif self.usernameEdit.text.strip() == '' or self.passwordEdit.text.strip() == '':
        if self.usernameEdit.text.strip() != 'nbia_guest':
            qt.QMessageBox.critical(slicer.util.mainWindow(), 'TCIA Browser', "Please enter username and password.", qt.QMessageBox.Ok)
        else:
            self.getCollectionValues()
    else:
        self.getCollectionValues()
        
  def onLogoutButton(self):
    if self.loginButton.isVisible():
        self.settings.setValue("loginStatus", True)
        if hasattr(self.TCIAClient, "exp_time"): 
            message = "You have logged in. Your token will expire at " + str(self.TCIAClient.exp_time)
        else: message = "You have logged in."
        self.promptLabel.setText(message)
        self.usernameLabel.hide()
        self.usernameEdit.hide()
        self.passwordLabel.hide()
        self.passwordEdit.hide()
        self.loginButton.hide()
        self.nlstSwitch.hide()
        self.logoutButton.show()
        self.showBrowserButton.show()
        self.showBrowserButton.enabled = True
    else:
        self.collectionDescriptions = []
        if self.usernameEdit.text.strip() != "nbia_guest":
                self.TCIAClient.logOut()
        del(self.TCIAClient)
        self.settings.setValue("loginStatus", False)
        self.browserWidget.close()
        self.promptLabel.setText("To browse collections, please log in first")
        self.usernameEdit.setText("")
        self.usernameLabel.show()
        self.usernameEdit.show()
        self.passwordEdit.setText("")
        self.passwordLabel.show()
        self.passwordEdit.show()
        self.loginButton.show()
        self.nlstSwitch.show()
        self.logoutButton.hide()
        self.showBrowserButton.hide()
        self.showBrowserButton.enabled = False
        self.settings.setValue("browserWidgetGeometry", "")
    
  def onShowBrowserButton(self):
    self.showBrowser()

  def onUseCacheStateChanged(self, state):
    if state == 0:
      self.useCacheFlag = False
    elif state == 2:
      self.useCacheFlag = True

  def onContextMenuTriggered(self):
    self.clinicalPopup.getData(self.selectedCollection, self.selectedPatient)

  def onRemoveSeriesContextMenuTriggered(self):
    removeList = []
    for uid in self.seriesInstanceUIDs:
      if uid.isSelected():
        row = self.seriesTableWidget.row(uid)
        self.seriesTableWidget.item(row, 1).setIcon(self.downloadIcon)
        removeList.append(uid.text())
        slicer.dicomDatabase.removeSeries(uid.text(), True)
    with open(self.downloadedSeriesArchiveFile, 'rb') as f:
      self.previouslyDownloadedSeries = pickle.load(f)
    f.close()
    updatedDownloadSeries = []
    for item in self.previouslyDownloadedSeries:
      if item not in removeList:
        updatedDownloadSeries.append(item)
    with open(self.downloadedSeriesArchiveFile, 'wb') as f:
      pickle.dump(updatedDownloadSeries,f)
    f.close()
    self.previouslyDownloadedSeries = updatedDownloadSeries
    # self.studiesTableSelectionChanged()

  def showBrowser(self):
    self.browserWidget.adjustSize()
    if not self.browserWidget.isVisible():
      self.popupPositioned = True
      self.browserWidget.show()
      if self.settings.value("browserWidgetGeometry") != "":
          self.browserWidget.setGeometry(self.settings.value("browserWidgetGeometry"))
    self.browserWidget.raise_()

    if not self.popupPositioned:
      mainWindow = slicer.util.mainWindow()
      screenMainPos = mainWindow.pos
      x = screenMainPos.x() + 100
      y = screenMainPos.y() + 100
      self.browserWidget.move(qt.QPoint(x, y))
      self.popupPositioned = True

  def showStatus(self, message):
    self.statusLabel.text = message
    self.statusLabel.setStyleSheet("QLabel { background-color : #F0F0F0 ; color : #383838; }")
    slicer.app.processEvents()

  def clearStatus(self):
    self.statusLabel.text = ''
    self.statusLabel.setStyleSheet("QLabel { background-color : white; color : black; }")

  def onStoragePathButton(self):
    self.storagePath = self.storagePathButton.directory
    self.settings.setValue("customStoragePath", self.storagePath)
    self.storageResetButton.enabled = True

  def onStorageResetButton(self):
    self.settings.remove("customStoragePath")
    self.storageResetButton.enabled = False
    self.storagePath = self.settings.value("defaultStoragePath")
    self.storagePathButton.directory = self.storagePath
    
  def getCollectionValues(self):
    self.initialConnection = True
    # Instantiate TCIAClient object
    self.TCIAClient = TCIAClient.TCIAClient(self.usernameEdit.text.strip(), self.passwordEdit.text.strip(), self.nlstSwitch.isChecked())
    self.showStatus("Getting Available Collections")
    if hasattr(self.TCIAClient, "credentialError"):
        qt.QMessageBox.critical(slicer.util.mainWindow(),'TCIA Browser', self.TCIAClient.credentialError, qt.QMessageBox.Ok)
        return None
    try:
      response = self.TCIAClient.get_collection_values()
      self.collectionDescriptions = self.TCIAClient.get_collection_descriptions()
      self.populateCollectionsTreeView(response)
      self.clearStatus()
    except Exception as error:
      self.loginButton.enabled = True
      self.clearStatus()
      message = "getCollectionValues: Error in getting response from TCIA server.\nHTTP Error:\n" + str(error)
      qt.QMessageBox.critical(slicer.util.mainWindow(),
                  'TCIA Browser', message, qt.QMessageBox.Ok)
    self.onLogoutButton()
    self.showBrowser()

  def onStudiesSelectAllButton(self):
    self.studiesTableWidget.selectAll()

  def onStudiesSelectNoneButton(self):
    self.studiesTableWidget.clearSelection()

  def onSeriesSelectAllButton(self):
    self.seriesTableWidget.selectAll()

  def onSeriesSelectNoneButton(self):
    self.seriesTableWidget.clearSelection()

  def collectionSelected(self, item):
    self.loadButton.enabled = False
    self.indexButton.enabled = False
    self.clearPatientsTableWidget()
    self.clearStudiesTableWidget()
    self.clearSeriesTableWidget()
    self.selectedCollection = item
    cacheFile = self.cachePath + self.selectedCollection + '.json'
    self.progressMessage = "Getting available patients for collection: " + self.selectedCollection
    self.showStatus(self.progressMessage)
    if self.selectedCollection[0:4] != 'TCGA':
      self.clinicalDataRetrieveAction.enabled = False
    else:
      self.clinicalDataRetrieveAction.enabled = True
    
    filteredDescriptions = list(filter(lambda record: record["collectionName"] == self.selectedCollection, self.collectionDescriptions))
    if len(filteredDescriptions) != 0: self.collectionDescription.setHtml(filteredDescriptions[0]["description"])

    patientsList = None
    if os.path.isfile(cacheFile) and self.useCacheFlag:
      f = codecs.open(cacheFile, 'rb', encoding='utf8')
      patientsList = f.read()[:]
      f.close()

      if not len(patientsList):
        patientsList = None

    if patientsList:
      self.populatePatientsTableWidget(patientsList)
      self.clearStatus()
      groupBoxTitle = 'Patients (Accessed: ' + time.ctime(os.path.getmtime(cacheFile)) + ')'
      self.patientsCollapsibleGroupBox.setTitle(groupBoxTitle)

    else:
      try:
        response = self.TCIAClient.get_patient(collection=self.selectedCollection)
        with open(cacheFile, 'wb') as outputFile:
          self.stringBufferReadWrite(outputFile, response)
        outputFile.close()
        f = codecs.open(cacheFile, 'rb', encoding='utf8')
        responseString = json.loads(f.read()[:])
        self.populatePatientsTableWidget(responseString)
        groupBoxTitle = 'Patients (Accessed: ' + time.ctime(os.path.getmtime(cacheFile)) + ')'
        self.patientsCollapsibleGroupBox.setTitle(groupBoxTitle)
        self.clearStatus()

      except Exception as error:
        self.clearStatus()
        message = "collectionSelected: Error in getting response from TCIA server.\nHTTP Error:\n" + str(error)
        qt.QMessageBox.critical(slicer.util.mainWindow(),
                    'TCIA Browser', message, qt.QMessageBox.Ok)

  def patientsTableSelectionChanged(self):
    self.clearStudiesTableWidget()
    self.clearSeriesTableWidget()
    self.studiesTableRowCount = 0
    self.numberOfSelectedPatients = 0
    for n in range(len(self.patientsIDs)):
      if self.patientsIDs[n].isSelected():
        self.numberOfSelectedPatients += 1
        self.patientSelected(n)

  def patientSelected(self, row):
    self.loadButton.enabled = False
    self.indexButton.enabled = False
    # self.clearStudiesTableWidget()
    self.clearSeriesTableWidget()
    self.selectedPatient = self.patientsIDs[row].text()
    cacheFile = self.cachePath + self.selectedPatient + '.json'
    self.progressMessage = "Getting available studies for patient ID: " + self.selectedPatient
    self.showStatus(self.progressMessage)
    if os.path.isfile(cacheFile) and self.useCacheFlag:
      f = codecs.open(cacheFile, 'rb', encoding='utf8')
      responseString = f.read()[:]
      f.close()
      self.populateStudiesTableWidget(responseString)
      self.clearStatus()
      if self.numberOfSelectedPatients == 1:
        groupBoxTitle = 'Studies (Accessed: ' + time.ctime(os.path.getmtime(cacheFile)) + ')'
      else:
        groupBoxTitle = 'Studies '

      self.studiesCollapsibleGroupBox.setTitle(groupBoxTitle)

    else:
      try:
        response = self.TCIAClient.get_patient_study(patientId=self.selectedPatient)
        responseString = json.dumps(response).encode("utf-8")
        with open(cacheFile, 'wb') as outputFile:
          outputFile.write(responseString)
          outputFile.close()
        f = codecs.open(cacheFile, 'rb', encoding='utf8')
        responseString = f.read()[:]
        self.populateStudiesTableWidget(responseString)
        if self.numberOfSelectedPatients == 1:
          groupBoxTitle = 'Studies (Accessed: ' + time.ctime(os.path.getmtime(cacheFile)) + ')'
        else:
          groupBoxTitle = 'Studies '

        self.studiesCollapsibleGroupBox.setTitle(groupBoxTitle)
        self.clearStatus()

      except Exception as error:
        self.clearStatus()
        message = "patientSelected: Error in getting response from TCIA server.\nHTTP Error:\n" + str(error)
        qt.QMessageBox.critical(slicer.util.mainWindow(),
                    'TCIA Browser', message, qt.QMessageBox.Ok)

  def studiesTableSelectionChanged(self):
    self.clearSeriesTableWidget()
    self.seriesTableRowCount = 0
    self.numberOfSelectedStudies = 0
    for n in range(len(self.studyInstanceUIDs)):
      if self.studyInstanceUIDs[n].isSelected():
        self.numberOfSelectedStudies += 1
        self.studySelected(n)

  def studySelected(self, row):
    self.loadButton.enabled = False
    self.indexButton.enabled = False
    self.selectedStudy = self.studyInstanceUIDs[row].text()
    self.selectedStudyRow = row
    self.progressMessage = "Getting available series for studyInstanceUID: " + self.selectedStudy
    self.showStatus(self.progressMessage)
    cacheFile = self.cachePath + self.selectedStudy + '.json'
    if os.path.isfile(cacheFile) and self.useCacheFlag:
      f = codecs.open(cacheFile, 'rb', encoding='utf8')
      responseString = f.read()[:]
      f.close()
      self.populateSeriesTableWidget(responseString)
      self.clearStatus()
      if self.numberOfSelectedStudies == 1:
        groupBoxTitle = 'Series (Accessed: ' + time.ctime(os.path.getmtime(cacheFile)) + ')'
      else:
        groupBoxTitle = 'Series '

      self.seriesCollapsibleGroupBox.setTitle(groupBoxTitle)

    else:
      self.progressMessage = "Getting available series for studyInstanceUID: " + self.selectedStudy
      self.showStatus(self.progressMessage)
      try:
        response = self.TCIAClient.get_series(studyInstanceUID=self.selectedStudy)
        responseString = json.dumps(response).encode("utf-8")
        # responseString = response.read()[:]
        with open(cacheFile, 'wb') as outputFile:
          # outputFile.write(responseString)
          outputFile.write(responseString)
          outputFile.close()
        self.populateSeriesTableWidget(responseString)

        if self.numberOfSelectedStudies == 1:
          groupBoxTitle = 'Series (Accessed: ' + time.ctime(os.path.getmtime(cacheFile)) + ')'
        else:
          groupBoxTitle = 'Series '

        self.seriesCollapsibleGroupBox.setTitle(groupBoxTitle)
        self.clearStatus()

      except Exception as error:
        self.clearStatus()
        message = "studySelected: Error in getting response from TCIA server.\nHTTP Error:\n" + str(error)
        qt.QMessageBox.critical(slicer.util.mainWindow(),
                    'TCIA Browser', message, qt.QMessageBox.Ok)

    self.onSeriesSelectAllButton()
    # self.loadButton.enabled = True
    # self.indexButton.enabled = True

  def seriesSelected(self):
    self.imagesToDownloadCount = 0
    self.loadButton.enabled = False
    self.indexButton.enabled = False
    for n in range(len(self.seriesInstanceUIDs)):
      if self.seriesInstanceUIDs[n].isSelected():
        self.imagesToDownloadCount += int(self.imageCounts[n].text())
        self.loadButton.enabled = True
        self.indexButton.enabled = True
    self.imagesCountLabel.text = 'No. of images to download: ' + '<span style=" font-size:8pt; font-weight:600; color:#aa0000;">' + str(
      self.imagesToDownloadCount) + '</span>' + ' '

  def onIndexButton(self):
    self.loadToScene = False
    self.addSelectedToDownloadQueue()
    # self.addFilesToDatabase()

  def onLoadButton(self):
    self.loadToScene = True
    self.addSelectedToDownloadQueue()

  def onCancelDownloadButton(self):
    self.cancelDownload = True
    for series in self.downloadQueue.keys():
      self.removeDownloadProgressBar(series)
    downloadQueue = {}
    seriesRowNumber = {}

  def addFilesToDatabase(self, seriesUID):
    self.progressMessage = "Adding Files to DICOM Database "
    self.showStatus(self.progressMessage)
    dicomWidget = slicer.modules.dicom.widgetRepresentation().self()

    indexer = ctk.ctkDICOMIndexer()
    # DICOM indexer uses the current DICOM database folder as the basis for relative paths,
    # therefore we must convert the folder path to absolute to ensure this code works
    # even when a relative path is used as self.extractedFilesDirectory.
    indexer.addDirectory(slicer.dicomDatabase, os.path.abspath(self.extractedFilesDirectory))
    indexer.waitForImportFinished()
    self.clearStatus()

  def addSelectedToDownloadQueue(self):
    DICOM.DICOMFileDialog.createDefaultDatabase()
    self.cancelDownload = False
    allSelectedSeriesUIDs = []
    downloadQueue = {}
    self.seriesRowNumber = {}
    self.downloadQueue = {}
    refSeriesList = []
    for n in range(len(self.seriesInstanceUIDs)):
      # print self.seriesInstanceUIDs[n]
      if self.seriesInstanceUIDs[n].isSelected():
        selectedCollection = self.selectedCollection
        selectedPatient = self.selectedPatient
        selectedStudy = self.selectedStudy
        selectedSeries = self.seriesInstanceUIDs[n].text()
        allSelectedSeriesUIDs.append(selectedSeries)
        # selectedSeries = self.selectedSeriesUIdForDownload
        self.selectedSeriesNicknamesDic[selectedSeries] = str(selectedPatient
                                    ) + '-' + str(
          self.selectedStudyRow + 1) + '-' + str(n + 1)

        # create download queue
        if not any(selectedSeries == s for s in self.previouslyDownloadedSeries):
          # check if selected is an RTSTRUCT or SEG file
          if self.modalities[n].text() in ["RTSTRUCT", "SEG"]:                          
              refSeries, refSeriesSize = self.TCIAClient.get_seg_ref_series(seriesInstanceUid = selectedSeries)
              # check if the reference series is also selected or is already downloaded
              if not self.seriesTableWidget.findItems(refSeries, qt.Qt.MatchExactly)[0].isSelected() and not any(refSeries == r for r in self.previouslyDownloadedSeries) and refSeries not in refSeriesList:
                  message = f"Your selection {selectedSeries} is an RTSTRUCT or SEG file and it seems you have not either downloaded or added the reference series {refSeries} to download, do you wish to download it as well?"
                  choice = qt.QMessageBox.warning(slicer.util.mainWindow(), 'TCIA Browser', message, qt.QMessageBox.Yes | qt.QMessageBox.No)
                  if (choice == qt.QMessageBox.Yes): 
                      allSelectedSeriesUIDs.append(refSeries)
                      refSeriesList.append(refSeries)
                      downloadFolderPath = os.path.join(self.storagePath, selectedSeries) + os.sep
                      self.downloadQueue[refSeries] = [downloadFolderPath, refSeriesSize]
                      # check if the reference series is in the same table
                      if len(self.seriesTableWidget.findItems(refSeries, qt.Qt.MatchExactly)) != 0:
                          refRow = self.seriesTableWidget.row(self.seriesTableWidget.findItems(refSeries, qt.Qt.MatchExactly)[0])
                          self.selectedSeriesNicknamesDic[refSeries] = str(selectedPatient) + '-' + str(self.selectedStudyRow + 1) + '-' + str(refRow + 1)
                          self.makeDownloadProgressBar(refSeries, refRow)
                          self.seriesRowNumber[refSeries] = refRow
          
          downloadFolderPath = os.path.join(self.storagePath, selectedSeries) + os.sep
          self.makeDownloadProgressBar(selectedSeries, n)
          self.downloadQueue[selectedSeries] = [downloadFolderPath, self.fileSizes[n].text()]
          self.seriesRowNumber[selectedSeries] = n
            
    self.downloadQueue = dict(reversed(self.downloadQueue.items()))
    self.seriesTableWidget.clearSelection()
    self.patientsTableWidget.enabled = False
    self.studiesTableWidget.enabled = False
    self.collectionSelector.enabled = False
    self.downloadSelectedSeries()

    if self.loadToScene:
      availablePlugins = list(slicer.modules.dicomPlugins)
      for seriesUID in allSelectedSeriesUIDs:
        if any(seriesUID == s for s in self.previouslyDownloadedSeries):
          self.progressMessage = "Examine Files to Load"
          self.showStatus(self.progressMessage)
          if slicer.dicomDatabase.fieldForSeries("Modality", seriesUID) == ("RTSTRUCT"):
              if not "DicomRtImportExportPlugin" in availablePlugins:
                self.progressMessage = "It appears that SlicerRT extension is not installed or enabled, skipping series: " + seriesUID
                self.showStatus(self.progressMessage)
                continue
              plugin = slicer.modules.dicomPlugins["DicomRtImportExportPlugin"]()
          elif slicer.dicomDatabase.fieldForSeries("Modality", seriesUID) == ("SEG"):
              if not "DICOMSegmentationPlugin" in availablePlugins:
                self.progressMessage = "It appears that QuantitativeReporting extension is not installed or enabled, skipping series: " + seriesUID
                self.showStatus(self.progressMessage)
                continue
              plugin = slicer.modules.dicomPlugins["DICOMSegmentationPlugin"]()
          else:
              plugin = slicer.modules.dicomPlugins["DICOMScalarVolumePlugin"]()
          seriesUID = seriesUID.replace("'", "")
          dicomDatabase = slicer.dicomDatabase
          fileList = slicer.dicomDatabase.filesForSeries(seriesUID)
          loadables = plugin.examine([fileList])
          self.clearStatus()
          volume = plugin.load(loadables[0])
      self.browserWidget.close()

  def downloadSelectedSeries(self):
    while self.downloadQueue and not self.cancelDownload:
      self.cancelDownloadButton.enabled = True
      selectedSeries, [downloadFolderPath, seriesSize] = self.downloadQueue.popitem()
      seriesSize = 0.01 if seriesSize == "< 0.01" else float(seriesSize)
      if not os.path.exists(downloadFolderPath):
        logging.debug("Creating directory to keep the downloads: " + downloadFolderPath)
        os.makedirs(downloadFolderPath)
      # save series uid in a text file for further reference
      # with open(downloadFolderPath + 'seriesUID.txt', 'w') as f:
        # f.write(selectedSeries)
        # f.close()
      fileName = downloadFolderPath + 'images.zip'
      logging.debug("Downloading images to " + fileName)
      self.extractedFilesDirectory = downloadFolderPath + 'images'
      self.progressMessage = "Downloading Images for series InstanceUID: " + selectedSeries
      self.showStatus(self.progressMessage)
      logging.debug(self.progressMessage)
      try:
        response = self.TCIAClient.get_image(seriesInstanceUid=selectedSeries)
        slicer.app.processEvents()
        # Save server response as images.zip in current directory
        if response.getcode() == 200:
          destinationFile = open(fileName, "wb")
          status = self.__bufferReadWrite(destinationFile, response, selectedSeries, seriesSize)

          destinationFile.close()
          logging.debug("Downloaded file %s from the TCIA server" % fileName)
          self.clearStatus()
          if status:
            self.progressMessage = "Extracting Images"
            logging.debug("Extracting images")
            # Unzip the data
            self.showStatus(self.progressMessage)
            totalItems = self.unzip(fileName, self.extractedFilesDirectory)
            if totalItems == 0:
              qt.QMessageBox.critical(slicer.util.mainWindow(),
                          'TCIA Browser',
                          "Failed to retrieve images for series %s. Please report this message to the developers!" % selectedSeries,
                          qt.QMessageBox.Ok)
            self.clearStatus()
            # Import the data into dicomAppWidget and open the dicom browser
            self.addFilesToDatabase(selectedSeries)
            #
            self.previouslyDownloadedSeries.append(selectedSeries)
            with open(self.downloadedSeriesArchiveFile, 'wb') as f:
              pickle.dump(self.previouslyDownloadedSeries, f)
            f.close()
            n = self.seriesRowNumber[selectedSeries]
            table = self.seriesTableWidget
            item = table.item(n, 1)
            item.setIcon(self.storedlIcon)
          else:
            logging.error("Failed to download images!")
            self.removeDownloadProgressBar(selectedSeries)
            self.downloadQueue.pop(selectedSeries, None)

          os.remove(fileName)

        else:
          self.clearStatus()
          logging.error("downloadSelectedSeries: Error getting image: " + str(response.getcode))  # print error code

      except Exception as error:
        self.clearStatus()
        message = "downloadSelectedSeries: Error in getting response from TCIA server.\nHTTP Error:\n" + str(error)
        qt.QMessageBox.critical(slicer.util.mainWindow(),
                    'TCIA Browser', message, qt.QMessageBox.Ok)
    self.cancelDownloadButton.enabled = False
    self.collectionSelector.enabled = True
    self.patientsTableWidget.enabled = True
    self.studiesTableWidget.enabled = True

  def makeDownloadProgressBar(self, selectedSeries, n):
    downloadProgressBar = qt.QProgressBar()
    self.downloadProgressBars[selectedSeries] = downloadProgressBar
    titleLabel = qt.QLabel(selectedSeries)
    progressLabel = qt.QLabel(self.selectedSeriesNicknamesDic[selectedSeries] + ' (0 KB)')
    self.downloadProgressLabels[selectedSeries] = progressLabel
    table = self.seriesTableWidget
    table.setCellWidget(n, 1, downloadProgressBar)
    # self.downloadFormLayout.addRow(progressLabel,downloadProgressBar)

  def removeDownloadProgressBar(self, selectedSeries):
    n = self.seriesRowNumber[selectedSeries]
    table = self.seriesTableWidget
    table.setCellWidget(n, 1, None)
    self.downloadProgressBars[selectedSeries].deleteLater()
    del self.downloadProgressBars[selectedSeries]
    self.downloadProgressLabels[selectedSeries].deleteLater()
    del self.downloadProgressLabels[selectedSeries]

  def stringBufferReadWrite(self, dstFile, response, bufferSize=819):
    response = json.dumps(response).encode("utf-8")
    self.downloadSize = 0
    while 1:
      #
      # If DOWNLOAD FINISHED
      #
      buffer = response[self.downloadSize:self.downloadSize + bufferSize]
      # buffer = response.read(bufferSize)[:]
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

  # This part was adopted from XNATSlicer module
  def __bufferReadWrite(self, dstFile, response, selectedSeries, seriesSize, bufferSize=8192):

    currentDownloadProgressBar = self.downloadProgressBars[selectedSeries]
    currentProgressLabel = self.downloadProgressLabels[selectedSeries]

    # Define the buffer read loop
    self.downloadSize = 0
    while 1:
      # If DOWNLOAD FINISHED
      buffer = response.read(bufferSize)
      slicer.app.processEvents()
      if not buffer:
        # Pop from the queue
        currentDownloadProgressBar.setMaximum(100)
        currentDownloadProgressBar.setValue(100)
        # currentDownloadProgressBar.setVisible(False)
        # currentProgressLabel.setVisible(False)
        self.removeDownloadProgressBar(selectedSeries)
        self.downloadQueue.pop(selectedSeries, None)
        break
      if self.cancelDownload:
        return False

      # Otherwise, Write buffer chunk to file
      slicer.app.processEvents()
      dstFile.write(buffer)
      #
      # And update progress indicators
      #
      self.downloadSize += len(buffer)
      currentDownloadProgressBar.setValue(self.downloadSize / seriesSize * 100)
      # currentDownloadProgressBar.setMaximum(0)
      currentProgressLabel.text = self.selectedSeriesNicknamesDic[
                      selectedSeries] + ' (' + str(int(self.downloadSize / 1024)
                                     ) + ' of ' + str(
        int(seriesSize / 1024)) + " KB)"
    # return self.downloadSize
    return True

  def unzip(self, sourceFilename, destinationDir):
    totalItems = 0
    with zipfile.ZipFile(sourceFilename) as zf:
      for member in zf.infolist():
        logging.debug("Found item %s in archive" % member.filename)
        words = member.filename.split('/')
        path = destinationDir
        for word in words[:-1]:
          drive, word = os.path.splitdrive(word)
          head, word = os.path.split(word)
          if word in (os.curdir, os.pardir, ''): continue
          path = os.path.join(path, word)
        logging.debug("Extracting %s" % words[-1])
        zf.extract(member, path)
        try:
          dcm = pydicom.read_file(os.path.join(path,words[-1]))
          totalItems = totalItems + 1
        except:
          pass
    logging.debug("Total %i DICOM items extracted from image archive." % totalItems)
    return totalItems

  def populateCollectionsTreeView(self, responseString):
    collections = responseString
    # populate collection selector
    n = 0
    self.collectionSelector.disconnect('currentIndexChanged(QString)')
    self.collectionSelector.clear()
    self.collectionSelector.connect('currentIndexChanged(QString)', self.collectionSelected)

    collectionNames = []
    for collection in collections:
      collectionNames.append(collection['Collection'])
    collectionNames.sort()

    for name in collectionNames:
      self.collectionSelector.addItem(name)

  def populatePatientsTableWidget(self, responseString):
    self.clearPatientsTableWidget()
    table = self.patientsTableWidget
    patients = responseString
    table.setRowCount(len(patients))
    n = 0
    for patient in patients:
      keys = patient.keys()
      for key in keys:
        if key == 'PatientId':
          patientIDString = str(patient['PatientId'])
          patientID = qt.QTableWidgetItem(patientIDString)
          self.patientsIDs.append(patientID)
          table.setItem(n, 0, patientID)
          if patientIDString[0:4] == 'TCGA':
            patientID.setIcon(self.reportIcon)
        if key == 'PatientSex':
          patientSex = qt.QTableWidgetItem(str(patient['PatientSex']))
          self.patientSexes.append(patientSex)
          table.setItem(n, 1, patientSex)
        if key == 'Phantom':
          phantom = qt.QTableWidgetItem(str(patient['Phantom']))
          self.phantoms.append(phantom)
          table.setItem(n, 2, phantom)
        if key == 'SpeciesDescription':
          speciesDescription = qt.QTableWidgetItem(str(patient['SpeciesDescription']))
          self.speciesDescriptions.append(speciesDescription)
          table.setItem(n, 3, speciesDescription)
      n += 1
    self.patientsTableWidget.resizeColumnsToContents()
    self.patientsTableWidgetHeader.setStretchLastSection(True)

  def populateStudiesTableWidget(self, responseString):
    self.studiesSelectAllButton.enabled = True
    self.studiesSelectNoneButton.enabled = True
    self.clearStudiesTableWidget()
    table = self.studiesTableWidget
    studies = json.loads(responseString)
    n = self.studiesTableRowCount
    table.setRowCount(n + len(studies))

    for study in studies:
      keys = study.keys()
      for key in keys:
        if key == 'StudyInstanceUID':
          studyInstanceUID = qt.QTableWidgetItem(str(study['StudyInstanceUID']))
          self.studyInstanceUIDs.append(studyInstanceUID)
          table.setItem(n, 0, studyInstanceUID)
        if key == 'StudyDate':
          studyDate = qt.QTableWidgetItem(str(study['StudyDate']))
          self.studyDates.append(studyDate)
          table.setItem(n, 1, studyDate)
        if key == 'StudyDescription':
          studyDescription = qt.QTableWidgetItem(str(study['StudyDescription']))
          self.studyDescriptions.append(studyDescription)
          table.setItem(n, 2, studyDescription)
        if key == 'PatientAge':
          patientAge = qt.QTableWidgetItem(str(study['PatientAge']))
          self.patientAges.append(patientAge)
          table.setItem(n, 3, patientAge)
        if key == 'LongitudinalTemporalEventType':
          longitudinalTemporalEventType = qt.QTableWidgetItem(str(study['LongitudinalTemporalEventType']))
          self.longitudinalTemporalEventTypes.append(longitudinalTemporalEventType)
          table.setItem(n, 4, longitudinalTemporalEventType)
        if key == 'LongitudinalTemporalOffsetFromEvent':
          longitudinalTemporalOffsetFromEvent = qt.QTableWidgetItem(str(study['LongitudinalTemporalOffsetFromEvent']))
          self.longitudinalTemporalOffsetFromEvents.append(longitudinalTemporalOffsetFromEvent)
          table.setItem(n, 5, longitudinalTemporalOffsetFromEvent)
        if key == 'SeriesCount':
          seriesCount = qt.QTableWidgetItem(str(study['SeriesCount']))
          self.seriesCounts.append(seriesCount)
          table.setItem(n, 6, seriesCount)
      n += 1
    self.studiesTableWidget.resizeColumnsToContents()
    self.studiesTableWidgetHeader.setStretchLastSection(True)
    self.studiesTableRowCount = n

  def populateSeriesTableWidget(self, responseString):
    self.clearSeriesTableWidget()
    table = self.seriesTableWidget
    seriesCollection = json.loads(responseString)
    self.seriesSelectAllButton.enabled = True
    self.seriesSelectNoneButton.enabled = True
    
    n = self.seriesTableRowCount
    table.setRowCount(n + len(seriesCollection))
    
    for series in seriesCollection:
      keys = series.keys()
      for key in keys:
        if key == 'SeriesInstanceUID':
          seriesInstanceUID = str(series['SeriesInstanceUID'])
          seriesInstanceUIDItem = qt.QTableWidgetItem(seriesInstanceUID)
          self.seriesInstanceUIDs.append(seriesInstanceUIDItem)
          table.setItem(n, 0, seriesInstanceUIDItem)
          if any(seriesInstanceUID == s for s in self.previouslyDownloadedSeries):
            self.removeSeriesAction.enabled = True
            icon = self.storedlIcon
          else:
            icon = self.downloadIcon
          downloadStatusItem = qt.QTableWidgetItem(str(''))
          downloadStatusItem.setTextAlignment(qt.Qt.AlignCenter)
          downloadStatusItem.setIcon(icon)
          self.downloadStatusCollection.append(downloadStatusItem)
          table.setItem(n, 1, downloadStatusItem)
        if key == 'SeriesDescription':
          seriesDescription = qt.QTableWidgetItem(str(series['SeriesDescription']))
          self.seriesDescriptions.append(seriesDescription)
          table.setItem(n, 2, seriesDescription)
        if key == 'SeriesNumber':
          seriesNumber = qt.QTableWidgetItem(str(series['SeriesNumber']))
          self.seriesNumbers.append(seriesNumber)
          table.setItem(n, 3, seriesNumber)
        if key == 'Modality':
          modality = qt.QTableWidgetItem(str(series['Modality']))
          self.modalities.append(modality)
          table.setItem(n, 4, modality)
        if key == 'BodyPartExamined':
          bodyPartExamined = qt.QTableWidgetItem(str(series['BodyPartExamined']))
          self.bodyPartsExamined.append(bodyPartExamined)
          table.setItem(n, 5, bodyPartExamined)
        if key == 'ProtocolName':
          protocolName = qt.QTableWidgetItem(str(series['ProtocolName']))
          self.protocolNames.append(protocolName)
          table.setItem(n, 6, protocolName)
        if key == 'Manufacturer':
          manufacturer = qt.QTableWidgetItem(str(series['Manufacturer']))
          self.manufacturers.append(manufacturer)
          table.setItem(n, 7, manufacturer)
        if key == 'ManufacturerModelName':
          manufacturerModelName = qt.QTableWidgetItem(str(series['ManufacturerModelName']))
          self.manufacturerModelNames.append(manufacturerModelName)
          table.setItem(n, 8, manufacturerModelName)
        if key == 'ImageCount':
          imageCount = qt.QTableWidgetItem(str(series['ImageCount']))
          self.imageCounts.append(imageCount)
          table.setItem(n, 9, imageCount)
        if key == 'FileSize':
          fileSizeConversion = "< 0.01" if str(round(series['FileSize']/1048576, 2)) == "0.0" else str(round(series['FileSize']/1048576, 2))
          fileSize = qt.QTableWidgetItem(fileSizeConversion)
          self.fileSizes.append(fileSize)
          table.setItem(n, 10, fileSize)
        if key == 'LicenseURI':
          licenseURI = qt.QTableWidgetItem(str(series['LicenseURI']))
          self.licenseURIs.append(licenseURI)
          table.setItem(n, 11, licenseURI)
      n += 1
    self.seriesTableWidget.resizeColumnsToContents()
    self.seriesTableRowCount = n
    self.seriesTableWidgetHeader.setStretchLastSection(True)

  def clearPatientsTableWidget(self):
    self.patientsTableWidget.horizontalHeader().setSortIndicator(-1, qt.Qt.AscendingOrder)
    table = self.patientsTableWidget
    self.patientsCollapsibleGroupBox.setTitle('Patients')
    self.patientsIDs = []
    self.phantoms = []
    self.patientSexes = []
    self.speciesDescriptions = []
    # self.collections = []
    table.setRowCount(0)
    table.clearContents()
    table.setHorizontalHeaderLabels(self.patientsTableHeaderLabels)

  def clearStudiesTableWidget(self):
    self.studiesTableWidget.horizontalHeader().setSortIndicator(-1, qt.Qt.AscendingOrder)
    self.studiesTableRowCount = 0
    table = self.studiesTableWidget
    self.studiesCollapsibleGroupBox.setTitle('Studies')
    self.studyInstanceUIDs = []
    self.studyDates = []
    self.studyDescriptions = []
    self.patientAges = []
    self.longitudinalTemporalEventTypes = []
    self.longitudinalTemporalOffsetFromEvents = []
    self.seriesCounts = []
    table.setRowCount(0)
    table.clearContents()
    table.setHorizontalHeaderLabels(self.studiesTableHeaderLabels)

  def clearSeriesTableWidget(self):
    self.seriesTableWidget.horizontalHeader().setSortIndicator(-1, qt.Qt.AscendingOrder)
    self.seriesTableRowCount = 0
    table = self.seriesTableWidget
    self.seriesCollapsibleGroupBox.setTitle('Series')
    self.seriesInstanceUIDs = []
    self.downloadStatusCollection = []
    self.seriesDescriptions = []
    self.seriesNumbers = []
    self.modalities = []
    self.bodyPartsExamined = []
    self.protocolNames = []
    self.manufacturers = []
    self.manufacturerModelNames = []
    self.imageCounts = []
    self.fileSizes = []
    self.licenseURIs = []
    table.setRowCount(0)
    table.clearContents()
    table.setHorizontalHeaderLabels(self.seriesTableHeaderLabels)

  def onReload(self, moduleName="TCIABrowser"):
    """Generic reload method for any scripted module.
    ModuleWizard will subsitute correct default moduleName.
    """
    import imp, sys, os, slicer
    import time
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
      sys.path.insert(0, p)
    fp = open(filePath, "rb")
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
    self.showBrowserButton.enabled = True

  def onReloadAndTest(self, moduleName="TCIABrowser"):
    self.onReload()
    evalString = 'globals()["%s"].%sTest()' % (moduleName, moduleName)
    tester = eval(evalString)
    tester.runTest()


#
# TCIABrowserLogic
#

class TCIABrowserLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget
  """

  def __init__(self):
    pass

  def hasImageData(self, volumeNode):
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

  def delayDisplay(self, message, msec=1000):
    #
    # logic version of delay display
    #
    print(message)
    self.info = qt.QDialog()
    self.infoLayout = qt.QVBoxLayout()
    self.info.setLayout(self.infoLayout)
    self.label = qt.QLabel(message, self.info)
    self.infoLayout.addWidget(self.label)
    qt.QTimer.singleShot(msec, self.info.close)
    self.info.exec_()

  def takeScreenshot(self, name, description, type=-1):
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
    slicer.qMRMLUtils().qImageToVtkImageData(qimage, imageData)

    annotationLogic = slicer.modules.annotations.logic()
    annotationLogic.CreateSnapShot(name, description, type, self.screenshotScaleFactor, imageData)

  def run(self, inputVolume, outputVolume, enableScreenshots=0, screenshotScaleFactor=1):
    """
    Run the actual algorithm
    """

    self.delayDisplay('Running the aglorithm')

    self.enableScreenshots = enableScreenshots
    self.screenshotScaleFactor = screenshotScaleFactor

    self.takeScreenshot('TCIABrowser-Start', 'Start', -1)

    return True


class TCIABrowserTest(unittest.TestCase):
  """
  This is the test case for your scripted module.
  """

  def delayDisplay(self, message, msec=1000):
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
    self.label = qt.QLabel(message, self.info)
    self.infoLayout.addWidget(self.label)
    qt.QTimer.singleShot(msec, self.info.close)
    self.info.exec_()

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    import traceback
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.testBrowserDownloadAndLoad()

  def testBrowserDownloadAndLoad(self):
    self.delayDisplay("Starting the test")
    widget = TCIABrowserWidget(None)
    widget.getCollectionValues()
    browserWindow = widget.browserWidget
    collectionsCombobox = browserWindow.findChildren('QComboBox')[0]
    print('Number of collections: {}'.format(collectionsCombobox.count))
    if collectionsCombobox.count > 0:
      collectionsCombobox.setCurrentIndex(randint(0, collectionsCombobox.count - 1))
      currentCollection = collectionsCombobox.currentText
      if currentCollection != '':
        print('connected to the server successfully')
        print('current collection: {}'.format(currentCollection))

      tableWidgets = browserWindow.findChildren('QTableWidget')

      patientsTable = tableWidgets[0]
      if patientsTable.rowCount > 0:
        selectedRow = randint(0, patientsTable.rowCount - 1)
        selectedPatient = patientsTable.item(selectedRow, 0).text()
        if selectedPatient != '':
          print('selected patient: {}'.format(selectedPatient))
          patientsTable.selectRow(selectedRow)

        studiesTable = tableWidgets[1]
        if studiesTable.rowCount > 0:
          selectedRow = randint(0, studiesTable.rowCount - 1)
          selectedStudy = studiesTable.item(selectedRow, 0).text()
          if selectedStudy != '':
            print('selected study: {}'.format(selectedStudy))
            studiesTable.selectRow(selectedRow)

          seriesTable = tableWidgets[2]
          if seriesTable.rowCount > 0:
            selectedRow = randint(0, seriesTable.rowCount - 1)
            selectedSeries = seriesTable.item(selectedRow, 0).text()
            if selectedSeries != '':
              print('selected series to download: {}'.format(selectedSeries))
              seriesTable.selectRow(selectedRow)

            pushButtons = browserWindow.findChildren('QPushButton')
            for pushButton in pushButtons:
              toolTip = pushButton.toolTip
              if toolTip[16:20] == 'Load':
                loadButton = pushButton

            if loadButton != None:
              loadButton.click()
            else:
              print('could not find Load button')
    else:
      print("Test Failed. No collection found.")
    scene = slicer.mrmlScene
    self.assertEqual(scene.GetNumberOfNodesByClass('vtkMRMLScalarVolumeNode'), 1)
    self.delayDisplay('Browser Test Passed!')
