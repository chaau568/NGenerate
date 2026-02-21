from analysis.models import SentenceAnalysis

def save_sentence_analysis(session, ai_result):
    bulk = []

    for chapter_block in ai_result:
        chapter = session.chapters.get(id=chapter_block["chapter_id"])

        for s in chapter_block["sentences"]:
            bulk.append(
                SentenceAnalysis(
                    analysis_session=session,
                    chapter=chapter,
                    sentence_index=s["index"],
                    type=s["type"],
                    emotion=s.get("emotion", "neutral"),
                    sentence=s["sentence"],
                    character_name=s.get("character_name", "")
                )
            )

    SentenceAnalysis.objects.bulk_create(bulk)
