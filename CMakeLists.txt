cmake_minimum_required(VERSION 2.8.9)

project(TCIABrowser)

#-----------------------------------------------------------------------------
set(EXTENSION_HOMEPAGE "https://github.com/QIICR/TCIABrowser/blob/master/")
set(EXTENSION_CATEGORY "Informatics")
set(EXTENSION_CONTRIBUTORS "Alireza Mehrtash(SPL and BWH), Andrey Fedorov (SPL and BWH), Adam Li (GU), Justin Kirby (FNLCR)")
set(EXTENSION_DESCRIPTION "A Module to download DICOM data from The Cancer Imaging Archive.")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/QIICR/TCIABrowser/master/TCIABrowser/Resources/Icons/TCIABrowser.png")
set(EXTENSION_SCREENSHOTURLS "https://raw.githubusercontent.com/QIICR/TCIABrowser/master/TCIABrowser/Resources/Screenshot/Screenshot_2.png")
set(EXTENSION_DEPENDS QuantitativeReporting SlicerRT)

#-----------------------------------------------------------------------------
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
add_subdirectory(TCIABrowser)

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_CPACK})
