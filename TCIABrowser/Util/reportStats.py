from TCIAClient import *

def getTCIASummary(fileName):

  summaryFile = open(fileName,'w')

  tcia_client = TCIAClient()
  print('Connected')
  response = tcia_client.get_collection_values()
  collectionsStr = response.read()[:]
  collections = [c['Collection'] for c in json.loads(collectionsStr)]

  import datetime
  startTime = datetime.datetime.now()

  print 'Collection,PatientID,StudyID,Modality,ImageCount,Manufacturer,BodyPartExamined,AnnotationsFlag'

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
        # TODO: collect a spreadsheet with the stats on what is/pop available
        # in TCIA, make plots with R by modality, number of series, whatever
        # parameters of the series are available

        for ser in series:
          #summaryFile.write(c+','+p+','+s+','+ser['Modality']+','+int(ser['ImageCount'])+','+ser['Manufacturer']+','+int(ser['AnnotationsFlag'])+'\n')
          #print c,',',p,',',s,',',ser['Modality'],',',str(ser['ImageCount']),',',ser['Manufacturer']
          summaryFile.write(c+',')
          summaryFile.write(p+',')
          summaryFile.write(s+',')
          try:
            summaryFile.write(ser['Modality']+',')
          except:
            summaryFile.write('NA,')
          try:
            summaryFile.write(str(ser['ImageCount'])+',')
          except:
            summaryFile.write('NA,')
          try:
            summaryFile.write(ser['Manufacturer']+',')
          except:
            summaryFile.write('NA,')
          try:
            summaryFile.write(ser['BodyPartExamined']+',')
          except:
            summaryFile.write('NA,')
          try:
            summaryFile.write(ser['AnnotationsFlag']+'\n')
          except:
            summaryFile.write('NA\n')

        # generate 2 plots:
        # 1) summary of collections: # patients/series
        # 2) summary by modality: #patients/series per modality

    endTime = datetime.datetime.now()

    print "Started: ",startTime.isoformat()
    print "Finished: ",endTime.isoformat()
