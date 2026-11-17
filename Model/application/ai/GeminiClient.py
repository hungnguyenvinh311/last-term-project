from time import monotonic
"""Small Gemini REST adapter shared by transcription and intent extraction.

Only this adapter knows Google's wire format. Never puts a key in a URL/log.
"""
import os
import re
import httpx
from dotenv import dotenv_values
from Model.application.config.settings import ROOT
from Model.application.errors import AIUnavailable

DEFAULT_MODEL='gemini-3.1-flash-lite'

def app_config():
    return dotenv_values(ROOT/'.env.app')

class GeminiClient:
    def __init__(self,config_provider=None,client_factory=None):
        self._unavailable={}
        self.config_provider=config_provider or app_config
        self.client_factory=client_factory or httpx.Client

    def configuration(self,task):
        config=self.config_provider()
        def value(name,default=''):
            return str(config.get(name) or os.getenv(name) or default).strip()
        key=value('APP_GEMINI_API_KEY') or value('GEMINI_API_KEY')
        model=value('APP_GEMINI_TRANSCRIBE_MODEL' if task=='transcription' else 'APP_GEMINI_INTENT_MODEL',DEFAULT_MODEL)
        if not re.fullmatch(r'gemini-[A-Za-z0-9._-]+',model):
            raise AIUnavailable('Tên model Gemini không hợp lệ trong .env.app.')
        return key,model

    def generate(self,task,parts,instruction,schema):
        key,model=self.configuration(task)
        if not key:
            raise AIUnavailable('Chưa cấu hình APP_GEMINI_API_KEY trong .env.app. Hãy tạo key tại Google AI Studio.')
        circuit=(key,model,task)
        if monotonic()<self._unavailable.get(circuit,0):
            raise AIUnavailable('Gemini tạm thời không khả dụng; hệ thống đang chờ trước khi thử lại.')
        payload={
            'systemInstruction':{'parts':[{'text':instruction}]},
            'contents':[{'role':'user','parts':parts}],
            'generationConfig':{'temperature':0,'maxOutputTokens':2048,
                                'responseMimeType':'application/json','responseJsonSchema':schema},
        }
        try:
            with self.client_factory(timeout=90 if task=='transcription' else 12) as client:
                response=client.post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
                                     headers={'x-goog-api-key':key},json=payload)
                response.raise_for_status()
                data=response.json()
            candidates=data.get('candidates') or []
            if not candidates or candidates[0].get('finishReason')!='STOP':
                raise AIUnavailable('Gemini chưa trả về kết quả hoàn chỉnh hoặc đã chặn nội dung. Hãy thử lại yêu cầu.')
            answer=''.join(p.get('text','') for p in candidates[0].get('content',{}).get('parts',[]) if not p.get('thought'))
            if not answer.strip(): raise AIUnavailable('Gemini trả về kết quả trống.')
            return answer
        except httpx.HTTPStatusError as exc:
            status=exc.response.status_code
            if status in {429,500,502,503,504}: self._unavailable[circuit]=monotonic()+30
            if status in {401,403}: message='Gemini từ chối API key hoặc quyền truy cập. Hãy kiểm tra APP_GEMINI_API_KEY và project Google AI Studio.'
            elif status==429: message='Gemini đã hết hạn mức hoặc đang giới hạn lượt gọi. Vui lòng đợi quota được cấp lại hoặc kiểm tra hạn mức trong AI Studio.'
            elif status==404: message='Không tìm thấy model Gemini hoặc project chưa có quyền dùng model. Hãy kiểm tra APP_GEMINI_TRANSCRIBE_MODEL / APP_GEMINI_INTENT_MODEL.'
            elif status==400: message='Gemini không chấp nhận key, định dạng dữ liệu hoặc cấu hình model. Hãy kiểm tra cấu hình Gemini và thử lại bản ghi/yêu cầu.'
            else: message='Dịch vụ Gemini đang lỗi. Vui lòng thử lại sau.'
            raise AIUnavailable(message) from None
        except httpx.TimeoutException:
            raise AIUnavailable('Gemini quá thời gian chờ. Hãy dùng bản ghi/yêu cầu ngắn hơn hoặc thử lại.') from None
        except (httpx.HTTPError,ValueError,TypeError,AttributeError):
            raise AIUnavailable('Không kết nối hoặc đọc được phản hồi Gemini. Vui lòng thử lại.') from None
