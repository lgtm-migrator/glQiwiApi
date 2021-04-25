import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    packages=setuptools.find_packages(),
    include_package_data=True,
    name="glQiwiApi",  # Replace with your own username
    version="0.2.17",
    author="GLEF1X",
    author_email="glebgar567@gmail.com",
    description="Light and fast wrapper for qiwi and yoomoney",
    package_data={"glQiwiApi": ["py.typed", "*.pyi", "**/*.pyi"]},
    # Длинное описание, которое будет отображаться на странице PyPi.
    # Использует README.md репозитория для заполнения.
    long_description=long_description,
    # Определяет тип контента, используемый в long_description.
    long_description_content_type="text/markdown",
    url="https://github.com/GLEF1X/glQiwiApi",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "pytz==2021.1",
        "aiohttp==3.7.4.post0",
        'aiofiles==0.6.0',
        "pydantic==1.8.1",
        "wheel",
    ],
    python_requires=">=3.7",
)
