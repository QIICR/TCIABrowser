from TCIAClient import *

def getTCIASummary(fileName):

  # which attributes to keep track of
  seriesAttributes = ['SeriesInstanceUID','Modality','ProtocolName','SeriesDate','BodyPartExamined',\
      'AnnotationsFlag','Manufacturer','ImageCount']

  summaryFile = open(fileName,'w')

  tcia_client = TCIAClient()
  print('Connected')
  response = tcia_client.get_collection_values()
  collectionsStr = response.read()[:]
  collections = [c['Collection'] for c in json.loads(collectionsStr)]

  import datetime
  startTime = datetime.datetime.now()

  for attr in seriesAttributes:
    summaryFile.write(attr+',')
  summaryFile.write('\n')

  for c in collections:
    response = tcia_client.get_patient(collection=c)
    patientsStr = response.read()[:]
    patients = [p['PatientID'] for p in json.loads(patientsStr)]

    print 'Collection ',c,' (total of ',len(patients),' patients)'

    for p in patients:
      response = tcia_client.get_patient_study(collection=c,patientId=p)
      studiesStr = response.read()[:]
      studies = [s['StudyInstanceUID'] for s in json.loads(studiesStr)]

      print '  Patient ',p,' (total of ',len(studies),' studies)'
    
      for s in studies:
        response = tcia_client.get_series(collection=c,studyInstanceUID=s)
        seriesStr = response.read()[:]
        series = json.loads(seriesStr)
        print '   Study ',s,' (total of ',len(series),' series)'

        for ser in series:
          for attr in seriesAttributes:
            try:
              summaryFile.write(str(ser[attr])+',')
            except:
              summaryFile.write('NA,')
          summaryFile.write('\n')

    endTime = datetime.datetime.now()

    print "Started: ",startTime.isoformat()
    print "Finished: ",endTime.isoformat()
