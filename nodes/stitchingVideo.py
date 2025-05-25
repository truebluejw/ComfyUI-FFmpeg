import os
import subprocess
from ..func import has_audio,getVideoInfo,set_file_name,video_type
import torch
import math
import time

device = "cuda" if torch.cuda.is_available() else "cpu"

class StitchingVideo:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": { 
                "video1_path": ("STRING", {"default":"C:/Users/Desktop/video1.mp4",}),
                "video2_path": ("STRING", {"default":"C:/Users/Desktop/video2.mp4",}),
                "device": (["cpu","cuda"], {"default":device,}),
                "use_audio": (["video1","video2"], {"default":"video1",}),
                "stitching_type":(["horizontal","vertical"], {"default":"horizontal",}),
                "output_path": ("STRING", {"default": "C:/Users/Desktop/output"}),
                "scale_and_crop": (["yes", "no"], {"default": "no"}),  # 新增参数控制缩放裁剪
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("video_complete_path",)
    FUNCTION = "stitching_video"
    OUTPUT_NODE = True
    CATEGORY = "🔥FFmpeg"
  
    def stitching_video(self, video1_path, video2_path,device,use_audio,stitching_type,output_path,scale_and_crop):
        try:
            video1_path = os.path.abspath(video1_path).strip()
            video2_path = os.path.abspath(video2_path).strip()
            output_path = os.path.abspath(output_path).strip()
             # 视频不存在
            if not video1_path.lower().endswith(video_type()):
                raise ValueError("video1_path："+video1_path+"不是视频文件（video1_path:"+video1_path+" is not a video file）")
            if not os.path.isfile(video1_path):
                raise ValueError("video1_path："+video1_path+"不存在（video1_path:"+video1_path+" does not exist）")
            
            if not video2_path.lower().endswith(video_type()):
                raise ValueError("video2_path："+video2_path+"不是视频文件（video2_path:"+video2_path+" is not a video file）")
            if not os.path.isfile(video2_path):
                raise ValueError("video2_path："+video2_path+"不存在（video2_path:"+video2_path+" does not exist）")
            
            #判断output_path是否是一个目录
            if not os.path.isdir(output_path):
                raise ValueError("output_path："+output_path+"不是目录（output_path:"+output_path+" is not a directory）")
            
            video1_audio = has_audio(video1_path)
            video2_audio = has_audio(video2_path)
            
            #final_output = set_file_name(video1_path)
            #增加以视频1+视频2的文件名合并重命名
            final_output = f"{os.path.splitext(os.path.basename(video1_path))[0]}--{os.path.splitext(os.path.basename(video2_path))[0]}.mp4"
            
            #文件名根据年月日时分秒来命名
            output_path = os.path.join(output_path, final_output)
            
            #CPU默认参数：
            use_cuvid = ""
            use_encoder = "-c:v libx264" #默认用CPU编码

            if device == "cuda":
                use_cuvid = "-hwaccel cuda"
                use_encoder = "-c:v h264_nvenc"
            
            video_info = getVideoInfo(video1_path)
            video_info1 = getVideoInfo(video2_path)
            duration = video_info['duration']
            fps = video_info['fps']
            
            loop_count = max(1, int(duration / video_info1['duration'] + 0.9999))
            # libx264、libx265等编码器要求宽高必须是2的倍数，如果报错，可以把device换为GPU
            width =  math.ceil(video_info['width']/2)*2
            height = math.ceil(video_info['height']/2)*2
            
            use_audio = {
                'video1': '0',
                'video2': '1',
            }.get(use_audio, '0')
            
            tack_type = {
                'horizontal': 'hstack',
                'vertical': 'vstack',
            }.get(stitching_type, 'hstack')
            
            scale = {
                'horizontal':f'-1:{height}',
                'vertical':  f'{width}:-1',
            }.get(stitching_type, f'{width}:-1')
            
            print(f">>loop_count:{loop_count}")
            if video1_audio or video2_audio:
                #-map 1:a 指定使用第二个视频的音频流
                command = f'ffmpeg "-y" {use_cuvid} -i "{video1_path}" -stream_loop {loop_count-1} -i "{video2_path}" -filter_complex "[0:v]setpts=PTS-STARTPTS[ref];[1:v]scale={scale},fps={fps},setpts=PTS-STARTPTS[vid2];[ref][vid2]{tack_type}=inputs=2[v]" -map "[v]" -map {use_audio}:a? {use_encoder} -c:a aac -strict experimental -t {duration} "{output_path}"'
            else:
                command = f'ffmpeg "-y" {use_cuvid} -i "{video1_path}" -i "{video2_path}" -filter_complex "[0:v]setpts=PTS-STARTPTS[ref];[1:v]scale={scale},fps={fps}[vid2];[vid2]loop=loop={loop_count}:size=1:start=0,setpts=N/({fps})/TB[looped];[ref][looped]{tack_type}=inputs=2[v]" -map "[v]" {use_encoder} -t {duration} "{output_path}"'
            print(command)
            

            # 执行命令并检查错误
            result = subprocess.run(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            
            # 构建滤镜链
            if scale_and_crop == "yes":
                time.sleep(1)
                if not os.path.isfile(output_path) and os.path.getsize(output_path)<=0:
                    print(f"output video：{output_path}不存在或文件内容为空!")
                    return (output_path,)
                crop_video_path=os.path.join(os.path.dirname(output_path),"crop--"+final_output)
                #ffmpeg "-y" -i Z:\sucai\video_right_test\20250520040751.mp4 -filter_complex "[0:v]split=2[bg][fg];[bg]scale=540:-1,setsar=1[scaled_bg];[scaled_bg]gblur=sigma=10[blurred];[blurred]scale=540:960:force_original_aspect_ratio=disable[bg_out];[fg]scale=540:-1,setsar=1[fg_out];[bg_out][fg_out]overlay=(W-w)/2:(H-h)/2[out];[out]scale=540:960:force_original_aspect_ratio=disable,setsar=1[final_out]" -map "[final_out]" -map 0:a -c:v h264_nvenc -c:a aac Z:\sucai\video_right_test\crop20250520040751.mp4
                if stitching_type == "vertical":
                    command = f'ffmpeg "-y" -i "{output_path}" -filter_complex "[0:v]scale=-1:960[scaled];[scaled]crop=540:ih:(iw-540)/2:0[out]" -map "[out]" -map 0:a {use_encoder} -c:a aac "{crop_video_path}"'
                else:
                    command = f'ffmpeg "-y" -i "{output_path}" -filter_complex "[0:v]split=2[bg][fg];[bg]scale=540:-1,setsar=1[scaled_bg];[scaled_bg]gblur=sigma=10[blurred];[blurred]scale=540:960:force_original_aspect_ratio=disable[bg_out];[fg]scale=540:-1,setsar=1[fg_out];[bg_out][fg_out]overlay=(W-w)/2:(H-h)/2[out];[out]scale=540:960:force_original_aspect_ratio=disable,setsar=1[final_out]" -map "[final_out]" -map 0:a {use_encoder} -c:a aac "{crop_video_path}"'
                print(f">>FFmpeg Scale and crop::{command}")
                result = subprocess.run(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                output_path=crop_video_path
            
            # 检查返回码
            if result.returncode != 0:
                # 如果有错误，输出错误信息
                print(f"Error: {result.stderr.decode('utf-8')}")
                if device == "cuda":
                    print(f"***当前运算模式*[{device}]*************看下换成CPU重新执行，是否解决因编码问题的报错！********") 
                    self.stitching_video(video1_path, video2_path,"cpu",use_audio,stitching_type,os.path.dirname(output_path),scale_and_crop)
            else:
                # 输出标准输出信息
                print(f">>FFmpeg 执行完毕！Completed!\t stdout: {result.stdout}")
            return (output_path,)
        except Exception as e:
            #print("******[2]***********看下是否执行到这里！") 
            raise ValueError(e)