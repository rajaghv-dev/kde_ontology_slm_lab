# MiniSearchConfig.cmake — placeholder package config file. Real KDE projects ship one per module.
include(CMakeFindDependencyMacro)
find_dependency(Qt6 COMPONENTS Core Quick)
find_dependency(KF6 COMPONENTS CoreAddons Config DBusAddons)
include("${CMAKE_CURRENT_LIST_DIR}/MiniSearchTargets.cmake")
