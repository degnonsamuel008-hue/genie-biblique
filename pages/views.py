from django.shortcuts import render
from django.shortcuts import render, redirect
from django.contrib import messages

from .forms import ContactForm


def about(request):
    return render(request, "pages/about.html")


def faq(request):
    return render(request, "pages/faq.html")


def terms(request):
    return render(request, "pages/terms.html")


def privacy(request):
    return render(request, "pages/privacy.html")


def contact(request):

    if request.method == "POST":

        form = ContactForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Votre message a été envoyé avec succès. Nous vous répondrons très bientôt."
            )

            return redirect("contact")

    else:

        form = ContactForm()

    return render(
        request,
        "pages/contact.html",
        {
            "form": form
        }
    )
