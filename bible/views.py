from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import DailyReading,ReadingProgress

@login_required
def plan_view(request):
    today_num=timezone.now().timetuple().tm_yday
    reading=DailyReading.objects.filter(day_number=today_num).first()
    progress=ReadingProgress.objects.filter(user=request.user).select_related("reading")
    done_ids=[p.reading_id for p in progress if p.completed]
    all_days=DailyReading.objects.all()
    total_done = len(done_ids)
    progress_pct = round(total_done * 100 / 365)
    return render(request,"bible/plan.html",
        {"today":reading,
        "today_num":today_num,
        "done_ids":done_ids,
        "all_days":all_days,
        "total_done":total_done,
        "progress_pct":progress_pct}
    )

@login_required
def mark_done(request,day_number):
    reading=DailyReading.objects.get(day_number=day_number)
    prog,_= ReadingProgress.objects.get_or_create(user=request.user,reading=reading)
    prog.completed = True
    prog.completed_at = timezone.now()
    prog.save()
    profile=request.user.profile
    profile.streak_days +=1
    profile.save()
    return redirect("bible_plan")

