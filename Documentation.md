TCIABrowser Documentation
=========================


## Introduction and Acknowledgements
Extension: **TCIABrowser** <br>
Extension Category: Informatics <br>
Acknowledgments: This work is funded by the National Institutes of Health, National Cancer Institute through the Grant Quantitative Image Informatics for Cancer Research (QIICR) (U24 CA180918) (PIs Kikinis and Fedorov). <br>
Contributors: Alireza Mehrtash(SPL), Andrey Fedorov(SPL), Adam Li(GU), Justin Kirby(FNLCR) <br>
Contact: Alireza Mehrtash, <email>mehrtash@bwh.harvard.edu</email>; Justin Kirby, <email>kirbyju@mail.nih.gov</email> <br>
License: [Slicer License](https://github.com/Slicer/Slicer/blob/main/License.txt) <br>


## Module Description
<img src="TCIABrowser.png" width="150">

The Cancer Imaging Archive (TCIA) hosts a large collection of Cancer medical imaging data which is available to the public through a programmatic interface (REST API). TCIA Browser is a Slicer module by which the user can connect to the TCIA archive, browse different collections, patient subjects, studies, and series, download the images, and visualize them in 3D Slicer.<br>
[TCIA metrics dashboard](https://www.cancerimagingarchive.net/dashboard2/) provides extensive details on the types of imaging data by anatomy and other characteristics available within TCIA.


## Panels and their use
1. #### Settings
> By opening the TCIABrowser module, it will show the settings. There are two settings currently available: Account and Storage Folder.
> By default, the username field is filled by "nbia_guest" with an empty password field.
> To browse and download public data, click "Login" and proceed.
> To access the NLST(National Lung Screening Trial) dataset, check the "nlst" box and proceed with the default login information.
> When the "nlst" box is checked, all entered account information will be discarded.
> Click the folder box and change the path to change where images are downloaded.
> To reset the storage folder back to its original location, click the "Reset Path" button.
> When done using the browser, click "logout" to exit or click "Show Browser" to check other available datasets.
> ![Settings Screenshot](TCIABrowser/Resources/Screenshot/Settings.png)
> - A: Login area
> - B: Storage location

2. #### Browsing Collections, Patients and Studies
> After logging into an account, it will connect to the TCIA server and list all available collections.
> Select a collection from the "Current Collection" combo box.
> The browser will get the patient data from the TCIA server and populate the Patients table.
> The use Cache checkbox will cache the query results on your hard drive, making further recurring queries faster.
> The user can uncheck this box if a direct query from the TCIA server is desired. In the case of caching server responses, the latest access time is provided for each table separately.
> Further selecting a patient will populate the study table for the selected one, and selecting a study will update the series table.
> ![Downloading Data Screenshot](TCIABrowser/Resources/Screenshot/Downloading.png)
> - A: Collection selector combobox
> - B: Cache server response to the local storage
> - C: Tables are expandable
> - D: Status of the series (Available on local database / Available on TCIA server)
> - E: Download and Index to the Slicer DICOM database (local storage)
> - F: Download and load into the Slicer scene

3. #### Downloading Series
> After selecting at least one series, the download icons will become activated.
> Pressing the "Download and Index" button will download the images from TCIA to your computer and index the DICOM files inside the 3D Slicer DICOM database.
> So you can review them, check the meta-data, and load them into the scene later with the Slicer DICOM module.
> Pressing the "Download and Load" button will download and load the images into the Slicer scene.
> You can select multiple items from all of the tables.
> By holding the Ctrl key and clicking on different patients, the studies for all the selected ones will be added to the studies table.
> You can select all the studies by pressing the 'Select All' button or make a specific selection by Ctrl+Click, and all the available series for download will be added to the series table.
> At the final step, select series for download from the series table.
> The total number of images for the selected series is indicated at the bottom right corner of the series table.
> After pressing the download button, you can check the download status of each series at the 'Download Status' collapsible button at the module's widget.
> While the download is in progress, you can still browse and add other series to the download queue or view the downloaded images in the 3D Slicer Scene.
> ![Downloading Data Screenshot](TCIABrowser/Resources/Screenshot/Downloading.png)
> - A: Progress bar showing the download status of the selected series
> - B: Status bar showing the current process and the status of server responses
> - C: Cancel downloads button


## Similar Modules
- [SNATSlicer](https://github.com/NrgXnat/XNATSlicer.git)
- [DICOM](https://slicer.readthedocs.io/en/latest/user_guide/modules/dicom.html)

## Reference
- [Quantitative Image Informatics for Cancer Research (QIICR)](http://qiicr.org/)
- [Quantitative Imaging Network (QIN)](http://imaging.cancer.gov/programsandresources/specializedinitiatives/qin)
- [TCIA Home Page](http://cancerimagingarchive.net/)
- [cBioPortal for Cancer Genomics Web Interface](https://docs.cbioportal.org/web-api-and-clients/)
- [Description of TCIA Collections](https://wiki.cancerimagingarchive.net/display/Public/Collections)
- [TCIA Rest API Documentation](https://wiki.cancerimagingarchive.net/display/Public/TCIA+Programmatic+Interface+REST+API+Guides)
- [Project page at NAMIC 2014 Project Week](http://www.na-mic.org/Wiki/index.php/2014_Project_Week:TCIA_Browser_Extension_in_Slicer)
- [Rapid API page for testing TCIA API endpoint](https://rapidapi.com/tcia/api/the-cancer-imaging-archive/)


## Information for Developers
**[Source Code](https://github.com/QIICR/TCIABrowser.git)**
<br>
Extension Dependencies:
- [QuantitativeReporting](https://qiicr.gitbook.io/quantitativereporting-guide/)
- [SlicerRT](http://slicerrt.github.io)

Checking the API from the Python console:
```
import TCIABrowserLib as tblib
client = tblib.TCIAClient.TCIAClient()
response = client.get_collection_values()
print(response_string)
```
