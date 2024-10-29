# setup.py

from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README.md
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name='SpawnreDJ',
    version='0.3.2',  # Increment version number as appropriate
    packages=find_packages(),
    install_requires=[
        'mutagen>=1.45.1',
        'spotipy>=2.19.0',
        'musicbrainzngs>=0.7',
        'requests>=2.25.1',
        'pandas>=1.0.0',
        'python-dotenv>=0.19.0',
        # Add other dependencies here with version specs if necessary
    ],
    entry_points={
        'console_scripts': [
            'SpawnreDJ=SpawnreDJ.main:main',
        ],
    },
    author='Todd Marco',
    author_email='spawn.id.0000@gmail.com',
    description='A tool to generate, copy, analyze, & curate M3U playlists from a folder of audio files.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/SpawnID0000/SpawnreDJ',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    license='GNU General Public License v3 (GPLv3)',
    python_requires='>=3.6, <4',
    include_package_data=True,  # Ensure non-Python files are included
    # package_data={
    #     'SpawnreDJ': ['data/*.json'],  # Adjust as necessary
    # },
)
