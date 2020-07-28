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

# class TraceMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response
#
#     def __call__(self, request: HttpRequest):
#         logging.error("asdjbfasdhjbfds2")
#         logging.error("__name__")
#
#
#         tracer = trace.get_tracer(__name__)
#         with tracer.start_as_current_span("foo"):
#             logging.warning(trace.get_current_span().get_context().trace_id)
#             response = self.get_response(request)
#         return response

# class TraceMiddleware(_DjangoMiddleware):
#     def __init__(self, get_response=None):
#         super().__init__()
#         self.get_response = get_response
#
#     def process_view(
#             self, request, view_func, view_args, view_kwargs
#     ):
#         super().process_view(request, view_func, view_args, view_kwargs)
