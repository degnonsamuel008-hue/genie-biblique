from .models import Badge, UserBadge

def check_badges(user, profile):
    all_badges   = Badge.objects.all()
    already_earned = set(
        UserBadge.objects.filter(user=user).values_list("badge_id", flat=True))
    new_badges = []
    for badge in all_badges:
        if badge.id in already_earned: continue
        value = getattr(profile, badge.condition_key, 0)
        if value >= badge.condition_value:
            UserBadge.objects.create(user=user, badge=badge)
            profile.total_xp += badge.xp_reward
            profile.save()
            new_badges.append(badge)
    return new_badges
        