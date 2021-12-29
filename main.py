#-*- coding: utf-8 -*
import requests
import asyncio
import re
import aiofiles
import aiohttp
import os
from tqdm import tqdm

dl_img = True

def get_htm(url):
    req = requests.get(url)
    req.encoding = 'gbk'
    text = req.text
    all_novel_name = re.search(r'<div id="title">(?P<name>.*?)</div>',text,re.S) 
    nov_name = all_novel_name.group('name')

    return text,nov_name

                
def get_novel_title(html,novel_id,version):
    novel_title = {}
    html_list = html.split('vcss')
    
    if version == 2:
        novel_compile = re.compile(r'colspan=".*?" vid=".*?">(?P<novel_name>.*?)</td>\r\n',re.S)
    elif version == 1:
        novel_compile = re.compile(r'colspan=".*?">(?P<novel_name>.*?)</td>\r\n',re.S)
        
    title_compile = re.compile(r'<td class="ccss"><a href="(?P<url>.*?)">(?P<title_name>.*?)</a></td>',re.S)  
    
    
    for novel in html_list:
        
        res_novel = novel_compile.finditer(novel)
        res_title = title_compile.finditer(novel)
        
        for it in res_novel:
            title_list = []
            novel_name = it.group('novel_name')
            
            for title in res_title:
                
                title_anme = title.group('title_name')
                title_url = title.group('url')
                title_list.append({title_anme:f'https://www.wenku8.net/novel/{version}/{novel_id}/{title_url}'})
                
            novel_title[novel_name] = title_list
    return novel_title


def make_dir(file,novel_name):
    try:
        os.makedirs(f'novel/{novel_name}/{file}')
    except FileExistsError:
        pass
        
def name_replace(replace_str:str):
    replace_list = [b'\\',b"/",b":",b"*",b"?",b'"',b"<",b">",b"|"]
    replace_str = replace_str.strip()
    replace_str = replace_str.encode()
    for str in replace_list:
        replace_str = replace_str.replace(str,b'')
    replace_str = replace_str.decode('u8')
    return replace_str


def get_novel_text(text):
    obj = re.compile(r'&nbsp;&nbsp;&nbsp;&nbsp;(?P<text_re>.*?)\n',re.S)
    
    text_line = obj.finditer(text)
    text_list = []

    for it in text_line:
        if '<br />' in it.group('text_re'):
            line = it.group('text_re')[:-7]
        elif it.group('text_re') == '\r':
            continue
        else:
            line = it.group('text_re')
        text_list.append(line)
        
    return text_list
        
async def get_img(url,file,all_novel_name,session):
    obj = re.compile(r'<div class="divimage"><a href="(?P<img_re>.*?)"  target="_blank">',re.S)
    
    async with session.get(url) as req:
        img_url = obj.finditer(await req.text())
        r = 0
        for it in img_url:
            real_img_url = it.group('img_re')
            img_name = real_img_url.split('/')[-1]
            async with session.get(real_img_url) as req2:
                async with aiofiles.open(f'novel/{all_novel_name}/{file}/{r}.{img_name}',mode='wb') as aiofile:
                    await aiofile.write(await req2.content.read())
            r += 1

async def dl_novel(file,url,name,session,all_novel_name,pbar):
    name = name_replace(name)
    try:
        if '插图' in name:
            if dl_img == True:
                await get_img(url,file,all_novel_name,session)
                pbar.update(1)
                return 'img'
        async with aiofiles.open(f'novel/{all_novel_name}/{file}/{name}.txt',mode='w',encoding='utf-8') as aiofile:
            async with session.get(url) as req:
                text = await req.text()
                text_list = get_novel_text(text)
                novel_text = '\n\n'.join(text_list)
                await aiofile.write(novel_text)
                pbar.update(1)
    except FileNotFoundError:
        make_dir(file,all_novel_name)
        if '插图' in name:
            if dl_img == True:
                await get_img(url,file,all_novel_name,session)
                pbar.update(1)
                return 'img'               
        async with aiofiles.open(f'novel/{all_novel_name}/{file}/{name}.txt',mode='w',encoding='utf-8') as aiofile:
            async with session.get(url) as req:
                text = await req.text()
                text_list = get_novel_text(text)
                novel_text = '\n\n'.join(text_list)
                await aiofile.write(novel_text)
                pbar.update(1)
        

async def main(novel_id):
    tasks_long = 0
    tasks = []
    headers = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'}
    try:
        version = 2
        url = f'https://www.wenku8.net/novel/{version}/{novel_id}/index.htm'
        html,all_novel_name = get_htm(url)
        novel_title = get_novel_title(html,novel_id,version)
    except IndexError:
        version = 1
        url = f'https://www.wenku8.net/novel/{version}/{novel_id}/index.htm'
        html,all_novel_name = get_htm(url)
        novel_title = get_novel_title(html,novel_id,version)
    
    # print(novel_title)
    
    
    for key,valeue in novel_title.items():
        tasks_long = tasks_long + len(novel_title[key])
    with tqdm(total=tasks_long) as bar:
        async with aiohttp.ClientSession(headers=headers) as session:
            for key,valeue in novel_title.items():
                r = 0
                for dict in valeue:                    
                    for key_n,valeue_n in dict.items():
                        tasks.append(asyncio.create_task(dl_novel( key, valeue_n,f'{r}.{key_n}', session, all_novel_name, bar))) 
                    r += 1
            await asyncio.wait(tasks)

if __name__ =='__main__':
    novel_id = 2428 # https://www.wenku8.net/novel/2/{id}/index.htm or https://www.wenku8.net/book/{id}.htm
    asyncio.run(main(novel_id))
