from pathlib import Path

def publish_video(video_path:str, access_token:str, title:str, description:str='', privacy_status:str='private', tags=None):
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError as e:
        raise RuntimeError('YouTube publishing dependencies are not installed. Run: pip install google-api-python-client google-auth') from e
    if not Path(video_path).exists(): raise RuntimeError('Video file not found')
    if privacy_status not in {'private','unlisted','public'}: raise RuntimeError('privacy_status must be private, unlisted or public')
    creds=Credentials(token=access_token,scopes=['https://www.googleapis.com/auth/youtube.upload'])
    youtube=build('youtube','v3',credentials=creds,cache_discovery=False)
    body={'snippet':{'title':title,'description':description,'tags':tags or [],'categoryId':'22'},'status':{'privacyStatus':privacy_status}}
    media=MediaFileUpload(video_path,chunksize=8*1024*1024,resumable=True)
    request=youtube.videos().insert(part='snippet,status',body=body,media_body=media)
    response=None
    while response is None:
        _,response=request.next_chunk()
    return {'video_id':response.get('id'),'url':f"https://www.youtube.com/watch?v={response.get('id')}"}
