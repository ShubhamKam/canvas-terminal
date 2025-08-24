cmake_minimum_required(VERSION 3.10)
project(libjackpal-termexec2)

add_library(jackpal-termexec2 SHARED process.cpp)

find_library(log-lib log)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

target_link_libraries(jackpal-termexec2 ${log-lib})
