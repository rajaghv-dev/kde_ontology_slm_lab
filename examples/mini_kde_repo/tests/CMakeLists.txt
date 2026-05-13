find_package(Qt6 REQUIRED COMPONENTS Test)
add_executable(tst_kfilesearcher tst_kfilesearcher.cpp)
target_link_libraries(tst_kfilesearcher PRIVATE Qt6::Test)
add_test(NAME tst_kfilesearcher COMMAND tst_kfilesearcher)
