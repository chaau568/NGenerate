# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.response import Response
# from rest_framework import status
# from django.shortcuts import get_object_or_404

# from django.core.exceptions import ValidationError

# from analysis.pricing import CreditPricing
# from novels.models import Novel, Chapter
# from asset.models import CharacterImage
# from .models import AnalysisSession, SentenceAnalysis, IllustrationAnalysis, ProcessingStep

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def prepare_analysis_preview(request):
#     novel_id = request.data.get('novel_id')
#     chapter_ids = request.data.get('chapter_ids', [])

#     novel = get_object_or_404(Novel, id=novel_id, user=request.user)

#     chapters = Chapter.objects.filter(
#         id__in=chapter_ids,
#         novel=novel
#     ).order_by('order')

#     if not chapters.exists():
#         return Response(
#             {"error": "No chapters selected"},
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     # 1. default analysis name
#     default_name = (
#         f"{novel.title} "
#         f"# {chapters.first().order} - # {chapters.last().order}"
#     )

#     # 2. analyze credits
#     analyze_credits = chapters.count() * CreditPricing.CHAPTER_UNIT

#     return Response({
#         "novel": {
#             "id": novel.id,
#             "title": novel.title,
#         },
#         "analysis": {
#             "name": default_name,
#             "chapter_count": chapters.count(),
#             "credits_per_chapter": 5,
#             "analyze_credits": analyze_credits,
#         },
#         "chapters": [
#             {
#                 "id": c.id,
#                 "order": c.order,
#                 "title": c.title,
#             }
#             for c in chapters
#         ]
#     })
    
# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def start_analysis(request):
#     novel_id = request.data.get('novel_id')
#     chapter_ids = request.data.get('chapter_ids')
#     name = request.data.get('name')

#     novel = get_object_or_404(Novel, id=novel_id, user=request.user)
#     chapters = Chapter.objects.filter(id__in=chapter_ids, novel=novel)

#     if not chapters.exists():
#         return Response(
#             {"error": "No chapters selected"},
#             status=status.HTTP_404_NOT_FOUND
#         )

#     analyze_credits = chapters.count() * 5

#     session = AnalysisSession.objects.create(
#         novel=novel,
#         name=name,
#         analyze_credits=analyze_credits
#     )
#     session.chapters.set(chapters)

#     steps = [
#         ('analysis', 'text_analysis'),
#         ('analysis', 'character_extraction'),
#         ('analysis', 'illustration_gen'),
#         ('generation', 'voice_gen'),
#         ('generation', 'image_gen'),
#         ('generation', 'video_compilation'),
#     ]

#     ProcessingStep.objects.bulk_create([
#         ProcessingStep(
#             analysis_session=session,
#             phase=phase,
#             name=step_name,
#             order=i + 1
#         )
#         for i, (phase, step_name) in enumerate(steps)
#     ])

#     try:
#         session.start_analysis()
#     except ValidationError as e:
#         return Response(
#             {"error": e.message},
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     return Response({
#         "analyze_session_id": session.id,
#         "analyze_credits": session.analyze_credits,
#         "status": session.status
#     }, status=status.HTTP_201_CREATED)

# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def analysis_status(request, session_id):
#     session = get_object_or_404(
#         AnalysisSession,
#         id=session_id,
#         novel__user=request.user
#     )

#     steps = session.process_step.all()

#     return Response({
#         "status": session.status,
#         "analysis_progress": session.analysis_progress,
#         "generation_progress": session.generation_progress,
#         "current_step": steps.filter(status='processing').first().name
#         if steps.filter(status='processing').exists() else None,
#         "steps": [
#             {
#                 "name": s.name,
#                 "phase": s.phase,
#                 "status": s.status
#             }
#             for s in steps
#         ]
#     })

# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def generation_summary(request, session_id):
#     session = get_object_or_404(
#         AnalysisSession,
#         id=session_id,
#         novel__user=request.user
#     )

#     # 1. Sentence → voice (10 sentence = 1 credit)
#     sentence_count = SentenceAnalysis.objects.filter(
#         analysis_session=session
#     ).count()
#     sentence_credits = CreditPricing.sentence_to_credit(sentence_count=sentence_count)

#     # 2. Character images (1 image = 5 credits)
#     character_image_count = CharacterImage.objects.filter(
#         character_profile__novel=session.novel
#     ).count()
#     character_image_credits = character_image_count * CreditPricing.CHARACTER_IMAGE

#     # 3. Scene illustrations (1 chapter = 1 illustration = 10 credits)
#     illustration_count = IllustrationAnalysis.objects.filter(
#         analysis_session=session
#     ).count()
#     illustration_credits = illustration_count * CreditPricing.SCENE_IMAGE

#     total_credits = (
#         sentence_credits +
#         character_image_credits +
#         illustration_credits
#     )

#     return Response({
#         "analysis_session": {
#             "id": session.id,
#             "name": session.name
#         },
#         "summary": {
#             "sentence_assets": {
#                 "count": sentence_count,
#                 "credits_per_unit": "10 sentences = 1 credit",
#                 "credits": sentence_credits,
#             },
#             "character_images": {
#                 "count": character_image_count,
#                 "credits_per_asset": 5,
#                 "credits": character_image_credits,
#             },
#             "scene_images": {
#                 "count": illustration_count,
#                 "credits_per_asset": 10,
#                 "credits": illustration_credits,
#             },
#             "total_credits": total_credits,
#         }
#     })

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def start_generation(request, session_id):
#     session = get_object_or_404(
#         AnalysisSession,
#         id=session_id,
#         novel__user=request.user
#     )

#     try:
#         session.start_generation()
#     except ValidationError as e:
#         return Response(
#             {"error": e.message},
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     return Response({
#         "status": session.status,
#         "generation_progress": session.generation_progress
#     })
