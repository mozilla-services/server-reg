# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import os

from services.tests.support import TestEnv


def initenv(config=None):
    """Reads the config file and instantiates an auth and a storage.
    """
    mydir = os.path.dirname(__file__)
    testenv = TestEnv(ini_path=config, ini_dir=mydir, load_sections=['auth'])
    return testenv.ini_dir, testenv.config, testenv.auth
