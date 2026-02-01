from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DirectMessageForm, GroupMessageForm, GroupThreadForm, InMailForm
from .models import DirectMessage, GroupThread, InMail


@login_required
def messaging_home(request):
    user = request.user
    context = {
        "dm_count": DirectMessage.objects.filter(
            Q(sender=user) | Q(recipient=user)
        ).count(),
        "inmail_count": InMail.objects.filter(
            Q(sender=user) | Q(recipient=user)
        ).count(),
        "group_count": GroupThread.objects.filter(members=user).distinct().count(),
    }
    return render(request, "messaging/messaging_home.html", context)


@login_required
def dm_list(request):
    messages = (
        DirectMessage.objects.filter(Q(sender=request.user) | Q(recipient=request.user))
        .select_related("sender", "recipient")
        .order_by("-created_at")
    )
    return render(request, "messaging/dm_list.html", {"messages": messages})


@login_required
def dm_detail(request, message_id):
    message = get_object_or_404(
        DirectMessage,
        Q(sender=request.user) | Q(recipient=request.user),
        id=message_id,
    )
    return render(request, "messaging/dm_detail.html", {"message": message})


@login_required
def dm_create(request):
    if request.method == "POST":
        form = DirectMessageForm(request.POST, user=request.user)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            message.save()
            return redirect("messaging:dm_detail", message_id=message.id)
    else:
        form = DirectMessageForm(user=request.user)
    return render(request, "messaging/dm_form.html", {"form": form})


@login_required
def inmail_list(request):
    messages = (
        InMail.objects.filter(Q(sender=request.user) | Q(recipient=request.user))
        .select_related("sender", "recipient")
        .order_by("-created_at")
    )
    return render(request, "messaging/inmail_list.html", {"messages": messages})


@login_required
def inmail_detail(request, message_id):
    message = get_object_or_404(
        InMail,
        Q(sender=request.user) | Q(recipient=request.user),
        id=message_id,
    )
    return render(request, "messaging/inmail_detail.html", {"message": message})


@login_required
def inmail_create(request):
    if request.method == "POST":
        form = InMailForm(request.POST, user=request.user)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            message.save()
            return redirect("messaging:inmail_detail", message_id=message.id)
    else:
        form = InMailForm(user=request.user)
    return render(request, "messaging/inmail_form.html", {"form": form})


@login_required
def group_list(request):
    threads = (
        GroupThread.objects.filter(members=request.user)
        .distinct()
        .prefetch_related("members")
        .order_by("name")
    )
    return render(request, "messaging/group_list.html", {"threads": threads})


@login_required
def group_create(request):
    if request.method == "POST":
        form = GroupThreadForm(request.POST, user=request.user)
        if form.is_valid():
            thread = form.save(commit=False)
            thread.created_by = request.user
            thread.save()
            form.save_m2m()
            thread.members.add(request.user)
            return redirect("messaging:group_detail", thread_id=thread.id)
    else:
        form = GroupThreadForm(user=request.user)
    return render(request, "messaging/group_form.html", {"form": form})


@login_required
def group_detail(request, thread_id):
    thread = get_object_or_404(GroupThread, id=thread_id, members=request.user)
    messages = thread.messages.select_related("sender").order_by("created_at")

    if request.method == "POST":
        form = GroupMessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.thread = thread
            message.sender = request.user
            message.save()
            return redirect("messaging:group_detail", thread_id=thread.id)
    else:
        form = GroupMessageForm()

    context = {
        "thread": thread,
        "messages": messages,
        "form": form,
        "members": thread.members.all().order_by("username"),
    }
    return render(request, "messaging/group_detail.html", context)
