from django.urls import path
from . import views

urlpatterns = [
    path('compare/', views.DocCompare, name='DocCompare'),
]
