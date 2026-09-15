from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.models import UserProfile
import random
from django.utils import timezone
from .models import Question,Score,Book
from django.http import HttpResponse, request
from accounts.utils import check_badges


def calculate_xp(score, total, difficulty='moyen'):
    score = int(score or 0)
    total = int(total or 0)
    if total <= 0:
        return 0

    multipliers = {'facile': 1, 'moyen': 1.5, 'difficile': 2, 'expert': 3}
    xp = int(score * 10 * multipliers.get(str(difficulty).lower(), 1))
    if score == total:
        xp += 50
    return max(xp, 0)


def check_and_award_badges(user, profile):
    return check_badges(user, profile)


def splash(request):
    top_scores = Score.objects.select_related("user").order_by("-score")[:4]
    return render(request, "quiz/splash.html", {
        "top_scores": top_scores,
    })


def home(request):
    books=Book.objects.all()
    top=Score.objects.select_related("user").order_by("-score")[:5]
    return render(request,"quiz/home.html",{"books":books,"top_scores":top})

@login_required
def start_quiz(request):
    if request.method=="POST":
        difficulty=request.POST.get("difficulty","moyen")
        book_id=request.POST.get("book","")
        count=int(request.POST.get("count",10))
        qs=Question.objects.filter(difficulty=difficulty)
        if book_id:
            qs=qs.filter(book_id=book_id)
        questions=random.sample(list(qs),min(count,qs.count()))
        request.session["questions"]=[q.id for  q in questions ]
        request.session["index"]=0
        request.session["score"]=0
        request.session["difficulty"]=difficulty
        request.session["answers"]=[]
        return  redirect("question")
    books=Book.objects.all()
    return render(request,"quiz/start.html",{"books":books})

@login_required
def question_view(request):
    ids = request.session.get("questions", [])
    index = request.session.get("index", 0)

    if not ids or index >= len(ids):
        return redirect("result")

    q = get_object_or_404(Question, id=ids[index])

    choices = {
        "A": q.option1,
        "B": q.option2,
        "C": q.option3,
        "D": q.option4,
    }
    options = list(choices.values())
    random.shuffle(options)

    correct_text = q.correct_answer
    if q.correct_answer in choices.values():
        correct_text = q.correct_answer
    else:
        correct_text = next((value for value in choices.values() if value == q.correct_answer), q.correct_answer)

    if request.method == "POST":
        answer = (request.POST.get("answer", "") or "").strip()
        answer_upper = answer.upper()

        correct_key = next((key for key, value in choices.items() if value == correct_text), None)
        correct_answer_key = correct_key or next((key for key, value in choices.items() if value == q.correct_answer), None)

        is_correct = (
            answer_upper == correct_answer_key or
            answer.lower() == correct_text.lower() or
            answer_upper in choices and choices[answer_upper] == correct_text
        )

        if is_correct:
            request.session["score"] = request.session.get("score", 0) + 1

        answers = request.session.get("answers", [])
        answers.append({
            "question": q.question,
            "user_answer": answer,
            "correct_answer": q.correct_answer,
            "correct_answer_text": correct_text,
            "correct_answer_key": correct_answer_key,
            "is_correct": is_correct,
            "explanation": q.explanation,
        })

        request.session["answers"] = answers
        request.session["index"] = index + 1

        return redirect("question")

    return render(request, "quiz/question.html", {
        "question": q,
        "options": options,
        "index": index + 1,
        "total": len(ids),
        "progress": round(index / len(ids) * 100),
    })
    

@login_required
def result_view(request):
    score = request.session.get("score", 0)
    total = len(request.session.get("questions", []))
    diff  = request.session.get("difficulty", "moyen")
    xp = calculate_xp(score, total, diff)

    new_badges = []

    Score.objects.create(
        user=request.user, score=score,
        total=total, difficulty=diff, xp_earned=xp
    )

    p = request.user.profile
    p.total_xp += xp
    p.total_questions_answered += total
    p.total_correct += score
    p.save()

    # ── Vérifier les badges APRÈS avoir mis à jour le profil ──
    new_badges = check_and_award_badges(request.user, p)

    return render(request, "quiz/result.html", {
        "score": score, "total": total, "xp": xp,
        "answers": request.session.get("answers", []),
        "percentage": round(score/total*100) if total else 0,
        "new_badges": new_badges,
    })


def leaderboard(request):
    top_scores = Score.objects.select_related("user").order_by("-score", "-created_at")[:20]
    top_users = UserProfile.objects.select_related("user").order_by("-total_xp")[:10]
    return render(request, "quiz/leaderboard.html", {
        "top_scores": top_scores,
        "top_users": top_users,
    })