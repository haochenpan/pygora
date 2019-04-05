import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pygora-phchcc",
    version="0.0.3",
    author="Haochen Pan",
    author_email="phchcc@gmail.com",
    description="A web crawler library that fetches and parses data from Boston College Agora Portal",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/haochenpan/pygora",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
