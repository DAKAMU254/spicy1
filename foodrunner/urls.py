from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', core_views.landing_page, name='landing'),
    path('register/', core_views.register_view, name='register'),
    path('login/', core_views.login_view, name='login'),
    path('logout/', core_views.logout_view, name='logout'),
    path('profile/', core_views.profile_view, name='profile'),
    path("__reload__/", include("django_browser_reload.urls")),
    
    # App URLs
    path('customer/', include(('customers.urls', 'customers'), namespace='customers')),
    path('restaurant/', include(('restaurants.urls', 'restaurants'), namespace='restaurants')),
    path('delivery/', include(('delivery.urls', 'delivery'), namespace='delivery')),
    path('payments/', include(('payments.urls', 'payments'), namespace='payments')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)