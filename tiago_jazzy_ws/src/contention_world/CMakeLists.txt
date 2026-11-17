cmake_minimum_required(VERSION 3.8)
project(contention_world)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch worlds DESTINATION share/${PROJECT_NAME})
install(PROGRAMS scripts/place_box scripts/run_trial DESTINATION lib/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_hallway_world test/test_hallway_world.py)
  ament_add_pytest_test(test_trial test/test_trial.py)
endif()

ament_package()
