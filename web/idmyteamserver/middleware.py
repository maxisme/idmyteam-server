from django.http import HttpRequest
from sentry_sdk import configure_scope


class SentryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        with configure_scope() as scope:
            # add X-B3-Traceid header as tag
            scope.set_tag("X-B3-Traceid", request.headers.get("X-B3-Traceid"))
        response = self.get_response(request)
        return response
