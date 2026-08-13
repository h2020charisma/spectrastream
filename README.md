# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/h2020charisma/spectrastream/blob/COVERAGE-REPORT/htmlcov/index.html)

| Name                                                  |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------------ | -------: | -------: | ------: | --------: |
| src/app\_pages/calibrate.py                           |      119 |       64 |     46% |93, 104-108, 119, 131, 136, 154-175, 182-185, 193-278 |
| src/app\_pages/convert.py                             |      193 |      167 |     13% |77-97, 119-569 |
| src/app\_pages/home.py                                |       27 |        0 |    100% |           |
| src/app\_pages/profiles.py                            |      157 |      109 |     31% |45-92, 97-189, 202, 236, 239-260, 282-284, 290-292, 315-318, 321, 349-359 |
| src/app\_pages/verify.py                              |      258 |      140 |     46% |43-45, 52-64, 86, 115, 119, 144-160, 177, 196-206, 242-251, 260, 279-280, 293-296, 305, 324-366, 371-432, 446-481, 500, 514-515, 534-537, 558-575, 579-653 |
| src/spectrastream/\_\_init\_\_.py                     |        1 |        0 |    100% |           |
| src/spectrastream/acquisition.py                      |       68 |        3 |     96% |86, 88, 178 |
| src/spectrastream/calibration/\_\_init\_\_.py         |        6 |        0 |    100% |           |
| src/spectrastream/calibration/engines/\_\_init\_\_.py |        0 |        0 |    100% |           |
| src/spectrastream/calibration/engines/base.py         |       50 |       10 |     80% |153-157, 174-180 |
| src/spectrastream/calibration/engines/rc2.py          |      278 |       84 |     70% |60, 101, 106, 138, 179, 181, 184, 188, 205, 235-236, 249-277, 301-302, 314-315, 317-322, 414, 457-480, 490-512, 544, 586, 597-613, 618 |
| src/spectrastream/calibration/registry.py             |       66 |       10 |     85% |38-39, 41, 72, 81, 88-89, 98-99, 110 |
| src/spectrastream/calibration/resolution.py           |       10 |        0 |    100% |           |
| src/spectrastream/calibration/spec.py                 |       75 |        2 |     97% |   97, 124 |
| src/spectrastream/calibration/verify.py               |      134 |       11 |     92% |85, 119, 127, 149, 203, 220, 262, 291-293, 322 |
| src/spectrastream/cwa.py                              |       39 |        0 |    100% |           |
| src/spectrastream/ingest.py                           |       58 |        6 |     90% |58-59, 67-68, 71, 107 |
| src/spectrastream/merge.py                            |       57 |        6 |     89% |55, 57, 77, 105-106, 122 |
| src/spectrastream/nexus.py                            |       96 |        3 |     97% |   134-136 |
| src/spectrastream/peaks.py                            |       46 |       20 |     57% |36-38, 48, 61, 78, 95-114 |
| src/spectrastream/preprocess.py                       |       69 |        6 |     91% |108, 119, 126, 158, 163-164 |
| src/spectrastream/profiles.py                         |      203 |       14 |     93% |50-53, 150, 198, 200, 202, 224, 243-244, 251, 306, 373 |
| src/spectrastream/upload.py                           |        7 |        0 |    100% |           |
| src/streamlit\_app.py                                 |       15 |        0 |    100% |           |
| src/ui/charts.py                                      |       87 |       37 |     57% |42, 48-49, 66-67, 77, 88-95, 120, 140-141, 162-174, 228, 253-296 |
| src/ui/inputs.py                                      |      119 |       91 |     24% |56-68, 74-126, 137-172, 207-267 |
| src/ui/localstore.py                                  |       46 |        1 |     98% |       139 |
| src/ui/profile\_store.py                              |       41 |       12 |     71% |27-28, 32-33, 50, 60-62, 73-74, 81-82 |
| src/ui/recipe\_form.py                                |      336 |      230 |     32% |96-97, 114-190, 203-206, 211-219, 232-234, 242-244, 248-250, 268-342, 370-435, 440-443, 457-480, 485-510, 521-626, 654-656, 669-678, 680-681, 690, 742-762 |
| src/ui/state.py                                       |      103 |       15 |     85% |49-52, 120, 124, 169-177 |
| **TOTAL**                                             | **2764** | **1041** | **62%** |           |


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