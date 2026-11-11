from glob import glob

from setuptools import find_packages, setup

package_name = 'contention_scheduler'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Stone Stephenson',
    maintainer_email='stephensos@sonoma.edu',
    description='Robot pipelines and actual Linux CPU monitoring for the CS485 trials.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'pipelines = contention_scheduler.pipelines:main',
            'cpu_monitor = contention_scheduler.cpu_monitor:main',
        ],
    },
)
