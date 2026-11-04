from django.urls import path
from . import views

urlpatterns = [
    path("", views.search, name="search"),
    path("bookmark/<str:username>/", views.bookmark, name="bookmark"),
    path("bookmarks/", views.bookmark_list, name="bookmarks"),
    path("bookmarks/<int:pk>/delete/", views.bookmark_delete, name="bookmark_delete"),
    path("bookmarks/<int:pk>/note/", views.bookmark_update_note, name="bookmark_update_note"),
    path("signup/", views.signup, name="signup"),
    path("visualize/", views.visualize, name="visualize"),
]
