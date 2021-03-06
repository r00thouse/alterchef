# -*- coding: utf-8 -*-

import os
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404
from django.http import Http404, HttpResponseServerError
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse_lazy
from django.core.exceptions import PermissionDenied
from django.views.generic import ListView, UpdateView, DetailView, CreateView, DeleteView
from django.template import Context, Template, RequestContext
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
import pygments
from pygments.lexers import DiffLexer
from pygments.formatters import HtmlFormatter
from difflib import unified_diff

from utils import LoginRequiredMixin, UserOrAdminRequiredMixin, UserRequiredMixin
from models import IncludeFiles, Network, FwProfile, FwJob, SSHKey, OpenwrtImageBuilder
from forms import IncludeFilesFormset, IncludePackagesForm, FwProfileForm, \
                   NetworkForm, FwProfileSimpleForm


def index(request):
    return render(request, "index.html", {
    })


##
# Network Views

class NetworkCreateView(LoginRequiredMixin, CreateView):
    model = Network

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(NetworkCreateView, self).form_valid(form)

class NetworkUpdateView(LoginRequiredMixin, UserOrAdminRequiredMixin, UpdateView):
    model = Network

class NetworkDeleteView(LoginRequiredMixin, UserOrAdminRequiredMixin, DeleteView):
    model = Network
    success_url = reverse_lazy('network-list')

class NetworkDetailView(DetailView):
    model = Network

class NetworkListView(ListView):
    model = Network

##
# SSHKey views

class SSHKeyCreateView(LoginRequiredMixin, CreateView):
    model = SSHKey

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(SSHKeyCreateView, self).form_valid(form)

class SSHKeyUpdateView(LoginRequiredMixin, UserRequiredMixin, UpdateView):
    model = SSHKey

class SSHKeyDeleteView(LoginRequiredMixin, UserRequiredMixin, DeleteView):
    model = SSHKey
    success_url = reverse_lazy('sshkey-list')

class SSHKeyDetailView(DetailView):
    model = SSHKey

class SSHKeyListView(ListView):
    model = SSHKey

##
# Profile Views

class FwProfileDetailView(DetailView):
    model = FwProfile

    def get_context_data(self, **kwargs):
        context = super(FwProfileDetailView, self).get_context_data(**kwargs)
        context['pending_jobs'] = FwJob.objects.filter(status__in = ["WAITING", "STARTED"],
                                                       profile=self.object)
        jobs = FwJob.objects.filter(profile=self.object).order_by('-pk')[:1]
        if jobs:
            context['last_job'] = jobs[0]

        profiles = FwProfile.objects.all().exclude(slug=self.object.slug)
        if self.object.based_on:
            profiles = profiles.exclude(slug=self.object.based_on.slug)
        context['profiles'] = profiles
        context['openwrt_image_builder'] = OpenwrtImageBuilder
        return context

class FwProfileDeleteView(LoginRequiredMixin, UserOrAdminRequiredMixin, DeleteView):
    model = FwProfile
    success_url = reverse_lazy('network-list')

@login_required
def create_profile_simple(request):
    initial = {}
    default_profile_slug = getattr(settings, "DEFAULT_PROFILE_SLUG", None)
    if default_profile_slug:
        initial['based_on'] = FwProfile.objects.get(slug=default_profile_slug)

    if request.method == "POST":
        form = FwProfileSimpleForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            based_on = form.cleaned_data.get("based_on")
            fw_profile = form.save()
            if based_on:
                fw_profile.include_files = based_on.include_files
                fw_profile.include_packages = based_on.include_packages
            fw_profile.save()
            return redirect("fwprofile-detail", slug=fw_profile.slug)
    else:
        network = request.GET.get("network", None)
        if network:
            initial['network'] = get_object_or_404(Network, pk=network)
        form = FwProfileSimpleForm(user=request.user, initial=initial)

    return render(request, "firmcreator/create_profile_simple.html", {
        'form': form,
    })

@login_required
def crud_profile_advanced(request, slug=None):
    instance = get_object_or_404(FwProfile, slug=slug) if slug else None
    if request.method == "POST":
        profile_form = FwProfileForm(request.POST, request.FILES, user=request.user, instance=instance)
        include_files_formset = IncludeFilesFormset(request.POST, prefix="include-files")
        include_packages_form = IncludePackagesForm(request.POST)
        if profile_form.is_valid() and include_files_formset.is_valid() and \
           include_packages_form.is_valid():
            fw_profile = profile_form.save()
            fw_profile.include_packages = include_packages_form.to_str()
            files = include_files_formset.include_files()
            uploaded_files = profile_form.cleaned_data.get("upload_files")
            if uploaded_files:
                try:
                    files.update(IncludeFiles.load_from_tar(uploaded_files).files)
                except UnicodeDecodeError:
                    error = _("Encoding Error: Uploaded tarfile must have all it's files encoded in UTF-8.")
                    return HttpResponseServerError(render_to_string('500.html', {"message": error},
                                                                     RequestContext(request)))
            fw_profile.include_files = files
            fw_profile.save()
            return redirect("fwprofile-detail", slug=fw_profile.slug)

    else:
        based_on = request.GET.get("based_on", None)
        try:
            int(based_on)
        except (ValueError, TypeError):
            based_on = None
        if based_on:
            based_on = get_object_or_404(FwProfile, pk=based_on)

        def get_initial_files(obj):
            return [{"path": path, "content": content} for path, content in obj.include_files.iteritems()]

        inherited = instance or based_on
        initial_files = get_initial_files(inherited) if inherited else None
        include_files_formset = IncludeFilesFormset(initial=initial_files, prefix="include-files")
        include_packages_form = IncludePackagesForm.from_str(inherited.include_packages if inherited else "")

        profile_form = FwProfileForm(initial=dict(request.GET.items()) or None, instance=instance,
                                     user=request.user)

    return render(request, "firmcreator/crud_profile.html", {
        'include_files_formset': include_files_formset,
        'include_packages_form': include_packages_form,
        'profile_form': profile_form,
        'object': instance,
    })


@login_required
def cook(request, slug):
    profile = get_object_or_404(FwProfile, slug=slug)

    context = {"profile": profile}
    jobs = FwJob.objects.filter(profile=profile, status__in=["WAITING", "STARTED"])
    if jobs:
        context["job"] = jobs[0]
    else:
        if request.method == "POST":
            job_data = {
                "devices": profile.devices.split(),
                "revision": profile.openwrt_revision,
                "profile_id": profile.pk,
                "user_id": request.user.pk
            }
            job = FwJob.objects.create(status="WAITING", profile=profile,
                                       user=request.user, job_data=job_data)
            return redirect("fwprofile-detail", slug=profile.slug)
    return render(request, "firmcreator/cook.html", context)


def view_jobs(request):
    jobs = FwJob.objects.select_related().all()[:100]
    return render(request, "firmcreator/fwjob_list.html", {"jobs": jobs})

def diff(request, src_profile, dest_profile):
    src_profile = get_object_or_404(FwProfile, slug=src_profile)
    dest_profile = get_object_or_404(FwProfile, slug=dest_profile)

    html_formatter = HtmlFormatter()
    style = html_formatter.get_style_defs()

    def add_rm_chg(src, dest):
        return dest - src, src - dest, src.intersection(dest)

    def _highlight(diff):
        return pygments.highlight(diff, DiffLexer(), html_formatter)

    packages_added, packages_removed, packages_same = add_rm_chg(set(src_profile.include_packages.split()),
                                                                 set(dest_profile.include_packages.split()))

    packages_old = list(packages_removed) + list(packages_same)
    packages_new = list(packages_added) + list(packages_same)
    packages_diff = _highlight("\n".join(unified_diff(packages_old, packages_new)))

    files_added, files_removed, files_changed = add_rm_chg(set(src_profile.include_files),
                                                           set(dest_profile.include_files))

    for filename in files_changed.copy():
        if src_profile.include_files[filename] == dest_profile.include_files[filename]:
            files_changed.remove(filename)

    def highlight_diff(filename):
        out = "\n".join(unified_diff(src_profile.include_files.get(filename, "").splitlines(),
                                     dest_profile.include_files.get(filename, "").splitlines(),
                                     filename, filename))
        return _highlight(out)

    files_changed = [(filename, highlight_diff(filename)) for filename in files_changed]
    files_added = [(filename, highlight_diff(filename)) for filename in files_added]
    files_removed = [(filename, highlight_diff(filename)) for filename in files_removed]

    return render(request, "firmcreator/diff.html", {
        'style': style,
        'files_added': files_added,
        'files_changed': files_changed,
        'files_removed': files_removed,
        'packages_diff': packages_diff,
        'inverse_diff': reverse("fwprofile-diff", args=(dest_profile.slug, src_profile.slug)),

    })


class FwJobDetailView(DetailView):
    model = FwJob
    queryset = FwJob.objects.all()
