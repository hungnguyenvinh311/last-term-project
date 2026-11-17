import os
import httpx
from dotenv import dotenv_values
from Model.application.config.settings import ROOT
from Model.application.errors import AIUnavailable,DomainError

class SpeechTranscriberService:
    def __init__(self,config_provider=None):
        self.config_provider=config_provider or (lambda:dotenv_values(ROOT/'.env.app'))
    def transcribe(self,content,filename):
        if not content or len(content)>20*1024*1024: raise DomainError('Audio phải có dung lượng từ 1 byte đến 20 MB')
        if not filename.lower().endswith(('.webm','.wav','.mp3','.mp4','.m4a','.ogg')): raise DomainError('Định dạng audio không hỗ trợ')
        config=self.config_provider()
        key=(config.get('APP_OPENAI_API_KEY') or os.getenv('APP_OPENAI_API_KEY') or '').strip()
        if not key: raise AIUnavailable('Chưa cấu hình APP_OPENAI_API_KEY cho phiên âm; bạn có thể nhập văn bản.')
        base=(config.get('APP_TRANSCRIBE_BASE') or os.getenv('APP_TRANSCRIBE_BASE','https://api.openai.com/v1')).rstrip('/')
        if not base.startswith('https://'): raise AIUnavailable('Transcription provider requires HTTPS')
        try:
            with httpx.Client(timeout=60) as client:
                response=client.post(base+'/audio/transcriptions',headers={'Authorization':f'Bearer {key}'},files={'file':(filename,content)},data={'model':config.get('APP_TRANSCRIBE_MODEL') or os.getenv('APP_TRANSCRIBE_MODEL','gpt-transcribe'),'language':'vi'})
                response.raise_for_status();text=response.json()['text'].strip()
            if not text: raise AIUnavailable('Không nhận dạng được nội dung audio')
            return text
        except httpx.HTTPStatusError as exc:
            status=exc.response.status_code
            try: code=exc.response.json().get('error',{}).get('code')
            except ValueError: code=None
            if status==401:
                message='API key OpenAI đã hết hạn hoặc không hợp lệ. Hãy thay APP_OPENAI_API_KEY trong .env.app bằng key còn hoạt động.'
            elif status==429:
                message='Tài khoản OpenAI chưa đủ hạn mức/thanh toán cho API phiên âm.' if code=='insufficient_quota' else 'OpenAI đang giới hạn lượt gọi. Vui lòng thử lại sau.'
            elif status in {403,404} or code=='model_not_found':
                message='Tài khoản chưa có quyền dùng model phiên âm đã cấu hình. Hãy kiểm tra APP_TRANSCRIBE_MODEL.'
            elif status==400:
                message='OpenAI không chấp nhận bản ghi hoặc cấu hình phiên âm. Hãy ghi lại audio và kiểm tra model.'
            else: message='Dịch vụ phiên âm OpenAI đang lỗi. Vui lòng thử lại sau.'
            raise AIUnavailable(message) from None
        except httpx.TimeoutException: raise AIUnavailable('Phiên âm quá thời gian chờ. Hãy thử bản ghi ngắn hơn.') from None
        except (httpx.HTTPError,KeyError,ValueError): raise AIUnavailable('Phiên âm không thành công; hãy kiểm tra kết nối hoặc nhập văn bản.') from None
