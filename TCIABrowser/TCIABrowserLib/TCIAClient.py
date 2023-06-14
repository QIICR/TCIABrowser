try:
    import tcia_utils.nbia
except:
    slicer.util.pip_install('tcia_utils')
    import tcia_utils.nbia

import json, string, urllib.request, urllib.parse, urllib.error
#import TCIABrowserLib

#
# Refer https://wiki.cancerimagingarchive.net/display/Public/TCIA+Programmatic+Interface+REST+API+Guides for the API guide
#
class TCIAClient:
    GET_IMAGE = "getImage"
    # GET_MANUFACTURER_VALUES = "getManufacturerValues"
    # GET_MODALITY_VALUES = "getModalityValues"
    GET_COLLECTION_VALUES = "getCollectionValues"
    # GET_BODY_PART_VALUES = "getBodyPartValues"
    GET_PATIENT_STUDY = "getPatientStudy"
    GET_SERIES = "getSeries"
    GET_SERIES_SIZE = "getSeriesSize"
    GET_PATIENT = "getPatient"

    # use Slicer API key by default
    def __init__(self, user = "nbia_guest", pw = ""):
        if user == "nbia_guest":
            self.apiKey = ""
        else:
            self.apiKey == "restricted"
            tcia_utils.nbia.getToken(user, pw, api_url = self.apiKey)
        self.baseUrl = "https://services.cancerimagingarchive.net/nbia-api/services/v1"

    def execute(self, url, queryParameters = {}):
        queryParameters = dict((k, v) for k, v in queryParameters.items() if v)
        headers = {"api_key" : self.apiKey}
        queryString = "?%s" % urllib.parse.urlencode(queryParameters)
        requestUrl = url + queryString
        request = urllib.request.Request(url = requestUrl , headers = headers)
        resp = urllib.request.urlopen(request)
        return resp

    # def get_modality_values(self, collection = None, bodyPartExamined = None, outputFormat = "json"):
    #     serviceUrl = self.baseUrl + "/" + self.GET_MODALITY_VALUES
    #     queryParameters = {"Collection": collection, "BodyPartExamined": bodyPartExamined, "format": outputFormat}
    #     resp = self.execute(serviceUrl, queryParameters)
    #     return resp

    # def get_manufacturer_values(self, collection = None, modality = None, bodyPartExamined = None, outputFormat = "json"):
    #     serviceUrl = self.baseUrl + "/" + self.GET_MANUFACTURER_VALUES
    #     queryParameters = {"Collection": collection, "Modality": modality, "BodyPartExamined": bodyPartExamined, "format": outputFormat}
    #     resp = self.execute(serviceUrl, queryParameters)
    #     return resp

    def get_collection_values(self, outputFormat = "json"):
        # serviceUrl = self.baseUrl + "/" + self.GET_COLLECTION_VALUES
        # queryParameters = {"format": outputFormat}
        # resp = self.execute(serviceUrl, queryParameters)
        # return resp
        return tcia_utils.nbia.getCollections(api_url = self.apiKey)

    # def get_body_part_values(self, collection = None, modality = None, outputFormat = "csv"):
    #     serviceUrl = self.baseUrl + "/" + self.GET_BODY_PART_VALUES
    #     queryParameters = {"Collection": collection, "Modality": modality, "format": outputFormat}
    #     resp = self.execute(serviceUrl, queryParameters)
    #     return resp

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
        serviceUrl = self.baseUrl + "/" + self.GET_IMAGE
        queryParameters = {"SeriesInstanceUID": seriesInstanceUid}
        resp = self.execute(serviceUrl, queryParameters)
        return resp