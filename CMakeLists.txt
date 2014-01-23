cmake_minimum_required(VERSION 2.8.9)

project(TCIABorwser)

#-----------------------------------------------------------------------------
set(EXTENSION_HOMEPAGE "http://www.slicer.org/slicerWiki/index.php/Documentation/4.3/Extensions/TCIABorwser")
set(EXTENSION_CATEGORY "Informatics")
set(EXTENSION_CONTRIBUTORS "Alireza Mehrtash(SPL and BWH), Andrey Fedorov (SPL and BWH)")
set(EXTENSION_DESCRIPTION "A Module to connect to TCIA archive, browse the collections, patients and studies and download DICOM files to 3D Slicer.")
set(EXTENSION_ICONURL "http://viewvc.slicer.org/viewvc.cgi/Slicer4/trunk/Extensions/Testing/TCIABorwser/TCIABorwser.png?revision=21747&view=co")
set(EXTENSION_SCREENSHOTURLS "http://wiki.slicer.org/slicerWiki/images/e/e2/Slicer-r19441-TCIABorwser-screenshot.png")

#-----------------------------------------------------------------------------
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
add_subdirectory(TCIABrowser)

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_CPACK})
