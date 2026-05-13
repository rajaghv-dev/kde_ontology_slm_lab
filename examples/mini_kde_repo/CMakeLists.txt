# Mini KDE-style CMake. Intentionally simplified.
cmake_minimum_required(VERSION 3.16)
project(MiniSearch VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_AUTOMOC ON)

find_package(Qt6 REQUIRED COMPONENTS Core Quick)
find_package(KF6 REQUIRED COMPONENTS CoreAddons Config DBusAddons)

add_executable(minisearch
    src/main.cpp
    src/kfilesearcher.cpp
    src/kfilesearchbackend.cpp
)

target_link_libraries(minisearch
    PRIVATE
        Qt6::Core
        Qt6::Quick
        KF6::CoreAddons
        KF6::ConfigCore
        KF6::DBusAddons
)

add_subdirectory(tests)

install(TARGETS minisearch RUNTIME DESTINATION bin)
install(FILES desktop/minisearch.desktop DESTINATION share/applications)
install(FILES kconfig/minisearch.kcfg DESTINATION share/config.kcfg)
install(FILES dbus/org.kde.minisearch.xml DESTINATION share/dbus-1/interfaces)
