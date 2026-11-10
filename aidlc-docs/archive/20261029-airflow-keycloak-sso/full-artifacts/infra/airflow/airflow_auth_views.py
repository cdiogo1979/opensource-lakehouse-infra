"""Combined Keycloak and local-administrator FAB login views."""

from __future__ import annotations

import os

from flask import flash, g, redirect, render_template_string, request, url_for
from flask_appbuilder.security.decorators import no_cache
from flask_appbuilder.security.forms import LoginForm_db
from flask_appbuilder.security.views import AuthOAuthView
from flask_appbuilder.utils.base import get_safe_redirect
from flask_appbuilder.views import expose
from flask_login import login_user


_OAUTH_LOGIN_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head><meta charset="utf-8"><title>Sign in to Airflow</title></head>
  <body>
    <main>
      <h1>Sign in to Airflow</h1>
      {% for category, message in get_flashed_messages(with_categories=true) %}
      <p role="alert" class="{{ category }}">{{ message }}</p>
      {% endfor %}
      {% for provider in providers %}
      <p><a href="{{ url_for('.login', provider=provider.name) }}">Continue with {{ provider.name }}</a></p>
      {% endfor %}
      <p><a href="{{ local_login_url }}">Local administrator sign-in</a></p>
    </main>
  </body>
</html>
"""

_LOCAL_LOGIN_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head><meta charset="utf-8"><title>Local administrator sign-in</title></head>
  <body>
    <main>
      <h1>Local administrator sign-in</h1>
      {% for category, message in get_flashed_messages(with_categories=true) %}
      <p role="alert" class="{{ category }}">{{ message }}</p>
      {% endfor %}
      <form method="post">
        {{ form.hidden_tag() }}
        <p>{{ form.username.label }} {{ form.username(autocomplete="username") }}</p>
        <p>{{ form.password.label }} {{ form.password(autocomplete="current-password") }}</p>
        <button type="submit">Sign in</button>
      </form>
      <p><a href="{{ oauth_login_url }}">Back to Keycloak sign-in</a></p>
    </main>
  </body>
</html>
"""


class LakehouseAuthOAuthView(AuthOAuthView):
    @expose("/login/")
    @expose("/login/<provider>")
    def login(self, provider: str | None = None):
        if provider is not None:
            return super().login(provider)
        if g.user is not None and g.user.is_authenticated:
            return redirect(self.appbuilder.get_url_for_index)
        return render_template_string(
            _OAUTH_LOGIN_TEMPLATE,
            providers=self.appbuilder.sm.oauth_providers,
            local_login_url=url_for(
                ".local_login", next=request.args.get("next", "")
            ),
        )

    @expose("/local-login/", methods=["GET", "POST"])
    @no_cache
    def local_login(self):
        if g.user is not None and g.user.is_authenticated:
            return redirect(self.appbuilder.get_url_for_index)
        form = LoginForm_db()
        if form.validate_on_submit():
            local_admin_username = os.environ.get("AIRFLOW_ADMIN_USERNAME", "admin")
            user = None
            if form.username.data == local_admin_username:
                user = self.appbuilder.sm.auth_user_db(
                    form.username.data, form.password.data
                )
            if user is None:
                flash("Invalid local administrator credentials.", "warning")
                return redirect(
                    url_for(".local_login", next=request.args.get("next", ""))
                )
            login_user(user, remember=False)
            return redirect(get_safe_redirect(request.args.get("next", "")))
        return render_template_string(
            _LOCAL_LOGIN_TEMPLATE,
            form=form,
            oauth_login_url=url_for(
                ".login", next=request.args.get("next", "")
            ),
        )
