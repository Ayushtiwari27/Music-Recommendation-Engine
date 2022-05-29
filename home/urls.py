from xml.etree.ElementInclude import include
from django.urls import path
from home import views

urlpatterns = [
    path('',views.home, name="home"),
    path('nice',views.nice,name="nice"),
    path('login',views.loginUser, name="login"),
    path('register',views.registeruser, name="register"),
    path('logout',views.logoutUser, name="logout"),
    path('recommend_songs/<str:myid>',views.recommend_songs1, name="recommend_songs1")
]