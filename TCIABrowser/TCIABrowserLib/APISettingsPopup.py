from __main__ import vtk, qt, ctk, slicer

class APISettingsPopup:
  def __init__(self):
    self.window = qt.QWidget()
    self.window.setWindowTitle('API Settings')
    self.APISettingsPopupLayout = qt.QVBoxLayout(self.window)
    self.setup()
    self.numberOfRows = 0
    self.apiNameTableItems = []
    self.apiKeyTableItems = []
    self.makeSharedApiModalObjects()
    self.addAPIDialogBox = None
    self.deleteDialogBox = None
    self.populateAPITable()

  def setup(self):
    self.manageAPIsWidget = qt.QWidget()
    self.APISettingsPopupLayout.addWidget(self.manageAPIsWidget)
    self.manageAPIsLayout = qt.QVBoxLayout(self.manageAPIsWidget)
    label = qt.QLabel('Manage APIs')
    self.manageAPIsLayout.addWidget(label)

    self.apiTable = APITable()
    self.apiTable.connect('cellClicked(int,int)',self.apiSelected)
    self.manageAPIsLayout.addWidget(self.apiTable)

    self.manageButtonsWidget = qt.QWidget()
    self.manageButtonsLayout = qt.QHBoxLayout(self.manageButtonsWidget)
    self.manageAPIsLayout.addWidget(self.manageButtonsWidget)
    self.manageButtonsLayout.addStretch(1)

    self.addAPIButton = qt.QPushButton('Add')
    self.manageButtonsLayout.addWidget(self.addAPIButton)

    self.editAPIButton = qt.QPushButton('Edit')
    self.editAPIButton.enabled = False
    self.manageButtonsLayout.addWidget(self.editAPIButton)

    self.deleteAPIButton = qt.QPushButton('Delete')
    self.deleteAPIButton.enabled = False
    self.manageButtonsLayout.addWidget(self.deleteAPIButton)
    
    self.restartLabel = qt.QLabel('')
    self.restartLabel.setVisible(False)
    self.restartLabel.setText("<font color='red'>* Restart Required</font>")
    self.APISettingsPopupLayout.addWidget(self.restartLabel)

    self.APISettingsPopupButtonsWidget = qt.QWidget()
    self.APISettingsPopupButtonsLayout = qt.QHBoxLayout(self.APISettingsPopupButtonsWidget)
    self.APISettingsPopupButtonsLayout.addStretch(1)
    self.APISettingsPopupLayout.addWidget(self.APISettingsPopupButtonsWidget)

    self.doneButton = qt.QPushButton('Done')
    self.APISettingsPopupButtonsLayout.addWidget(self.doneButton)

    self.cancelButton = qt.QPushButton('Cancel')
    self.APISettingsPopupButtonsLayout.addWidget(self.cancelButton)

    # Connections
    self.addAPIButton.connect('clicked(bool)', self.onAddApiButton)
    self.editAPIButton.connect('clicked(bool)', self.onEditApiButton)
    self.deleteAPIButton.connect('clicked(bool)', self.onDeleteApiButton)
    self.doneButton.connect('clicked(bool)', self.onDoneButton)
    self.cancelButton.connect('clicked(bool)', self.onCancelButton)

  def open(self):
    if not self.window.isVisible():
      self.window.show()
    self.window.raise_()

  def onAddApiButton(self):
    self.dialogRole = 'Add'
    self.apiNameLineEdit.clear()
    self.apiKeyLineEdit.clear()
    self.showAddAPIModal()

  def onEditApiButton(self):
    self.dialogRole = 'Edit'
    self.showAddAPIModal()
    self.apiNameLineEdit.text = self.apiNameTableItems[self.currentAPIRow].text()
    self.apiKeyLineEdit.text = self.apiKeyTableItems[self.currentAPIRow].text()

  def onDeleteApiButton(self):
    if self.deleteDialogBox== None:
      self.deleteDialogBox= self.makeDeleteApiDialoge()
    self.deleteDialogBox.show()

  def onDoneButton(self):
    
    settings = qt.QSettings()
    table = self.apiTable
    settings.beginGroup("TCIABrowser/API-Keys")
    userApiNames = settings.childKeys()

    # remove all
    for userApi in userApiNames:
      settings.remove(userApi)
    settings.sync()

    # add modified 
    for api in range(0,self.numberOfRows):
      apiName = table.item(api,0).text()
      apiKey = table.item(api,1).text()
      settings.setValue(apiName,apiKey)
    settings.endGroup()
    self.window.hide()

  def onCancelButton(self):
    self.window.hide()

  def showAddAPIModal(self):
    if self.addAPIDialogBox== None:
      self.addAPIDialogBox= self.makeAddAPIDialog()
    self.addAPIDialogBox.show()

  def makeAddAPIDialog (self):

    self.apiNameLineEdit.clear()
    self.apiKeyLineEdit.clear()

    saveButton = qt.QPushButton("OK")
    cancelButton = qt.QPushButton("Cancel")

    currLayout = qt.QFormLayout()
    currLayout.addRow("API Name:", self.apiNameLineEdit)
    currLayout.addRow("API Key:", self.apiKeyLineEdit)

    buttonLayout = qt.QHBoxLayout()
    buttonLayout.addStretch(1)
    buttonLayout.addWidget(cancelButton)
    buttonLayout.addWidget(saveButton)

    masterForm = qt.QFormLayout()    
    masterForm.addRow(currLayout)
    masterForm.addRow(buttonLayout)

    addApiDialog = qt.QDialog(self.addAPIButton)
    addApiDialog.setWindowTitle("Add API")
    addApiDialog.setFixedWidth(300)
    addApiDialog.setLayout(masterForm)
    addApiDialog.setWindowModality(1)

    cancelButton.connect("clicked()", addApiDialog.hide)
    saveButton.connect("clicked()", self.saveApi)   
    
    return addApiDialog

  def makeDeleteApiDialoge(self):
    
    okButton = qt.QPushButton("OK")
    cancelButton = qt.QPushButton("Cancel")

    messageLabel = qt.QTextEdit()
    messageLabel.setReadOnly(True)
    messageLabel.insertPlainText("Are you sure you want to delete the selected API?") 
    messageLabel.setFontWeight(100)    
    messageLabel.setFixedHeight(40)
    messageLabel.setFrameShape(0)

    currLayout = qt.QVBoxLayout()
    currLayout.addWidget(messageLabel)
    #currLayout.addStretch(1)
    
    buttonLayout = qt.QHBoxLayout()
    buttonLayout.addStretch(1)
    buttonLayout.addWidget(cancelButton)
    buttonLayout.addWidget(okButton)
    
    masterForm = qt.QFormLayout()    
    masterForm.addRow(currLayout)
    masterForm.addRow(buttonLayout)

    deleteApiDialog = qt.QDialog(self.apiTable)
    deleteApiDialog.setWindowTitle("Delete API")
    deleteApiDialog.setLayout(masterForm)
    deleteApiDialog.setWindowModality(1)

    cancelButton.connect("clicked()", deleteApiDialog.hide)
    okButton.connect("clicked()", self.deleteApi) 
    
    return deleteApiDialog

  def saveApi(self):
    table = self.apiTable
    apiNameTableItem = qt.QTableWidgetItem(str(self.apiNameLineEdit.text))
    apiKeyTableItem = qt.QTableWidgetItem(str(self.apiKeyLineEdit.text))
    self.apiKeyTableItems.append(apiKeyTableItem)
    self.apiNameTableItems.append(apiNameTableItem)
    if self.dialogRole == 'Add':
      self.numberOfRows += 1
      table.setRowCount(self.numberOfRows)
      table.setItem(self.numberOfRows -1, 0, apiNameTableItem)
      table.setItem(self.numberOfRows -1, 1, apiKeyTableItem)
    elif self.dialogRole == 'Edit':
      table.setItem(self.currentAPIRow, 0, apiNameTableItem)
      table.setItem(self.currentAPIRow, 1, apiKeyTableItem)
    self.restartLabel.setVisible(True)

  def deleteApi(self):
    self.apiTable.removeRow(self.currentAPIRow)
    self.numberOfRows -= 1
    self.deleteDialogBox.hide()
    self.restartLabel.setVisible(True)

  def populateAPITable(self):

    settings = qt.QSettings()
    table = self.apiTable
    settings.beginGroup("TCIABrowser/API-Keys")
    userApiNames = settings.childKeys()
    self.numberOfRows = len(userApiNames)
    table.setRowCount(self.numberOfRows)
    row = 0
    for api in userApiNames:
      apiNameTableItem = qt.QTableWidgetItem(str(api))
      apiKeyTableItem = qt.QTableWidgetItem(str(settings.value(api)))
      table.setItem( row, 0, apiNameTableItem) 
      self.apiNameTableItems.append(apiNameTableItem)
      table.setItem( row, 1, apiKeyTableItem) 
      self.apiKeyTableItems.append(apiKeyTableItem)
      row += 1
    settings.endGroup()

  def makeSharedApiModalObjects(self):
    self.apiNameLineEdit = qt.QLineEdit()
    self.apiKeyLineEdit = qt.QLineEdit()

  def apiSelected(self,row,column):
    self.editAPIButton.enabled = True
    self.deleteAPIButton.enabled = True
    self.currentAPIRow = row
'''
class APITable(qt.QTableWidget):
  def __init__(self):
    super(APITable, self).__init__(self)
    
    self.addAPIDialogBox.hide()

  def populateTable(self):
    print 'populate api table'

  def makeSharedApiModalObjects(self):
    self.apiNameLineEdit = qt.QLineEdit()
    self.apiKeyLineEdit = qt.QLineEdit()

  def apiSelected(self,row,column):
    self.editAPIButton.enabled = True
    self.deleteAPIButton.enabled = True
    self.currentAPIRow = row
'''
class APITable(qt.QTableWidget):
  def __init__(self):
    super(APITable, self).__init__(self)
    self.setup()

  def setup(self):
    #--------------------
    # Setup columns.
    #--------------------
    self.setColumnCount(2)
    self.apiSettingsTableHeaderLabels = ['API Name', 'API Key']
    self.setHorizontalHeaderLabels(self.apiSettingsTableHeaderLabels)
    abstractItemView =qt.QAbstractItemView()
    self.setSelectionBehavior(abstractItemView.SelectRows) 
    apiSettingsTableWidgetHeader = self.horizontalHeader()
    apiSettingsTableWidgetHeader.setStretchLastSection(True)
