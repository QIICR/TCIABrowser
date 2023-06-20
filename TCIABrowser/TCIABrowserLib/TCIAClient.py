import slicer, json, string, urllib.request, urllib.parse, urllib.error

try:
    import tcia_utils.nbia
except:
    slicer.util.pip_install('tcia_utils')
    import tcia_utils.nbia

#import TCIABrowserLib

#
# Refer https://wiki.cancerimagingarchive.net/display/Public/TCIA+Programmatic+Interface+REST+API+Guides for the API guide
#
class TCIAClient:
    def __init__(self, user = "", pw = ""):
        if user == "nbia_guest":
            self.apiKey = ""
        elif user == "nlst":
            try:
                tcia_utils.nbia.getToken(user, pw, api_url = "nlst")
                self.apiKey = "nlst"
                self.exp_time = tcia_utils.nbia.nlst_token_exp_time
            except:
                self.credentialError = "Please check your credential and try again.\nFor more information, check the Python console."
        else:
            tcia_utils.nbia.getToken(user, pw, api_url = "")
            try:
                tcia_utils.nbia.api_call_headers != None
                self.apiKey = ""
                self.exp_time = tcia_utils.nbia.token_exp_time
            except:
                self.credentialError = "Please check your credential and try again.\nFor more information, check the Python console."

    def execute(self, url, queryParameters = {}):
        queryParameters = dict((k, v) for k, v in queryParameters.items() if v)
        headers = {"api_key" : self.apiKey}
        queryString = "?%s" % urllib.parse.urlencode(queryParameters)
        requestUrl = url + queryString
        request = urllib.request.Request(url = requestUrl , headers = headers)
        resp = urllib.request.urlopen(request)
        return resp

    def get_collection_values(self, outputFormat = "json"):
        # serviceUrl = self.baseUrl + "/" + self.GET_COLLECTION_VALUES
        # queryParameters = {"format": outputFormat}
        # resp = self.execute(serviceUrl, queryParameters)
        # return resp
        return tcia_utils.nbia.getCollections(api_url = self.apiKey)

    def get_patient_study(self, collection = None, patientId = None, studyInstanceUid = None, outputFormat = "json"):
        # serviceUrl = self.baseUrl + "/" + self.GET_PATIENT_STUDY
        # queryParameters = {"Collection": collection, "PatientID": patientId, "StudyInstanceUID": studyInstanceUid, "format": outputFormat}
        # resp = self.execute(serviceUrl, queryParameters)
        # return resp
        return tcia_utils.nbia.getStudy(collection, patientId, studyInstanceUid, api_url = self.apiKey)
        
    def get_series(self, collection = None, patientId = None, studyInstanceUID = None, seriesInstanceUID = None, modality = None, 
                   bodyPartExamined = None, manufacturer = None, manufacturerModel = None, outputFormat = "json"):
        # serviceUrl = self.baseUrl + "/" + self.GET_SERIES
        # queryParameters = {"Collection": collection, "PatientID": patientId, "StudyInstanceUID": studyInstanceUID, 
        #                    "SeriesInstanceUID": seriesInstanceUID, "Modality": modality, "BodyPartExamined": bodyPartExamined, 
        #                    "Manufacturer": manufacturer, "ManufacturerModelName": manufacturerModel, "format": outputFormat}
        # resp = self.execute(serviceUrl, queryParameters)
        # return resp
        return tcia_utils.nbia.getSeries(collection, patientId, studyInstanceUID, seriesInstanceUID, modality, 
                                         bodyPartExamined, manufacturer, manufacturerModel, api_url = self.apiKey)

    def get_series_size(self, seriesInstanceUid):
        # serviceUrl = self.baseUrl + "/" + self.GET_SERIES_SIZE
        # queryParameters = {"SeriesInstanceUID": seriesInstanceUid}
        # resp = self.execute(serviceUrl, queryParameters)
        # return resp
        return tcia_utils.nbia.getSeriesSize(seriesInstanceUid, api_url = self.apiKey)

    def get_patient(self, collection = None, outputFormat = "json"):
        # serviceUrl = self.baseUrl + "/" + self.GET_PATIENT
        # queryParameters = {"Collection": collection, "format": outputFormat}
        # resp = self.execute(serviceUrl, queryParameters)
        # return resp
        return tcia_utils.nbia.getPatient(collection, api_url = self.apiKey)

    def get_image(self, seriesInstanceUid):
        serviceUrl = tcia_utils.nbia.setApiUrl("getImage", self.apiKey) + "getImage"
        queryParameters = {"SeriesInstanceUID": seriesInstanceUid}
        resp = self.execute(serviceUrl, queryParameters)
        return resp