import openai
from django.conf import settings


class WhisperService:
    """
    Transcribe audio a texto usando OpenAI Whisper API.
    Compatible con: mp3, mp4, mpeg, mpga, m4a, wav, webm.
    Máximo 25 MB por archivo.
    """

    def __init__(self):
        if settings.OPENAI_API_KEY:
            self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            self.client = None

    def transcribe(self, audio_file_path: str, language: str = 'es') -> dict:
        """
        Retorna: {'transcription': str, 'duration': float, 'success': bool}
        """
        if not self.client:
            return {
                'transcription': '',
                'success': False,
                'error': 'OpenAI API key not configured'
            }

        try:
            with open(audio_file_path, 'rb') as audio_file:
                response = self.client.audio.transcriptions.create(
                    model='whisper-1',
                    file=audio_file,
                    language=language,
                    response_format='verbose_json',  # Incluye duración y segmentos
                )
            return {
                'transcription': response.text,
                'duration': getattr(response, 'duration', 0),
                'success': True,
                'segments': getattr(response, 'segments', []),
            }
        except Exception as e:
            return {
                'transcription': '',
                'success': False,
                'error': str(e)
            }
