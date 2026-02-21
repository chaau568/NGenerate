from analysis.models import CharacterProfileAnalysis

def save_character_profiles(novel, ai_result):
    for c in ai_result:
        CharacterProfileAnalysis.objects.update_or_create(
            novel=novel,
            name=c["name"],
            defaults={
                "sex": c.get("sex"),
                "age": c.get("age"),
                "appearance": c.get("appearance"),
                "base_personality": c.get("base_personality"),
                "outfit": c.get("outfit"),
                "race": c.get("race"),
            }
        )
