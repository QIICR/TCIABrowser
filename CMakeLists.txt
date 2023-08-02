cmake_minimum_required(VERSION 2.8.9)

project(TCIABrowser)

#-----------------------------------------------------------------------------
set(EXTENSION_HOMEPAGE "https://github.com/QIICR/TCIABrowser/blob/master/")
set(EXTENSION_CATEGORY "Informatics")
set(EXTENSION_CONTRIBUTORS "Alireza Mehrtash(SPL and BWH), Andrey Fedorov (SPL and BWH), Adam Li (GU), Justin Kirby (FNLCR)")
set(EXTENSION_DESCRIPTION "A Module to connect to TCIA archive, browse the collections, patients and studies and download DICOM files to 3D Slicer.")
set(EXTENSION_ICONURL "https://github.com/QIICR/TCIABrowser/blob/master/TCIABrowser/Resources/Logos/TCIABrowser.svg")
set(EXTENSION_SCREENSHOTURLS "https://github.com/QIICR/TCIABrowser/blob/master/TCIABrowser/Resources/Screenshot/Screenshot_1.png")
set(EXTENSION_DEPENDS QuantitativeReporting SlicerRT)

#-----------------------------------------------------------------------------
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
add_subdirectory(TCIABrowser)

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_CPACK})
