# MIT No Attribution

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Third-Party Licenses

This document contains the licenses and copyright notices for third-party software components used in the Oracle to PostgreSQL MyBatis Mapper Conversion (OMA) project.

## JPetStore-6 Sample Application

### License: Apache License 2.0
**Copyright**: MyBatis JPetStore Copyright 2010-2023  
**Source**: The MyBatis Team (http://mybatis.org/)  
**License URL**: https://www.apache.org/licenses/LICENSE-2.0  
**Usage**: Used as a sample application for testing Oracle to PostgreSQL conversion

### Included Components

#### iBATIS
- **License**: Apache License 2.0
- **Copyright**: Copyright 2010 The Apache Software Foundation
- **Source**: http://www.apache.org/

#### OGNL
- **License**: BSD-style license
- **Copyright**: Copyright (c) 2004, Drew Davidson and Luke Blanshard

```
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.
Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in the
documentation and/or other materials provided with the distribution.
Neither the name of the Drew Davidson nor the names of its contributors
may be used to endorse or promote products derived from this software
without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF
THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
DAMAGE.
```

## Python Dependencies

### psycopg2 - PostgreSQL Database Adapter
- **License**: GNU Lesser General Public License (LGPL) v3
- **Copyright**: Copyright (C) 2001-2021 Federico Di Gregorio
- **Source**: https://github.com/psycopg/psycopg2
- **Usage**: PostgreSQL database connectivity for OMA conversion tools

### Python Standard Library Components
The OMA conversion tools use the following Python standard library modules under the Python Software Foundation License:

- `xml.etree.ElementTree` - XML processing
- `argparse`, `csv`, `json`, `logging`, `os`, `re`, `sys` - Core functionality
- `datetime`, `time` - Date/time handling
- `collections`, `concurrent.futures` - Data structures and concurrency
- `subprocess`, `tempfile`, `shutil` - System operations

## License Compliance

- All third-party components are used in compliance with their respective licenses
- Original license files are preserved in their respective directories
- No modifications have been made to the core JPetStore-6 application code
- The OMA conversion tools are separate utilities that process the sample application
- This project does not redistribute any third-party binaries or modified source code

## Full License Texts

For complete license texts, please refer to:
- JPetStore-6: `jpetstore-6/LICENSE` and `jpetstore-6/NOTICE`
- Apache License 2.0: https://www.apache.org/licenses/LICENSE-2.0
- Python Software Foundation License: https://docs.python.org/3/license.html
- LGPL v3: https://www.gnu.org/licenses/lgpl-3.0.html
