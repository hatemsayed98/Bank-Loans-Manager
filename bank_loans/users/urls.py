from django.urls import path

from .api.views import LogoutAPIView
from .api.views import SignInView
from .api.views import UserRetrieveView

app_name = "users"
urlpatterns = [
    path("login/", SignInView.as_view(), name="token-obtain-pair"),
    path("profile/", UserRetrieveView.as_view(), name="user_retrieve"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
]
