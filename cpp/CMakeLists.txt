cmake_minimum_required(VERSION 3.12)
project(wvab_navigation_planner CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(navigation_planner navigation_planner.cpp)
target_include_directories(navigation_planner PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

add_executable(navigation_demo main_demo.cpp)
target_link_libraries(navigation_demo PRIVATE navigation_planner)

if(WIN32)
  add_executable(wvab_speaker speaker_cli.cpp)
  target_link_libraries(wvab_speaker PRIVATE ole32 sapi)
endif()
