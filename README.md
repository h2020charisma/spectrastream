# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/h2020charisma/spectrastream/blob/COVERAGE-REPORT/htmlcov/index.html)

| Name                                       |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------- | -------: | -------: | ------: | --------: |
| src/front\_end/htmlTemplates.py            |        3 |        0 |    100% |           |
| src/modules/models.py                      |       43 |        0 |    100% |           |
| src/modules/navigation\_bar.py             |       14 |        0 |    100% |           |
| src/modules/util.py                        |       74 |       45 |     39% |19-23, 27, 36-72, 80-91, 114-116, 120-126, 130-131 |
| src/pages/\_\_init\_\_.py                  |        0 |        0 |    100% |           |
| src/pages/apply\_calibration.py            |      188 |      149 |     21% |25-28, 38-45, 60, 81-317, 326, 343-366, 405, 410-499, 506 |
| src/pages/load\_instrument\_settings.py    |       29 |        3 |     90% |17-18, 145 |
| src/pages/load\_or\_create\_calibration.py |      833 |      738 |     11% |87-100, 133-134, 155-171, 177-196, 205-223, 232-253, 272, 277, 283, 295, 305-308, 357, 365-390, 405-408, 427-989, 996-1769, 1779-2123, 2130, 2158, 2180-2184, 2195-2199, 2205-2218, 2223, 2226, 2230-2380, 2384-2399, 2403-2410, 2413-2417, 2421, 2447-2500 |
| src/streamlit\_app.py                      |       10 |        0 |    100% |           |
| src/util\_x\_calibrations.py               |       31 |       31 |      0% |      1-59 |
| **TOTAL**                                  | **1225** |  **966** | **21%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/h2020charisma/spectrastream/COVERAGE-REPORT/badge.svg)](https://htmlpreview.github.io/?https://github.com/h2020charisma/spectrastream/blob/COVERAGE-REPORT/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/h2020charisma/spectrastream/COVERAGE-REPORT/endpoint.json)](https://htmlpreview.github.io/?https://github.com/h2020charisma/spectrastream/blob/COVERAGE-REPORT/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fh2020charisma%2Fspectrastream%2FCOVERAGE-REPORT%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/h2020charisma/spectrastream/blob/COVERAGE-REPORT/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.