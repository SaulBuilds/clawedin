from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CompanyForm
from .models import Company


@login_required
def company_create(request):
    if request.method == "POST":
        form = CompanyForm(request.POST)
        if form.is_valid():
            company = form.save(commit=False)
            company.owner = request.user
            company.save()
            return redirect("companies:company_detail", slug=company.slug)
    else:
        form = CompanyForm()

    return render(request, "companies/company_form.html", {"form": form})


def company_detail(request, slug):
    company = get_object_or_404(Company, slug=slug)
    return render(request, "companies/company_detail.html", {"company": company})
