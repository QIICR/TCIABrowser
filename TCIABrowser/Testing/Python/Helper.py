import qt, json, os, zipfile,dicom
import unittest
import slicer
import TCIABrowserLib

class Helper(object):

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

  def downloadSeries(self, TCIAClient):
    # Get collections
    try:
      responseString = TCIAClient.get_collection_values().read()[:]
      collections = json.loads(responseString)
      collectionsCount = len(collections)
      print ('Number of available collection(s): %d.'%collectionsCount)
    except Exception, error:
      raise Exception('Failed to get the collections!')
      return False
    # Get patients
    slicer.app.processEvents()
    collection = 'TCGA-GBM'
    print('%s was chosen.'%collection)
    try:
      responseString = TCIAClient.get_patient(collection = collection).read()[:]
      patients = json.loads(responseString)
      patientsCount = len(patients)
      print ('Number of available patient(s): %d'%patientsCount)
    except Exception, error:
      raise Exception('Failed to get patient!')
      return False
    patient = 'TCGA-06-0119'
    print('%s was chosen.'%patient)
    # Get studies
    slicer.app.processEvents()
    try:
      responseString = TCIAClient.get_patient_study(patientId = patient).read()[:]
      studies = json.loads(responseString)
      studiesCount = len(studies)
      print ('Number of available study(ies): %d'%studiesCount)
    except Exception, error:
      raise Exception('Failed to get patient study!')
      return False
    study = studies[0]['StudyInstanceUID']
    print('%s was chosen.'%study)
    # Get series
    slicer.app.processEvents()
    try:
      responseString = TCIAClient.get_series(studyInstanceUID = study).read()[:]
      seriesCollection = json.loads(responseString)
      seriesCollectionCount = len(seriesCollection)
      print ('Number of available series: %d'%seriesCollectionCount)
    except Exception, error:
      raise Exception('Failed to get series!')
      return False
    series = seriesCollection[0]['SeriesInstanceUID']
    print('%s was chosen.'%series)
    try:
      responseString = TCIAClient.get_series_size(series).read()[:]
      jsonResponse = json.loads(responseString)
      size = float(jsonResponse[0]['TotalSizeInBytes'])/(1024**2)
      print 'total size in bytes: %.2f MB'%size
    except Exception, error:
      raise Exception('Failed to get series size!')
      return False
    fileName = './images.zip'
    try:
      response = TCIAClient.get_image(seriesInstanceUid = series)
      slicer.app.processEvents()
      # Save server response as images.zip in current directory
      if response.getcode() == 200:
        destinationFile = open(fileName, "wb")
        bufferSize = 1024*512
        print 'Downloading ',
        while 1:
          buffer = response.read(bufferSize)
          slicer.app.processEvents()
          if not buffer: 
            break
          destinationFile.write(buffer)
          print 'X',
        destinationFile.close()
        print '... [DONE]'
      with zipfile.ZipFile(fileName) as zf:
        zipTest = zf.testzip()
      zf.close()
      destinationDir = './images/'
      if zipTest == None:
        with zipfile.ZipFile(fileName) as zf:
          zf.extractall(destinationDir)
      else:
        raise Exception('The zip file was corrupted!')
        return False
      dicomDir = './images/files/'
      firstFileName = os.listdir(dicomDir)[0]
      print 'Reading downloaded dicom images ....'
      ds = dicom.read_file(dicomDir + firstFileName)
      print 'downloaded Patient ID:', ds.PatientID
      print 'downloaded Study Instance UID:', ds.StudyInstanceUID
      print 'downloaded Series Instance UID:', ds.SeriesInstanceUID
      if str(ds.StudyInstanceUID) != str(study) or str(ds.SeriesInstanceUID) != str(series):
        print 'downloaded uids are not the same as requested'
    except Exception, error:
      print error
      raise Exception('Failed to get image!')
      return False
    # Test Passed
    return True
