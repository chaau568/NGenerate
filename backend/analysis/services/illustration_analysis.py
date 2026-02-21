from analysis.models import IllustrationAnalysis

def save_illustrations(session, ai_result):
    bulk = []

    for item in ai_result:
        chapter = session.chapters.get(id=item["chapter_id"])

        bulk.append(
            IllustrationAnalysis(
                analysis_session=session,
                chapter=chapter,
                positive_prompt=item["positive_prompt"],
                negative_prompt=item.get("negative_prompt", "")
            )
        )

    IllustrationAnalysis.objects.bulk_create(bulk)
