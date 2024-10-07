import slicer, os

try:
    slicer.util.pip_install('tcia_utils -U -q')
except:
    slicer.util.pip_install('tcia_utils')
import tcia_utils.nbia

class TCIAClient:
    def __init__(self, user = "nbia_guest", pw = "", nlst = False):
        if nlst: self.apiUrl = "nlst"
        else: self.apiUrl = ""
        # create a token
        try:
            tcia_utils.nbia.getToken(user, pw, api_url = self.apiUrl)
            if self.apiUrl == "nlst":
                self.exp_time = tcia_utils.nbia.nlst_token_exp_time
            else:
                self.exp_time = tcia_utils.nbia.token_exp_time
        except:
            self.credentialError = "Please check your credential and try again.\nFor more information, check the Python console."

    def get_collection_values(self):
        return tcia_utils.nbia.getCollections(api_url = self.apiUrl)

    def get_collection_descriptions(self):
        return tcia_utils.nbia.getCollectionDescriptions(api_url = self.apiUrl)

    def get_patient(self, collection = None):
        return tcia_utils.nbia.getPatient(collection, api_url = self.apiUrl)

    def get_patient_study(self, collection = None, patientId = None, studyInstanceUid = None):
        return tcia_utils.nbia.getStudy(collection, patientId, studyInstanceUid, api_url = self.apiUrl)

    def get_series(self, collection = None, patientId = None, studyInstanceUID = None, seriesInstanceUID = None, modality = None,
                   bodyPartExamined = None, manufacturer = None, manufacturerModel = None):
        return tcia_utils.nbia.getSeries(collection, patientId, studyInstanceUID, seriesInstanceUID, modality,
                                         bodyPartExamined, manufacturer, manufacturerModel, api_url = self.apiUrl)

    def get_image(self, seriesInstanceUid, path):
        try:
            tcia_utils.nbia.downloadSeries([seriesInstanceUid], path=path, input_type="list", as_zip=True, api_url = self.apiUrl)
            # Rename the file to match TCIABrowser.py expectations
            old_file_path = os.path.join(path, f"{seriesInstanceUid}.zip")
            new_file_path = os.path.join(path, "images.zip")
            os.rename(old_file_path, new_file_path)

        except Exception as e:
            raise RuntimeError(f"Error downloading series {seriesInstanceUid}: {e}")

    def get_seg_ref_series(self, seriesInstanceUid):
        refSeries = tcia_utils.nbia.getSegRefSeries(seriesInstanceUid)
        metadata = tcia_utils.nbia.getSeriesMetadata(refSeries, api_url = self.apiUrl)[0]
        fileSize = round(int(metadata["File Size"])/1048576, 2)
        return metadata["Series UID"], 0.01 if fileSize <= 0.01 else fileSize

    def logOut(self):
        tcia_utils.nbia.getToken(user="nbia_guest")
