from setuptools import setup, find_packages
import pathlib

# Read the contents of your README file
here = pathlib.Path(__file__).parent.resolve()
long_description = (here / "README.md").read_text(encoding="utf-8")

setup(
    name='DreamChain',
    version='0.06',
    packages=find_packages(),
    install_requires=[
        'requests',
        'pandas',
        'flask'
        
    ],
    author='Jackson Makl',
    author_email='jlm487@georgetown.edu',
    description='A Python client to interact with the DataPlatform API.',
    long_description=long_description,
    long_description_content_type='text/markdown',  # Specify Markdown here
    url='https://github.com/jacksonlmakl/DataPlatform',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
