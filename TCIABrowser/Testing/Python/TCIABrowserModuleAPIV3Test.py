import qt, json, os, zipfile,dicom
import unittest
import slicer
import TCIABrowserLib
from Helper import *

class TCIABrowserModuleAPIV3Test(unittest.TestCase):


  def testAPIV3(self):
    helper = Helper()
    print 'Started API v3 Test...'
    helper.delayDisplay('API V3 Test Started')
    TCIAClient = TCIABrowserLib.TCIAClient()
    self.assertTrue(helper.downloadSeries(TCIAClient))
    helper.delayDisplay('API V3 Test Passed')

