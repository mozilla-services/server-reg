# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Static controller that serve files.

XXX DO NOT USE IN PRODUCTION -- USE AN APACHE ALIAS INSTEAD

This controller will fully load files it serves in memory.
"""
import os
from mimetypes import guess_type

from webob.exc import HTTPNotFound
from webob import Response

_STATIC_DIR = os.path.join(os.path.dirname(__file__), '..', 'static')


class StaticController(object):
    """Used to return static files
    """
    def __init__(self, app):
        self.app = app

    def get_file(self, request):
        """Returns a file located in the static/ directory."""
        filename = request.sync_info['filename']
        path = os.path.join(_STATIC_DIR, filename)
        if not os.path.exists(path):
            raise HTTPNotFound()

        with open(path) as f:
            data = f.read()

        __, content_type = guess_type(filename)
        return Response(data, content_type=content_type)
