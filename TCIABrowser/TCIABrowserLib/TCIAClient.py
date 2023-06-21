import slicer, json, string, urllib.request, urllib.parse, urllib.error
    
try:
    slicer.util.pip_install('tcia_utils -U -q')
except:
    slicer.util.pip_install('tcia_utils')
import tcia_utils.nbia

#import TCIABrowserLib

#
# Refer https://wiki.cancerimagingarchive.net/display/Public/TCIA+Programmatic+Interface+REST+API+Guides for the API guide
#
class TCIAClient:
    def __init__(self, user = "nbia_guest", pw = "", nlst = False):
        self.apiKey = "" if not nlst else "nlst"
        if user != "nbia_guest" or self.apiKey == "nlst":
                tcia_utils.nbia.getToken(user, pw, self.apiKey)
                try:
                    if self.apiKey == "": tcia_utils.nbia.api_call_headers != None 
                    else: tcia_utils.nbia.nlst_api_call_headers != None 
                    self.exp_time = tcia_utils.nbia.token_exp_time if self.apiKey == "" else tcia_utils.nbia.nlst_token_exp_time
                except:
                    self.credentialError = "Please check your credential and try again.\nFor more information, check the Python console."

    def get_collection_values(self):
        return tcia_utils.nbia.getCollections(api_url = self.apiKey)
    
    def get_patient(self, collection = None):
        return tcia_utils.nbia.getPatient(collection, api_url = self.apiKey)

    def get_patient_study(self, collection = None, patientId = None, studyInstanceUid = None):
        return tcia_utils.nbia.getStudy(collection, patientId, studyInstanceUid, api_url = self.apiKey)
        
    def get_series(self, collection = None, patientId = None, studyInstanceUID = None, seriesInstanceUID = None, modality = None, 
                   bodyPartExamined = None, manufacturer = None, manufacturerModel = None):
        return tcia_utils.nbia.getSeries(collection, patientId, studyInstanceUID, seriesInstanceUID, modality, 
                                         bodyPartExamined, manufacturer, manufacturerModel, api_url = self.apiKey)

    def get_series_size(self, seriesInstanceUid):
        return tcia_utils.nbia.getSeriesSize(seriesInstanceUid, api_url = self.apiKey)

    def get_image(self, seriesInstanceUid):
        queryParameters = {"SeriesInstanceUID": seriesInstanceUid}
        url = tcia_utils.nbia.setApiUrl("getImage", self.apiKey) + "getImage?%s" % urllib.parse.urlencode(queryParameters)
        request = urllib.request.Request(url = url, headers = {"api_key" : self.apiKey})
        return urllib.request.urlopen(request)
    
    def logOut(self):
        tcia_utils.nbia.logoutToken(api_url = self.apiKey)