from django.conf.urls import patterns, include, url

from django.contrib import admin
from django.contrib.auth.decorators import permission_required, user_passes_test

from ikwen.core.views import Offline
from ikwen.core.analytics import analytics
from ikwen.accesscontrol.utils import is_staff, update_push_subscription

from ikwen_kakocase.shopping.views import FlatPageView, Home
from ikwen_kakocase.kakocase.views import Welcome, AdminHome, FirstTime, GuardPage
from ikwen_kakocase.trade.provider.views import ProviderDashboard, CCMDashboard

from yamo.views import save_ghost_user

admin.autodiscover()


urlpatterns = patterns(
    '',
    url(r'^laakam/', include(admin.site.urls)),
    url(r'^kakocase/', include('ikwen_kakocase.kakocase.urls', namespace='kakocase')),
    url(r'^kako/', include('ikwen_kakocase.kako.urls', namespace='kako')),
    url(r'^trade/', include('ikwen_kakocase.trade.urls', namespace='trade')),
    url(r'^billing/', include('ikwen.billing.urls', namespace='billing')),
    url(r'^marketing/', include('ikwen_kakocase.commarketing.urls', namespace='marketing')),
    url(r'^sales/', include('ikwen_kakocase.sales.urls', namespace='sales')),
    url(r'^shopping/', include('ikwen_kakocase.shopping.urls', namespace='shopping')),

    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^currencies/', include('currencies.urls')),
    url(r'^items/', include('ikwen_webnode.items.urls', namespace='items')),
    url(r'^web/', include('ikwen_webnode.web.urls', namespace='web')),
    url(r'^blog/', include('ikwen_webnode.blog.urls', namespace='blog')),
    url(r'^revival/', include('ikwen.revival.urls', namespace='revival')),
    url(r'^rewarding/', include('ikwen.rewarding.urls', namespace='rewarding')),
    url(r'^daraja/', include('daraja.urls', namespace='daraja')),

    url(r'^ikwen/dashboard/$', permission_required('trade.ik_view_dashboard')(ProviderDashboard.as_view()), name='dashboard'),
    url(r'^ikwen/CCMDashboard/$', permission_required('trade.ik_view_dashboard')(CCMDashboard.as_view()), name='ccm_dashboard'),
    url(r'^ikwen/theming/', include('ikwen.theming.urls', namespace='theming')),
    url(r'^cci/', include('ikwen_kakocase.cci.urls', namespace='cci')),
    url(r'^ikwen/cashout/', include('ikwen.cashout.urls', namespace='cashout')),
    url(r'^ikwen/home/$', user_passes_test(is_staff)(AdminHome.as_view()), name='admin_home'),
    url(r'^ikwen/', include('ikwen.core.urls', namespace='ikwen')),
    url(r'^analytics', analytics),
    url(r'^update_push_subscription$', update_push_subscription),

    url(r'^echo/', include('echo.urls', namespace='echo')),

    # url(r'^$', ProviderDashboard.as_view(), name='admin_home'),
    url(r'^page/(?P<url>[-\w]+)/$', FlatPageView.as_view(), name='flatpage'),
    url(r'^welcome/$', Welcome.as_view(), name='welcome'),
    url(r'^firstTime/$', FirstTime.as_view(), name='first_time'),
    url(r'^guardPage/$', GuardPage.as_view(), name='guard_page'),


    url(r'^home/', include('ikwen_webnode.webnode.urls', namespace='webnode')),
    url(r'^$', Home.as_view(), name='home'),

    url(r'^offline.html$', Offline.as_view(), name='offline'),
    url(r'^save_ghost_user$', save_ghost_user, name='save_ghost_user'),
)

