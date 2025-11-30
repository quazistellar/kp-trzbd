def theme_context(request):
    theme = 'light'
    if request.user.is_authenticated and request.user.profile_theme:
        theme = request.user.profile_theme
    return {'user_theme': theme}