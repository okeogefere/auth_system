from base64 import urlsafe_b64decode
# from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.shortcuts import render, redirect
from django.urls import reverse
from users.models import User
from users.forms import CustomUserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserProfileForm

#send mail and account verification
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.conf import settings
from django.db import transaction



@transaction.atomic
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # User is not active until email is confirmed
            user.save()

            # Generate confirmation token
            token = default_token_generator.make_token(user)

            # Ensure user.pk and token are not empty
            if user.pk and token:
                # Build confirmation URL
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                confirm_url = reverse('verify_email', kwargs={'uidb64': uidb64, 'token': token})
                confirmation_link = f'http://{get_current_site(request).domain}{confirm_url}'

                # Send confirmation email
                subject = 'Confirm your email address'
                message = render_to_string('users/verification_email.html', {'user': user, 'confirmation_link': confirmation_link, 'uid': uidb64, 'token': token})
                user_email = user.email
                try:
                    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user_email], html_message=message)
                except Exception as e:
                    messages.error(request, 'Failed to send confirmation email. Please try again later.')
                    user.delete()  # Delete the user if email sending fails
                    return redirect('register')  # Redirect back to registration page

                # Redirect to home after successful registration
                messages.success(request, 'Registration successful. Please check your email for verification.')
                return redirect('home')
            else:
                # Handle case where user.pk or token is empty
                messages.error(request, 'Error occurred while generating confirmation URL.')
                user.delete()  # Delete the user if registration fails
    else:
        form = CustomUserCreationForm()
    return render(request, 'users/register.html', {'form': form})



def user_login(request):
    if request.user.is_authenticated:
        messages.warning(request, 'You are logged in Already')
        return redirect('home')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "You are logged in")
            return redirect('home')
        else:
            messages.warning(request, 'User does not Exist, Create an account')
        
    return render(request, 'users/login.html')

def user_logout(request):
    logout(request)
    return redirect('login')

def verify_email(request, uidb64, token):
    try:
        uid = urlsafe_b64decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return render(request, 'users/verification_success.html')
    else:
        return render(request, 'users/verification_failed.html')

@login_required
def profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'users/profile.html', {'form': form})
