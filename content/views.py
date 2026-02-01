from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PostForm
from .models import Post


@login_required
def post_list(request):
    posts = Post.objects.filter(author=request.user)
    return render(request, "content/post_list.html", {"posts": posts})


@login_required
def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id, author=request.user)
    return render(request, "content/post_detail.html", {"post": post})


@login_required
def post_create(request):
    if request.method == "POST":
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect("content:post_detail", post_id=post.id)
    else:
        form = PostForm()
    return render(request, "content/post_form.html", {"form": form, "mode": "create"})


@login_required
def post_update(request, post_id):
    post = get_object_or_404(Post, id=post_id, author=request.user)
    if request.method == "POST":
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            return redirect("content:post_detail", post_id=post.id)
    else:
        form = PostForm(instance=post)
    return render(request, "content/post_form.html", {"form": form, "mode": "update", "post": post})


@login_required
def post_delete(request, post_id):
    post = get_object_or_404(Post, id=post_id, author=request.user)
    if request.method == "POST":
        post.delete()
        return redirect("content:post_list")
    return render(request, "content/post_confirm_delete.html", {"post": post})
