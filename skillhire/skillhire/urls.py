from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path(
        'all_offers/', views.AllOffersView.as_view(),
        name='all_offers'
    ),
    path(
        'offer/<int:id>', views.OfferView.as_view(),
        name='offer'
    ),
    path(
        'message/<int:id>', views.MessageView.as_view(),
        name='message'
    ),
    path(
        'user_offers/', views.UserOffersView.as_view(),
        name='user_offers'
    ),
    path(
        'user_offer/<int:id>/', views.UserOfferView.as_view(),
        name='user_offer'
    ),
    path(
        'add_offer/', views.AddOfferView.as_view(),
        name='add_offer'
    ),
    path(
        'all_views/', views.AllViewsView.as_view(),
        name='all_views'
    ),
    path(
        'history/', views.HistoryView.as_view(),
        name='history'
    ),
    path(
        'profile/', views.ProfileView.as_view(),
        name='profile'
    ),
    # path(
    #     'username/', views.UsernameView.as_view(),
    #     name='username'
    # ),
    path(
        'first_name/', views.FirstNameView.as_view(),
        name='first_name'
    ),
    path(
        'last_name/', views.LastNameView.as_view(),
        name='last_name'
    ),
    path(
        'email/', views.EmailView.as_view(),
        name='email'
    ),
    path(
        'location/', views.LocationView.as_view(),
        name='location'
    ),
]
