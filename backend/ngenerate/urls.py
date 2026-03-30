from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView

# 1. Import views จาก drf-spectacular
from drf_spectacular.views import (
    SpectacularAPIView, 
    SpectacularSwaggerView, 
    SpectacularRedocView
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # --- API Documentation ---
    # ส่วนนี้จะสร้างไฟล์ schema.yml เบื้องหลัง
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    
    # หน้า Swagger UI สำหรับทดสอบ API (แนะนำอันนี้)
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # หน้า Redoc สำหรับอ่าน Doc แบบสวยงาม (Optional)
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # jwt 
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # --- App Endpoints ---
    path('user/', include("users.urls")),
    path('payment/', include("payments.urls")),
    path('library/', include("novels.urls")),
    path('session/', include("ngenerate_sessions.urls")),
    path('asset/', include("asset.urls")),
    path('notification/', include("notifications.urls")),
    path("admin-console/", include("admin_console.urls")),
]

# การจัดการ Media และ Static files ในช่วง Development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)