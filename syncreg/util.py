# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import os
from mako.lookup import TemplateLookup

_TPL_DIR = os.path.join(os.path.dirname(__file__), 'templates')
_lookup = TemplateLookup(directories=[_TPL_DIR],
                         module_directory=_TPL_DIR)  # XXX defined in prod


def render_mako(template, **data):
    """Renders a mako template located in '/templates'

    Args:
        template: template name, so /templates/template exists
        data: dict passed to the template engine

    Requests:
        returns the rendered template
    """
    template = _lookup.get_template(template)
    return template.render(**data)
