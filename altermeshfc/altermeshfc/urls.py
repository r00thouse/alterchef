from django.conf.urls import patterns, include, url

from altermeshfc.firmcreator.views import NetworkCreateView, NetworkDetailView, NetworkListView, \
                                           NetworkUpdateView, NetworkDeleteView, FwProfileDetailView, \
                                           FwProfileDeleteView

urlpatterns = patterns('',
    url(r'^$', 'altermeshfc.firmcreator.views.index', name="index"),
    (r'^accounts/', include('registration.backends.default.urls')),

    url(r'^network/create/$', NetworkCreateView.as_view(), name='network-create'),
    url(r'^network/list/$', NetworkListView.as_view(), name='network-list'),
    url(r'^network/(?P<slug>[\w-]+)/$', NetworkDetailView.as_view(), name='network-detail'),
    url(r'^network/(?P<slug>[\w-]+)/edit/$', NetworkUpdateView.as_view(), name='network-edit'),
    url(r'^network/(?P<slug>[\w-]+)/delete/$', NetworkDeleteView.as_view(), name='network-delete'),

    url(r'^fwprofile/create/$', 'altermeshfc.firmcreator.views.create_profile_simple',
        name="fwprofile-create-simple"),
    url(r'^fwprofile/create-advanced/$', 'altermeshfc.firmcreator.views.crud_profile_advanced',
        name="fwprofile-create-advanced"),
    url(r'^fwprofile/(?P<slug>[\w-]+)/edit/$', 'altermeshfc.firmcreator.views.crud_profile_advanced',
        name="fwprofile-edit-advanced"),
    url(r'^fwprofile/(?P<slug>[\w-]+)/$', FwProfileDetailView.as_view(), name='fwprofile-detail'),
    url(r'^fwprofile/(?P<slug>[\w-]+)/delete/$', FwProfileDeleteView.as_view(), name='fwprofile-delete'),

    url(r'^diff/(?P<src_profile>[\w-]+)/(?P<dest_profile>[\w-]+)/$', 'altermeshfc.firmcreator.views.diff', name='fwprofile-diff'),


    url(r'^cook/(?P<slug>[\w-]+)/$', 'altermeshfc.firmcreator.views.cook', name='cook'),
    url(r'^cook/(?P<slug>[\w-]+)/started/$', 'altermeshfc.firmcreator.views.cook_started', name='cook-started'),

    url(r'^ls/(?P<path>.*)$', 'altermeshfc.list_dir.views.list_dir', name="list-dir"),

    url(r'^process_jobs/$', 'altermeshfc.firmcreator.views.process_jobs', name="process-jobs"),

    # url(r'^admin/', include(admin.site.urls)),
)
