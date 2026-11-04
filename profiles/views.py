import io

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm

from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import services
from .forms import BookmarkNoteForm
from .models import BookmarkedProfile


def search(request):
    query = request.GET.get("q", "").strip()
    context = {"query": query, "profile": None, "repos": [], "is_bookmarked": False}
    if query:
        try:
            profile = services.get_user(query)
            context["profile"] = profile
            context["repos"] = services.get_repos(profile["username"])
            if request.user.is_authenticated:
                context["is_bookmarked"] = BookmarkedProfile.objects.filter(
                    user=request.user, username__iexact=profile["username"]
                ).exists()
        except services.GitHubError as exc:  # catches all 4 error types
            messages.error(request, str(exc))

    return render(request, "profiles/search.html", context)


@login_required
@require_POST
def bookmark(request, username):
    try:
        data = services.get_user(username)
    except services.GitHubError as exc:
        messages.error(request, str(exc))
        return redirect("search")

    lookup = data.pop("username")
    _, created = BookmarkedProfile.objects.get_or_create(
        user=request.user, username=lookup, defaults=data
    )
    if created:
        messages.success(request, f"Bookmarked {lookup}.")
    else:
        messages.info(request, f"{lookup} is already bookmarked.")
    return redirect("bookmarks")


@login_required
def bookmark_list(request):
    items = BookmarkedProfile.objects.filter(user=request.user)
    return render(request, "profiles/bookmarks.html", {"bookmarks": items})


@login_required
@require_POST
def bookmark_delete(request, pk):
    item = get_object_or_404(BookmarkedProfile, pk=pk, user=request.user)
    item.delete()
    messages.success(request, "Bookmark removed.")
    return redirect("bookmarks")


@login_required
@require_POST
def bookmark_update_note(request, pk):
    item = get_object_or_404(BookmarkedProfile, pk=pk, user=request.user)
    form = BookmarkNoteForm(request.POST, instance=item)
    if form.is_valid():
        form.save()
        messages.success(request, f"Note updated for @{item.username}.")
    else:
        messages.error(request, "Could not update note.")
    return redirect("bookmarks")


def signup(request):
    if request.user.is_authenticated:
        return redirect("search")
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to GitHub Profile Viewer, {user.username}!")
            return redirect("search")
    else:
        form = UserCreationForm()
    return render(request, "registration/signup.html", {"form": form})

from django.http import HttpResponse, HttpResponseBadRequest
from .temp import render_card
def visualize(request):
    username=request.GET.get("username", "").strip()
    if not username:
        return HttpResponseBadRequest("Missing 'username' parameter.")
    try:
        profile = services.get_user(username)
        repos = services.get_repos(profile["username"])
        img = render_card(
            username=profile["username"],
            name=profile.get("name", ""),
            bio=profile.get("bio", ""),
            public_repos=profile.get("public_repos", 0),
            followers=profile.get("followers", 0),
            following=profile.get("following", 0),
            avatar_url=profile.get("avatar_url", ""),
            repos=repos,
        )
    except services.GitHubError as exc:
        return HttpResponseBadRequest(str(exc))
    buffer=io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return HttpResponse(buffer.getvalue(), content_type="image/png")