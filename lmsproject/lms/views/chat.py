from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
import requests
import json

OLLAMA_API_URL = "http://localhost:11434/api/generate"  # Default Ollama API endpoint

@login_required
def chat_view(request):
    """Render the chat interface"""
    return render(request, 'lms/student/ai_chat.html')

@login_required
@csrf_exempt
def chat_api(request):
    """Handle chat API requests"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)

    try:
        data = json.loads(request.body)
        user_message = data.get('message', '')

        if not user_message:
            return JsonResponse({'error': 'Message is required'}, status=400)

        # Prepare the context for the AI
        context = f"You are an AI learning assistant helping a student. The student's question is: {user_message}"

        # Make request to Ollama API
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": "mistral",  # You can change this to any model you have installed
                "prompt": context,
                "stream": False
            }
        )

        if response.status_code == 200:
            ai_response = response.json().get('response', '')
            return JsonResponse({'response': ai_response})
        else:
            return JsonResponse(
                {'error': 'Failed to get response from AI'},
                status=500
            )

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except requests.RequestException as e:
        return JsonResponse(
            {'error': f'Failed to connect to Ollama: {str(e)}'},
            status=500
        ) 