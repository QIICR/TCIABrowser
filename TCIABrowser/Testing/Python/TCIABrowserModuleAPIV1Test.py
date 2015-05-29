import qt, json, os, zipfile,dicom
import unittest
import slicer
import TCIABrowserLib
from Helper import *

class TCIABrowserModuleAPIV1Test(unittest.TestCase):

  def testAPIV3(self):
    helper = Helper()
    print 'Started API v1 Test...'
    helper.delayDisplay('API V1 Test Started')
    TCIAClient = TCIABrowserLib.TCIAClient(baseUrl='https://services.cancerimagingarchive.net/services/TCIA/TCIA/query')
    self.assertTrue(helper.downloadSeries(TCIAClient))
    helper.delayDisplay('API V1 Test Passed')
