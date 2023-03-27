import setuptools

setuptools.setup(
    name="lcc_browser",
    version="1.0",
    author="Adrian Haensler",
    description="Model railroad LCC application with an embedded web browser",
    license="MIT",
    project_urls = {
        "Source": "https://github.com/ahaensler/lcc_browser",
        "Issues": "https://github.com/ahaensler/lcc_browser/issues",
    },
    packages=[
        "lcc_browser",
        "lcc_browser.can",
        "lcc_browser.can.drivers",
        "lcc_browser.lcc",
        "lcc_browser.wx_controls",
        "lcc_browser.templates",
    ],
    scripts=["bin/lcc_browser"],
    install_requires=[
        "wxPython >= 4.2.0",
        "appdirs >= 1.4.4",
        "construct >= 2.10.68",
        "lxml >= 4.9.1",
        "pyserial >= 3.5",
        "PyYAML >= 6.0",
        "setuptools >= 62.6.0",
    ],
    python_requires=">=3.10"
)
