import os, sys
import mmap
from pprint import pprint
import multiprocessing
e=sys.exit

fn = '/Bic/scripts/oats/fix/missing_oats/pycopy/MatchIt_20161206.dat'

def blocks(f, cut, size=64*1024): # 65536
        start, chunk =cut
        iter=0
        read_size=int(size)
        _break =False
        while not _break:
                if _break: break
                if f.tell()+size>start+chunk:
                        read_size=int(start+chunk- f.tell() )
                        _break=True
                b = f.read(read_size)
                iter +=1
                if not b: break
                yield b


def get_chunk_line_count(data):
        fn,  chunk_id, cut = data
        start, chunk =cut
        cnt =0
        last_bl=None

        with open(fn, "r") as f:
                if 0:
                        f.seek(start)
                        bl = f.read(chunk)
                        cnt= bl.count('\n')
                else:
                        f.seek(start)
                        for i, bl  in enumerate(blocks(f,cut)):
                                cnt +=  bl.count('\n')
                                last_bl=bl

                if not last_bl.endswith('\n'):
                        cnt -=1

                return cnt
                
def start_process():
        print ('Starting', multiprocessing.current_process().name)
        

def file_count(fn):
        statinfo = os.stat(fn)
        fsize= statinfo.st_size
        pool_size = multiprocessing.cpu_count() * 2
        pool_size=36
        chunk=int(fsize/pool_size)
        fh = open(fn, "rb")

        cuts=[]
        curpos=0
        new_chunk_size=chunk
        for i in range(pool_size):
                fh.seek(chunk, os.SEEK_CUR)
                
                pos = fh.tell()
                l=fh.readline()
                partial_line=fh.tell()-pos
                new_chunk_size=fh.tell() - pos
                cuts.append([curpos,fh.tell()-curpos])
                curpos=fh.tell()
        fh.close()
        inputs = list([(fn, i,cut) for i,cut in enumerate(cuts)])

        pool = multiprocessing.Pool(processes=pool_size,
                                                                initializer=start_process,
                                                                )
        pool_outputs = pool.map(get_chunk_line_count, inputs)
        pool.close() # no more tasks
        pool.join()  # wrap up current tasks

        #print ('Pool    :', pool_outputs)
        
        print  'File size    : %d' % sum(pool_outputs)
        
        
