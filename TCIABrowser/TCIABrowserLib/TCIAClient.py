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
        if nlst: self.apiKey = "nlst"
        elif user == "nbia_guest": self.apiKey = ""
        else: self.apiKey = "restricted"
        if self.apiKey == "nlst" or self.apiKey == "restricted":
                tcia_utils.nbia.getToken(user, pw, self.apiKey)
                try:
                    if self.apiKey == "restricted": tcia_utils.nbia.api_call_headers != None 
                    else: tcia_utils.nbia.nlst_api_call_headers != None 
                    self.exp_time = tcia_utils.nbia.token_exp_time if self.apiKey == "restricted" else tcia_utils.nbia.nlst_token_exp_time
                except:
                    self.credentialError = "Please check your credential and try again.\nFor more information, check the Python console."

    def get_collection_values(self):
        return tcia_utils.nbia.getCollections(api_url = self.apiKey)
    
    def get_collection_descriptions(self):
        return tcia_utils.nbia.getCollectionDescriptions("nlst" if self.apiKey == "nlst" else "")
    
    def get_patient(self, collection = None):
        return tcia_utils.nbia.getPatient(collection, api_url = self.apiKey)

    def get_patient_study(self, collection = None, patientId = None, studyInstanceUid = None):
        return tcia_utils.nbia.getStudy(collection, patientId, studyInstanceUid, api_url = self.apiKey)
        
    def get_series(self, collection = None, patientId = None, studyInstanceUID = None, seriesInstanceUID = None, modality = None, 
                   bodyPartExamined = None, manufacturer = None, manufacturerModel = None):
        return tcia_utils.nbia.getSeries(collection, patientId, studyInstanceUID, seriesInstanceUID, modality, 
                                         bodyPartExamined, manufacturer, manufacturerModel, api_url = self.apiKey)

    def get_image(self, seriesInstanceUid):
        queryParameters = {"SeriesInstanceUID": seriesInstanceUid}
        url = tcia_utils.nbia.setApiUrl("getImage", self.apiKey) + "getImage?NewFileNames=Yes&%s" % urllib.parse.urlencode(queryParameters)
        headers = {"api_key": self.apiKey}
        if self.apiKey == "restricted": headers = headers | tcia_utils.nbia.api_call_headers
        request = urllib.request.Request(url = url, headers = headers)
        return urllib.request.urlopen(request)
    
    def logOut(self):
        tcia_utils.nbia.logoutToken(api_url = self.apiKey)