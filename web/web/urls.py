"""web URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from opentelemetry.ext import jaeger
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (BatchExportSpanProcessor, SimpleExportSpanProcessor, ConsoleSpanExporter)

from web.settings import DEBUG

trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

if DEBUG:
    # print tracer
    trace.get_tracer_provider().add_span_processor(
        SimpleExportSpanProcessor(ConsoleSpanExporter())
    )
else:
    # jaeger tracer
    jaeger_exporter = jaeger.JaegerSpanExporter(
        service_name='ID My Team',
        collector_host_name='jaeger-collector',
        collector_port=14268
    )
    trace.get_tracer_provider().add_span_processor(BatchExportSpanProcessor(jaeger_exporter))

with tracer.start_as_current_span('started ID My Team'):
    print('Started!')

urlpatterns = [
    path("", include("idmyteamserver.urls")),
]
