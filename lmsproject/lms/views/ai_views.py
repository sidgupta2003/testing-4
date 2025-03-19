from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from ..utils.ai_utils import ai_helper

@login_required
def ai_assistance(request):
    """View to handle AI assistance requests"""
    if request.method == 'POST':
        action = request.POST.get('action')
        text = request.POST.get('text', '')
        
        if action == 'sentiment':
            result = ai_helper.analyze_sentiment(text)
            return JsonResponse(result)
            
        elif action == 'generate':
            prompt = text
            result = ai_helper.generate_text(prompt)
            return JsonResponse({'generated_text': result})
            
        elif action == 'summarize':
            result = ai_helper.summarize_text(text)
            return JsonResponse({'summary': result})
            
        elif action == 'question':
            context = request.POST.get('context', '')
            question = text
            result = ai_helper.answer_question(context, question)
            return JsonResponse(result)
            
    return render(request, 'lms/ai_assistance.html') 