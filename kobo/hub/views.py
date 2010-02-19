# -*- coding: utf-8 -*-


import os

from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.generic.list_detail import object_detail
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse

from kobo.django.views.generic import object_list
from kobo.hub.models import Task, Worker, Channel, Arch
from kobo.hub.forms import TaskSearchForm


def user_list(request):
    args = {
        "queryset": User.objects.order_by("username"),
        "allow_empty": True,
        "paginate_by": 50,
        "template_name": "user/list.html",
        "template_object_name": "usr",
#        "extra_context": {
#            "search_form": search_form,
#        }
    }

    return object_list(request, **args)


def user_detail(request, id):
    user = get_object_or_404(User, id=id)
    dict = {
        "queryset": User.objects,
        "object_id": id,
        "template_object_name": "usr",
        "template_name": "user/detail.html",
        "extra_context": {
            "tasks": Task.objects.filter(owner=user).count(),
        }
    }

    return object_detail(request, **dict)


def worker_list(request):
    args = {
        "queryset": Worker.objects.order_by("name"),
        "allow_empty": True,
        "paginate_by": 50,
        "template_name": "worker/list.html",
        "template_object_name": "worker",
#        "extra_context": {
#            "search_form": search_form,
#        }
    }

    return object_list(request, **args)


def worker_detail(request, id):
    dict = {
        "queryset": Worker.objects.select_related(),
        "object_id": id,
        "template_object_name": "worker",
        "template_name": "worker/detail.html",
    }

    return object_detail(request, **dict)


def channel_list(request):
    args = {
        "queryset": Channel.objects.order_by("name"),
        "allow_empty": True,
        "paginate_by": 50,
        "template_name": "channel/list.html",
        "template_object_name": "channel",
#        "extra_context": {
#            "search_form": search_form,
#        }
    }

    return object_list(request, **args)


def channel_detail(request, id):
    channel = get_object_or_404(Channel, id=id)
    dict = {
        "queryset": Channel.objects,
        "object_id": id,
        "template_object_name": "channel",
        "template_name": "channel/detail.html",
        "extra_context": {
            "worker_list": Worker.objects.filter(channels__name=channel.name),
        }
    }

    return object_detail(request, **dict)


def arch_list(request):
    args = {
        "queryset": Arch.objects.order_by("name"),
        "allow_empty": True,
        "paginate_by": 50,
        "template_name": "arch/list.html",
        "template_object_name": "arch",
#        "extra_context": {
#            "search_form": search_form,
#        }
    }

    return object_list(request, **args)


def arch_detail(request, id):
    arch = get_object_or_404(Arch, id=id)
    dict = {
        "queryset": Arch.objects,
        "object_id": id,
        "template_object_name": "arch",
        "template_name": "arch/detail.html",
        "extra_context": {
            "worker_list": Worker.objects.filter(arches__name=arch.name),
        }
    }

    return object_detail(request, **dict)


def task_list(request, state):
    search_form = TaskSearchForm(request.GET)

    args = {
        "queryset": Task.objects.filter(state__in=state, parent__isnull=True).filter(search_form.get_query(request)).order_by("-dt_finished", "id").defer("result", "args").select_related("owner", "worker"),
        "allow_empty": True,
        "paginate_by": 50,
        "template_name": "task/list.html",
        "template_object_name": "task",
        "extra_context": {
            "search_form": search_form,
        }
    }

    return object_list(request, **args)


def task_detail(request, id):
    task = get_object_or_404(Task, id=id)

    logs = []
    for i in task.logs.list:
        if request.user.is_superuser:
            logs.append(i)
            continue
        if not os.path.basename(i).startswith("traceback"):
            logs.append(i)
    logs.sort(lambda x, y: cmp(os.path.split(x), os.path.split(y)))

    c = {
	"task_list": task.subtasks(),
	"logs": logs,
    }

    dict = {
        "queryset": Task.objects.select_related(),
        "object_id": id,
        "template_object_name": "task",
        "template_name": "task/detail.html",
        "extra_context": c,
    }

    return object_detail(request, **dict)


def task_log(request, id, log_name):
    """
    IMPORTANT: reverse to 'task/log-json' *must* exist
    """
    if os.path.basename(log_name).startswith("traceback") and not request.user.is_superuser:
        return HttpResponseForbidden()

    task = get_object_or_404(Task, id=id)
    offset = int(request.GET.get("offset", 0))
    content = task.logs[log_name][offset:]

    if request.GET.get("format") == "txt":
        response = HttpResponse(mimetype='text/plain')
        response['Content-Disposition'] = 'attachment; filename=%s' % os.path.basename(log_name)
        response.write(content)
        return response

    context = {
        "offset": offset + len(content) + 1,
        "task_finished": task.is_finished() and 1 or 0,
        "content": content,
        "log_name": log_name,
        "task": task,
        "json_url": reverse("task/log-json", args=[id, log_name]),
    }

    return render_to_response("task/log.html", context, context_instance=RequestContext(request))


def task_log_json(request, id, log_name):
    if os.path.basename(log_name).startswith("traceback") and not request.user.is_superuser:
        return HttpResponseForbidden(mimetype="application/json")

    task = get_object_or_404(Task, id=id)
    offset = int(request.GET.get("offset", 0))
    content = task.logs[log_name][offset:]

    result = {
        "new_offset": offset + len(content),
        "task_finished": task.is_finished() and 1 or 0,
        "content": content,
    }

    return HttpResponse(simplejson.dumps(result), mimetype="application/json")
