from analysis.services.text_analysis import save_sentence_analysis
from analysis.services.character_analysis import save_character_profiles
from analysis.services.illustration_analysis import save_illustrations

def run_analysis_pipeline(session, ai_client):
    steps = session.process_step.filter(phase="analysis")

    try:
        # STEP 1: Text Analysis
        step = steps.get(name="text_analysis")
        step.start_step()

        text_result = ai_client.analyze_text(session)
        save_sentence_analysis(session, text_result)

        step.complete_step()

        # STEP 2: Character Extraction
        step = steps.get(name="character_extraction")
        step.start_step()

        character_result = ai_client.extract_characters(session)
        save_character_profiles(session.novel, character_result)

        step.complete_step()

        # STEP 3: Illustration Prompt
        step = steps.get(name="illustration_gen")
        step.start_step()

        illustration_result = ai_client.generate_illustrations(session)
        save_illustrations(session, illustration_result)

        step.complete_step()

        session.complete_analysis()

    except Exception as e:
        session.fail(str(e))
        raise
