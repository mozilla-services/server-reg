# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from pyramid.security import Authenticated, Allow

from cornice.service import Service


class SRService(Service):
    """Custom Service class to assist DRY in the SyncReg project.

    This Service subclass provides useful defaults for SyncReg service
    endpoints, such as configuring authentication and path prefixes.
    """

    def __init__(self, **kwds):
        kwds["path"] = self._configure_the_path(kwds["path"])
        kwds.setdefault("acl", syncreg_acl)
        super(SRService, self).__init__(**kwds)

    def _configure_the_path(self, path):
        """Helper method to apply default configuration of the service path."""
        path = path.replace("{api}", "{api:1.0|1}")
        path = path.replace("{username}", "{username:[a-zA-Z0-9._-]+}")
        return path


def syncreg_acl(request):
    """Access Control List factory for SyncReg views.

    This ACL gives the "authn" permission to any authenticated user.  If
    the request matchdict as a "username" entry then it gives that username
    the "owner" permission.
    """
    acl = [(Allow, Authenticated, "authn")]
    if "username" in request.matchdict:
        acl.append((Allow, request.matchdict["username"], "owner"))
    return acl


user = SRService(name="user",
                 path="/user/{api}/{username}")
user_node = SRService(name="user_node",
                      path="/user/{api}/{username}/node/weave")
password_reset = SRService(name="password_reset",
                      path="/user/{api}/{username}/password_reset")
user_email = SRService(name="user_email",
                       path="/user/{api}/{username}/email")
user_password = SRService(name="user_password",
                          path="/user/{api}/{username}/password")
weave_password_reset = SRService(name="weave_password_reset",
                                 path="/weave-password-reset")
captcha = SRService(name="captcha",
                  path="/misc/{api}/captcha_html")
media = SRService(name="media",
                  path="/media/{filename}")


@user.get()
def user_exists(request):
    return request.registry["syncreg.controller.user"].user_exists(request)


@user.put()
def create_user(request):
    return request.registry["syncreg.controller.user"].create_user(request)


@user.delete(permission="owner")
def delete_user(request):
    return request.registry["syncreg.controller.user"].delete_user(request)


@user_node.get()
def get_user_node(request):
    return request.registry["syncreg.controller.user"].user_node(request)


@password_reset.get()
def get_password_reset(request):
    return request.registry["syncreg.controller.user"].password_reset(request)


@password_reset.delete(permission="owner")
def delete_password_reset(request):
    c = request.registry["syncreg.controller.user"]
    return c.delete_password_reset(request)


@user_email.post(permission="owner")
def change_email(request):
    return request.registry["syncreg.controller.user"].change_email(request)


@user_password.post()
def change_password(request):
    return request.registry["syncreg.controller.user"].change_password(request)


@weave_password_reset.get()
def get_weave_password_reset(request):
    c = request.registry["syncreg.controller.user"]
    return c.password_reset_form(request)


@weave_password_reset.post()
def post_weave_password_reset(request):
    c = request.registry["syncreg.controller.user"]
    return c.do_password_reset(request)


@captcha.get()
@captcha.post()
def captcha_form(request):
    return request.registry["syncreg.controller.user"].captcha_form(request)


@media.get()
def get_file(request):
    return request.registry["syncreg.controller.static"].get_file(request)
