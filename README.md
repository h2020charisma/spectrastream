# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/h2020charisma/spectrastream/blob/COVERAGE-REPORT/htmlcov/index.html)

| Name                                       |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------- | -------: | -------: | ------: | --------: |
| src/front\_end/htmlTemplates.py            |        3 |        0 |    100% |           |
| src/modules/models.py                      |       54 |        0 |    100% |           |
| src/modules/navigation\_bar.py             |       14 |        0 |    100% |           |
| src/modules/util.py                        |       77 |       46 |     40% |22-26, 30-31, 40-76, 84-95, 118-120, 124-130, 134-135 |
| src/pages/\_\_init\_\_.py                  |        0 |        0 |    100% |           |
| src/pages/apply\_calibration.py            |      191 |      149 |     22% |34-37, 48-55, 70, 91-329, 340, 358-383, 416, 422-512, 520 |
| src/pages/load\_instrument\_settings.py    |       38 |        3 |     92% |38-39, 166 |
| src/pages/load\_or\_create\_calibration.py |      837 |      739 |     12% |89-102, 128-129, 150-167, 173-193, 202-220, 229-250, 271, 277, 284, 294, 304-307, 354, 362-387, 403-406, 419-999, 1006-1786, 1796-2158, 2165, 2191, 2213-2217, 2229-2233, 2240-2253, 2258, 2262, 2267-2418, 2422-2438, 2444-2451, 2454-2458, 2463, 2490-2539 |
| src/streamlit\_app.py                      |       12 |        0 |    100% |           |
| src/util\_x\_calibrations.py               |       33 |       33 |      0% |      1-61 |
| **TOTAL**                                  | **1259** |  **970** | **23%** |           |


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