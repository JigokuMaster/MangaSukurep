import sys,time,os,zipfile,requests
from traceback import print_exc

REQUESTING_FILE_INFO = 0
DOWNLOADING = 1
FILE_DOWNLOADED = 2
DOWNLOAD_FAILED = -1



invalide_chars = ['"',':','*','\\','|','<','>','?']
def validate_fspath(path):
    if path is None:
       raise TypeError('path should be string')

    valide_path = ''
    for char in path:
        if char in invalide_chars:
            valide_path += '_'

        else:
            valide_path += char

    return valide_path

class DownloaderV1:
    def __init__(self,download_dir,session = None):
        self.downloadCanceled = False
        self.download_dir =  validate_fspath(download_dir)
        self.timeout = 30
        self.chunk_size = 1024*512
        self.session = session
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({'User-Agent' : 'Mozila/5.0'})

        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

    def requestFileInfo(self,url):
        length = 'Content-Length'
        disposition = 'content-disposition'
        file_name,file_size = '',0
        r = None

        try:
            r = self.session.head(url)
        except Exception as e:
            self.reportState(DOWNLOAD_FAILED,e)
            return

        if disposition in r.headers:
            file_name = r.headers[disposition]

        else:
            parts = url.split('/')
            file_name = parts[-1] or parts[-2]
         
        if length in r.headers:
            file_size = int(r.headers[length])

        return file_name , file_size

    def downloadFile(self,url,file_name_ = None):
        self.stopDowloading = False
        file_size = 0
        if file_name is None:
            file_info = self.request_fileinfo(url)
            if file_info is None:
                return False
            file_name ,file_size = file_info

        try:
            fp = os.path.join(self.download_dir,file_name)
            r = self.session.get(url ,timeout = self.timeout, stream = True)
            downloaded_bytes = 0
            with open(fp,'wb') as f:
                for chunk in r.iter_content(self.chunk_size):
                    if self.downloadCanceled:
                        break

                    f.write(chunk)         
                    downloaded_bytes += len(chunk)
                    self.self.reportState(
                        DOWNLOADING,
                        file_name,file_size,downloaded_bytes
                    )

        except Exception as e:
            self.reportState(DOWNLOAD_FAILED,e)

        self.reportState(FILE_DOWNLOADED,file_name,file_size)
        return True

    def downloadFiles(self,files_list, file_name = None):
        zipfile_name = file_name
        if not zipfile_name.endswith('.zip'):
            zipfile_name += '.zip'                

        fp = os.path.join(self.download_dir,zipfile_name)
        mode = 'w'
        if os.path.exists(fp) and zipfile.is_zipfile(fp):
            mode = 'a'

        zf = zipfile.ZipFile(fp,mode)
        name_list = zf.namelist()
        list_size = len(files_list)
        file_size = 0  
        for name,url in files_list:
            if self.downloadCanceled:
                zf.close()
                return False

            try:
                if not (name in name_list):
                    url = 'http://127.0.0.11:8080/1.png'
                    r = self.session.get(url,timeout = self.timeout)
                    content = r.content
                    content_length = len(content)
                    file_size += content_length
                    zf.writestr(name,content)
                    time.sleep(3)

                else:
                    content_length = zf.getinfo(name).file_size
                    file_size += content_length

                args = DOWNLOADING,name,file_size,content_length
                self.reportState(*args)
 
            except Exception as e:
                self.reportState(DOWNLOAD_FAILED,file_name,e)
                zf.close()
                return False

        self.reportState(FILE_DOWNLOADED,file_name,file_size)
        zf.close()
        return True

    def cancelDownload(self):
        self.downloadCanceled = True
        try:
            self.session.close()
        except:
            pass

    def reportState(self , *args):
        pass

if __name__ == '__main__':
    print(validate_fspath('/sdcard/jjk<:>me/oroo!!?*'))
    print(validate_fspath(None))
