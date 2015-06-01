#-----------------------------------------------------------------------------
set(MODULE_NAME TCIABrowser)
set(LIB_NAME TCIABrowserLib)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  ${LIB_NAME}/__init__.py
  ${LIB_NAME}/TCIAClient.py
  ${LIB_NAME}/APISettingsPopup.py
  ${LIB_NAME}/clinicalDataPopup.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/downloadAndIndex.png
  Resources/Icons/downloadAndLoad.png
  Resources/Icons/report.png
  Resources/Icons/TCIABrowser.png
  Resources/Icons/stored.png
  Resources/Icons/download.png
  Resources/Icons/cancel.png
  Resources/Logos/logo-vertical.png
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  WITH_GENERIC_TESTS
  )

#-----------------------------------------------------------------------------
if(BUILD_TESTING)

  # Register the unittest subclass in the main script as a ctest.
  # Note that the test will also be available at runtime.
  slicer_add_python_unittest(SCRIPT ${MODULE_NAME}.py SLICER_ARGS --additional-module-path ${CMAKE_BINARY_DIR}/${Slicer_QTSCRIPTEDMODULES_LIB_DIR} )

  # Additional build-time testing
  add_subdirectory(Testing)
endif()

