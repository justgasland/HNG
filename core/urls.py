from django.urls import path
from .views import(
    HealthCheck,
    ReelReadView

)

urlpatterns=[
    path('reelread', ReelReadView.as_view(), name='reelread'),
    path('health', HealthCheck.as_view(), name='healthcheck')
]