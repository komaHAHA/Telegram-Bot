import telebot
import requests
import os
from moviepy.editor import VideoFileClip
import pvleopard
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from moviepy.video.tools.subtitles import SubtitlesClip
from pytube import YouTube
import re

token = '6702017718:AAE7esbofIF9czK1pPA6myIGreUJRFVek6M'
bot = telebot.TeleBot(token)

def second_to_timecode(x: float) -> str:
    hour, x = divmod(x, 3600)
    minute, x = divmod(x, 60)
    second, x = divmod(x, 1)
    millisecond = int(x * 1000.)

    return '%.2d:%.2d:%.2d,%.3d' % (hour, minute, second, millisecond)

def to_srt(
        words: list[pvleopard.Leopard.Word],
        endpoint_sec: float = 0.7,
        length_limit: int = 10) -> str:
    def _helper(end: int) -> None:
        lines.append("%d" % section)
        lines.append(
            "%s --> %s" %
            (
                second_to_timecode(words[start].start_sec),
                second_to_timecode(words[end].end_sec)
            )
        )
        lines.append(' '.join(x.word for x in words[start:(end + 1)]))
        lines.append('')

    lines = list()
    section = 0
    start = 0
    for k in range(1, len(words)):
        if ((words[k].start_sec - words[k - 1].end_sec) >= endpoint_sec) or \
                (length_limit is not None and (k - start) >= length_limit):
            _helper(k - 1)
            start = k
            section += 1
    _helper(len(words) - 1)

    return '\n'.join(lines)

def is_youtube_url(text):
    youtube_pattern = r'(https?://)?(www\.)?(youtube|youtu)\.(com|be)/.+'
    if re.match(youtube_pattern, text):
        return True
    else:
        return False

@bot.message_handler(commands=['start'])
def start_message(message):
    mess = '''
    Привет, я могу сделать субтитры к Вашему видео. Вы можете отпрвить мне видео, загрузив его с локального устройства, или же отправив ссылку на видео с YouTube.
    '''
    bot.send_message(message.chat.id, mess)
    
@bot.message_handler(content_types=['text'])
def get_url_message(message):
    if is_youtube_url(message.text):
        video = YouTube(message.text)
        video_stream = video.streams.get_highest_resolution()
        video_stream.download(output_path=os.getcwd(), filename='video.mp4')
        audio_stream = video \
            .streams \
            .filter(only_audio=True, audio_codec='opus') \
            .order_by('bitrate') \
            .last()
        audio_stream.download(output_path=os.getcwd(), filename='audio.mp3')
        
        leopard = pvleopard.create(access_key='XBQ1H4y9Uxc+RfEhu+3OLuusy+0CW9AtpDddqDrKx0TJsgOM9dQfuA==')
        transcript, words = leopard.process_file(f'{os.getcwd()}\\audio.mp3')

        subtitle_path = f'{os.getcwd()}\\subtitles.srt'

        with open(subtitle_path, 'w') as f:
            f.write(to_srt(words))

        video = VideoFileClip(f'{os.getcwd()}\\video.mp4')
        generator = lambda text: TextClip(text, font='Times New Roman', fontsize=36, color='white')
        subtitles = SubtitlesClip(f'{os.getcwd()}\\subtitles.srt', generator)
        video_with_subtitles = CompositeVideoClip([video, subtitles.set_position(('center', 'bottom'))])
        video_with_subtitles.write_videofile(f'{os.getcwd()}\\video_with_subtitles.mp4', codec="libx264")

        with open(f'{os.getcwd()}\\video_with_subtitles.mp4', 'rb') as f:
            bot.send_message(message.chat.id, 'Вот твое видео:')
            bot.send_video(message.chat.id, f)
    else:
        bot.send_message(message.chat.id, 'Неверно указана URL ссылка. Введите ссылку корректно.')
            

@bot.message_handler(content_types=['video'])
def get_video_message(message):
    video_id = message.video.file_id
    file_info = bot.get_file(video_id)
    file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
    video_file = requests.get(file_url)
    
    video_path = f'{os.getcwd()}\\video.mp4'
    audio_path = f'{os.getcwd()}\\audio.mp3'
    
    with open(video_path, 'wb') as f:
        f.write(video_file.content)

    video = VideoFileClip(video_path)
    audio = video.audio
    audio.write_audiofile(audio_path)

    leopard = pvleopard.create(access_key='XBQ1H4y9Uxc+RfEhu+3OLuusy+0CW9AtpDddqDrKx0TJsgOM9dQfuA==')
    transcript, words = leopard.process_file(f'{os.getcwd()}\\audio.mp3')
    
    subtitle_path = f'{os.getcwd()}\\subtitles.srt'

    with open(subtitle_path, 'w') as f:
        f.write(to_srt(words))
    
    video = VideoFileClip(f'{os.getcwd()}\\video.mp4')
    generator = lambda text: TextClip(text, font='Times New Roman', fontsize=36, color='white')
    subtitles = SubtitlesClip(f'{os.getcwd()}\\subtitles.srt', generator)
    video_with_subtitles = CompositeVideoClip([video, subtitles.set_position(('center', 'bottom'))])
    video_with_subtitles.write_videofile(f'{os.getcwd()}\\video_with_subtitles.mp4', codec="libx264")
    
    with open(f'{os.getcwd()}\\video_with_subtitles.mp4', 'rb') as f:
        bot.send_message(message.chat.id, 'Вот твое видео:')
        bot.send_video(message.chat.id, f)


bot.polling(non_stop=True)
