import urllib,sys, os
import time
import csv
import  qt, ctk, slicer
from __main__ import vtk, qt, ctk, slicer

class clinicalDataPopup:
  def __init__(self,cachePath,icon):
    self.cachePath = cachePath
    self.window = qt.QWidget()
    self.window.setWindowTitle('Clinical Data (From cBioportal for Cancer Genomics)')
    self.window.setWindowIcon(icon)
    self.layout= qt.QVBoxLayout(self.window)
    self.setup()
    #self.progress = qt.QProgressDialog(self.window)
    #self.progress.setWindowTitle("Clinical Data")

  def setup(self):
    self.tableAreaWidget = qt.QWidget()
    self.layout.addWidget(self.tableAreaWidget)
    self.tableLayout= qt.QVBoxLayout(self.tableAreaWidget)
    label = qt.QLabel('Clinical Data')
    #self.tableLayout.addWidget(label)
    self.clinicalDataTableWidget = qt.QTableWidget()
    self.tableLayout.addWidget(self.clinicalDataTableWidget)
    verticalheader = self.clinicalDataTableWidget.verticalHeader()
    verticalheader.setDefaultSectionSize(20)

    self.buttonsWidget = qt.QWidget()
    self.buttonsLayout = qt.QHBoxLayout(self.buttonsWidget)
    self.layout.addWidget(self.buttonsWidget)

    self.accessLabel = qt.QLabel('')
    self.buttonsLayout.addWidget(self.accessLabel)
    self.buttonsLayout.addStretch(1)
    self.updateButton = qt.QPushButton('Update Cache')
    self.updateButton.toolTip = 'Connect to cBioPortal and update the data'
    self.buttonsLayout.addWidget(self.updateButton)

    self.closeButton= qt.QPushButton('Close')
    self.buttonsLayout.addWidget(self.closeButton)

    # Connections
    self.updateButton.connect('clicked(bool)', self.onUpdateButton)
    self.closeButton.connect('clicked(bool)', self.onCloseButton)

  def getData(self, collection, patient):
    self.onCloseButton()
    self.collection = collection
    self.patient = patient
    self.cacheFile = self.cachePath + collection+'.csv'
    if os.path.isfile(self.cacheFile):
      self.readResponseCSVFile(self.cacheFile)
    else:
      self.requestClinicalData(self.cacheFile)

  def readResponseCSVFile(self,cacheFile):
    table = self.clinicalDataTableWidget
    self.tableItems = []
    table.clear()
    accessLabelText = 'Accessed: '+ time.ctime(os.path.getmtime(self.cacheFile))
    self.accessLabel.setText(accessLabelText)
    data = []
    data = list(csv.reader(open(self.cacheFile, 'rb'), delimiter='\t'))
    headers = data[0]
    table.setRowCount(len(headers))
    table.setColumnCount(1)
    table.setVerticalHeaderLabels(headers)
    horizontalHeader = table.horizontalHeader()
    horizontalHeader.hide()
    horizontalHeader.setStretchLastSection(True)
    patient = None

    for row in data:
      for item in row:
        if self.patient in item:
          patient = row

    if patient != None:
      for index,item in enumerate(patient):
        tableItem = qt.QTableWidgetItem(str(item))
        table.setItem(index, 0, tableItem)
        self.tableItems.append(tableItem)
    else:
      message = "The Selected Patient is not in the list provided by cBioportal Server"
      qt.QMessageBox.critical(slicer.util.mainWindow(),
                        'TCIA Browser', message, qt.QMessageBox.Ok)
      print('patient not in the query')

  def open(self):
    if not self.window.isVisible():
      self.window.show()
    self.window.raise_()

  def onCloseButton(self):
    self.window.hide()

  def onUpdateButton(self):
    self.requestClinicalData(self.cacheFile)

  def requestClinicalData(self,cacheFile):
    if self.collection == 'TCGA-GBM':
      queryString = 'gbm_tcga_pub_all'
    elif self.collection == 'TCGA-BRCA':
      queryString = 'brca_tcga_pub_all'
    elif self.collection == 'TCGA-LGG':
      queryString = 'lgg_tcga_all'
    elif self.collection == 'TCGA-KIRC':
      queryString = 'kirc_tcga_pub_all'
    elif self.collection == 'TCGA-LUAD':
      queryString = 'luad_tcga_all'
    elif self.collection == 'TCGA-PRAD':
      queryString = 'prad_tcga_all'
    elif self.collection == 'TCGA-LIHC':
      queryString = 'lihc_tcga_all'
    elif self.collection == 'TCGA-KIRP':
      queryString = 'kirp_tcga_all'
    elif self.collection == 'TCGA-OV':
      queryString = 'ov_tcga_pub_all'
    elif self.collection == 'TCGA-HNSC':
      queryString = 'hnsc_tcga_all'
    self.progressMessage = "Please wait while retreiving information from cBioportal for Cancer Genomics server."
    #self.showProgress(self.progressMessage)
    try:

      url = 'http://www.cbioportal.org/public-portal/webservice.do?cmd=getClinicalData&case_set_id='
      requestUrl = url + queryString
      request = urllib.request(url=requestUrl)
      response = urllib.request.urlopen(request)
      responseString = response.read()[:]
      if responseString[:7] == 'CASE_ID':
        with open(self.cacheFile, 'wb') as outputFile:
          outputFile.write(responseString)
          outputFile.close()
        self.readResponseCSVFile(self.cacheFile)
        self.closeProgress()
      else:
        self.closeProgress()
        message = "Error in getting response from cBioportal Server"
        qt.QMessageBox.critical(slicer.util.mainWindow(),
                        'TCIA Browser', message, qt.QMessageBox.Ok)
    except Exception as error:
      self.closeProgress()
      message = "Error in getting response from cBioportal Server"
      qt.QMessageBox.critical(slicer.util.mainWindow(),
                        'TCIA Browser', message, qt.QMessageBox.Ok)

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
